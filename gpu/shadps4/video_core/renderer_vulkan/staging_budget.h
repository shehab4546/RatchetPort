// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <algorithm>
#include <cstdint>
#include <numeric>
#include <span>
#include <vector>

namespace Vulkan {
struct StagingBudgetEntry {
    std::uint64_t bytes, last_frame;
    bool completed, held;
};
// A soft limit: active GPU work, held readbacks, and this frame's allocations always survive.
inline std::vector<std::size_t> PlanStagingTrim(std::span<const StagingBudgetEntry> entries,
                                              std::uint64_t budget, std::uint64_t frame) {
    std::vector<std::size_t> candidates;
    std::uint64_t total = 0;
    for (std::size_t i = 0; i < entries.size(); ++i) {
        const auto& e = entries[i];
        total += e.bytes;
        if (e.completed && !e.held && e.last_frame < frame) candidates.push_back(i);
    }
    std::stable_sort(candidates.begin(), candidates.end(), [&](auto a, auto b) {
        return entries[a].last_frame < entries[b].last_frame;
    });
    std::size_t count = 0;
    while (count < candidates.size() && total > budget) total -= entries[candidates[count++]].bytes;
    candidates.resize(count);
    return candidates;
}
} // namespace Vulkan
