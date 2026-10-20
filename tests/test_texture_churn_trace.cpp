// Drive the real diagnostic accumulator with known transfers and nested refreshes.
#include "video_core/texture_cache/churn_trace.h"
#include <cstdlib>
#include <string_view>
#include <thread>

int main(int argc, char** argv) {
    const char* flag = argc > 1 && std::string_view(argv[1]) == "off" ? "0" : "1";
#ifdef _WIN32
    _putenv_s("RATCHET_IMAGE_CHURN", flag);
#else
    setenv("RATCHET_IMAGE_CHURN", flag, 1);
#endif
    using namespace VideoCore::ChurnTrace;
    constexpr std::uint64_t MiB = 1024 * 1024;
    const Meta a{101, 0x1000000000, 16 * MiB, 2048, 2048, 12, 37, 1, 0x42};
    const Meta b{202, 0x1001000000, 2 * MiB, 512, 512, 10, 37, 0, 0x42};
    Record(a, Event::Created);
    Record(b, Event::Created);
    {
        RefreshScope outer{a};
        Record(a, Event::CpuWrite);
        Record(a, Event::LegacyCharge, 16 * MiB);
        Source(16 * MiB, false);
        Record(a, Event::Upload, 4 * MiB, 5 * MiB, 2);
        {
            RefreshScope nested{b};
            Source(2 * MiB, true);
            Record(b, Event::LegacyCharge, 2 * MiB);
            Record(b, Event::EmptyCopies);
        }
        Source(64, false); // Must belong to a after b's scope ends.
        Record(a, Event::Upload, 4 * MiB, 5 * MiB, 2);
    }
    OnFlip();
    {
        RefreshScope next{a};
        Record(a, Event::BackingWrite);
        Record(a, Event::LegacyCharge, 16 * MiB);
        Record(a, Event::Upload, 4 * MiB, 5 * MiB, 2);
    }
    PageGap(0x1000000000, 4096, true, false);
    PageGap(0x1000000000, 4096, true, false);
    GenerationMiss();
    Report(true);
    OnFlip();
    {
        RefreshScope next_window{a};
        Record(a, Event::Upload, 4 * MiB, 5 * MiB, 2);
    }
    Report(true);

    const Producer shader{.kind = ProducerKind::ShaderBuffer, .stage = 5, .slot = 3,
                          .binding = 9, .flags = 1, .shader = 0x123456789abcdef0,
                          .address = a.address, .size = a.guest_bytes};
    const Producer other{.kind = ProducerKind::ShaderBuffer, .stage = 0, .slot = 4,
                         .binding = 10, .shader = 0xabc, .address = b.address,
                         .size = b.guest_bytes};
    const Producer copy{.kind = ProducerKind::BufferCopy, .flags = 2,
                        .address = b.address, .size = 256, .source = 0x2000};
    {
        ProducerScope outer{shader};
        Record(a, Event::GpuWrite);
        {
            ProducerScope nested{copy};
            Record(b, Event::GpuWrite);
        }
        Record(a, Event::GpuWrite); // Restores shader after nested copy.
    }
    Record(a, Event::Upload, 32);
    Record(b, Event::HashClean); // Cancels pending writer association.
    Record(b, Event::Upload, 64);
    Record(a, Event::GpuWrite); // Unknown producer; must survive a report boundary.
    Report(true);
    Record(a, Event::Upload, 16);
    {
        ProducerScope outer{shader};
        Record(b, Event::GpuWrite);
        {
            ProducerScope nested{other};
            Record(b, Event::GpuWrite);
        }
        Record(b, Event::GpuWrite);
    }
    Record(b, Event::Upload, 48); // Last writer is shader, with multiple producers flagged.
    {
        ProducerScope scope{copy};
        Record(b, Event::GpuWrite);
        Record(b, Event::EmptyCopies);
    }
    Record(b, Event::Upload, 64); // Empty copy also clears association.
    Report(true);
    {
        ProducerScope parent{shader};
        std::thread worker{[&] {
            Record(b, Event::GpuWrite); // Must not inherit parent's thread-local scope.
            ProducerScope scoped{copy};
            Record(b, Event::GpuWrite);
        }};
        Record(a, Event::GpuWrite);
        worker.join();
    }
    Record(a, Event::Upload, 8);
    Record(b, Event::Upload, 8);
    Report(true);
    {
        ProducerScope scope{shader};
        Record(a, Event::GpuWrite);
        Record(a, Event::ZeroMirror, 4096);
    }
    Record(a, Event::Upload, 64); // Mirror ended the pending writer association.
    Report(true);
}
