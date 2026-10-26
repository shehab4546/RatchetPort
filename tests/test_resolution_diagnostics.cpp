// SPDX-License-Identifier: GPL-2.0-or-later
#include "ratchet_resolution_diagnostics.h"
#include "ratchet_resolution.h"
#include <cassert>
#include <climits>
#include <string>
#include <thread>
#include <vector>

namespace D = RatchetResolutionDiagnostics;
int main(int argc, char**) {
    if (argc > 1) return D::Enabled() ? 1 : 0;
    assert(D::Enabled());
    constexpr unsigned widths[]{1280, 1600, 1920, 2560, 3840};
    constexpr unsigned heights[]{720, 900, 1080, 1440, 2160};
    assert(RatchetResolution::Expected(0) == 0);
    assert(RatchetResolution::Expected(-1) == 0);
    assert(RatchetResolution::Expected(6) == 0);
    for (unsigned i = 0; i < 5; ++i) {
        assert(RatchetResolution::Expected(int(i + 1)) == RatchetResolution::Pack(widths[i], heights[i]));
        for (unsigned divisor : {1u, 2u, 4u, 8u}) {
            assert(D::Relevant(widths[i] / divisor, heights[i] / divisor));
            assert(D::Relevant(widths[i] / divisor, (heights[i] + divisor - 1) / divisor));
        }
        for (unsigned samples : {1u, 2u, 4u, 8u})
            assert(D::BaseBytes(widths[i], heights[i], 1, 2, samples, 32) ==
                   std::uint64_t(widths[i]) * heights[i] * 2 * samples * 4);
    }
    assert(D::Relevant(1920, 2160)); // display-width auxiliary, not full scene
    assert(D::Relevant(1920, 1088)); // padded target
    assert(!D::Relevant(1, 1) && !D::Relevant(8192, 8192));
    assert(!D::BaseBytes(UINT_MAX, UINT_MAX, UINT_MAX, 1, 1, 32));
    assert(!D::BaseBytes(1920, 0, 1, 1, 1, 32));
    assert(D::BaseBytes(1, 1, 1, 1, 1, 1) == 1);
    assert(!D::RangeValid(UINT64_MAX - 3, 4));
    assert(D::RangeValid(UINT64_MAX - 4, 4));
    assert(!D::RangeValid(0x1000, 0));

    D::Budget repeated{8};
    assert(repeated.Admit(10));
    for (int i = 0; i < 10000; ++i) assert(!repeated.Admit(10));
    assert(repeated.Admit(11)); // changed identity survives deduplication
    D::Budget concurrent{64};
    std::atomic<unsigned> accepted{0};
    std::vector<std::thread> threads;
    for (unsigned t = 0; t < 8; ++t) threads.emplace_back([&, t] {
        for (unsigned i = 0; i < 1000; ++i)
            if (concurrent.Admit(t * 1000 + i)) ++accepted;
    });
    for (auto& thread : threads) thread.join();
    assert(accepted == 64 && concurrent.Full());
    int descriptions = 0;
    for (int i = 0; i < 100; ++i)
        D::Once(D::Channel::Pass, 123, [&] { ++descriptions; return std::string("test"); });
    assert(descriptions == 1);
    std::puts("resolution-diagnostics-test ok (no GPU/gameplay)");
}
