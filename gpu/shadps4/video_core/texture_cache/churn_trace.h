// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once

#include <cstdint>
#include <cstdlib>
#include <compare>

namespace VideoCore::ChurnTrace {
inline bool Enabled() {
    static const bool enabled = [] {
        const char* value = std::getenv("RATCHET_IMAGE_CHURN");
        return value && value[0] == '1' && value[1] == '\0';
    }();
    return enabled;
}

struct Meta {
    std::uint64_t uid, address, guest_bytes;
    std::uint32_t width, height, levels, format, tiled, flags;
};

template <typename Image>
Meta Describe(const Image& image) {
    return {image.image_uid, image.info.guest_address, image.info.guest_size,
            image.info.size.width, image.info.size.height, image.info.resources.levels,
            static_cast<std::uint32_t>(image.info.pixel_format),
            static_cast<std::uint32_t>(image.info.IsTiled()),
            static_cast<std::uint32_t>(image.flags)};
}

enum class Event {
    Created, CpuWrite, MaybeWrite, BackingWrite, GpuWrite, AliasCopy,
    Refresh, LegacyCharge, HashClean, EmptyCopies, Upload, ZeroMirror,
};

// Only metadata/counters are retained. No image pointer or guest memory is retained/read.
void Record(const Meta& meta, Event event, std::uint64_t bytes = 0,
            std::uint64_t span_bytes = 0, std::uint32_t mips = 0);
template <typename Image>
void RecordImage(const Image& image, Event event, std::uint64_t bytes = 0,
                 std::uint64_t span_bytes = 0, std::uint32_t mips = 0) {
    if (Enabled()) Record(Describe(image), event, bytes, span_bytes, mips);
}
void Source(std::uint64_t bytes, bool gpu_branch);
void PageGap(std::uint64_t address, std::uint64_t size, bool track, bool read_watch);
void GenerationMiss();
void OnFlip();
void Report(bool force = false);

// Declared writable bindings/copy destinations, not proof of GPU execution or data changes.
enum class ProducerKind : std::uint32_t { Unknown, ShaderBuffer, BufferCopy };
struct Producer {
    ProducerKind kind{};
    std::uint32_t stage{}, slot{}, binding{}, flags{};
    std::uint64_t shader{}, address{}, size{}, source{};
    auto operator<=>(const Producer&) const = default;
};
class ProducerScope {
public:
    explicit ProducerScope(const Producer& producer);
    ~ProducerScope();
    ProducerScope(const ProducerScope&) = delete;
    ProducerScope& operator=(const ProducerScope&) = delete;
private:
    Producer previous{};
};

// Associates buffer-cache source choices with the current RefreshImage, including nesting.
class RefreshScope {
public:
    explicit RefreshScope(const Meta& meta);
    ~RefreshScope();
    RefreshScope(const RefreshScope&) = delete;
    RefreshScope& operator=(const RefreshScope&) = delete;
private:
    std::uint64_t previous{};
};
} // namespace VideoCore::ChurnTrace
