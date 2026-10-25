// Adaptive image-cache pressure policy. All sizes use the same accounting domain.
#pragma once
#include <cstddef>
#include <cstdint>

namespace VideoCore {
struct GcPolicy {
    bool active = false;
    // A 7-point recovery gap prevents oscillation around the trigger.
    bool Update(uint64_t used, uint64_t trigger, uint64_t recovery) {
        if (active && used < recovery) active = false;
        if (!active && used >= trigger) active = true;
        return active;
    }
    static uint64_t Percent(uint64_t budget, unsigned percent) {
        return budget / 100 * percent + budget % 100 * percent / 100;
    }
    static constexpr size_t ScanLimit = 256;
    static constexpr unsigned DeadlineMs = 2;
    static constexpr uint64_t RetryTicks = 120;
    // These are submission ticks, not frames. Preserve the existing recent-use protection.
    static uint64_t MinimumAge(bool pressure, bool critical) {
        return critical ? 160 : pressure ? 80 : 16;
    }
    static size_t DeletionLimit(bool pressure, bool critical) {
        return critical ? 24 : pressure ? 12 : 4;
    }
};
} // namespace VideoCore
