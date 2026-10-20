// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <algorithm>
#include <cstdint>

namespace VideoCore {
// The tiling shader processes 64 texels per group. Each callback receives its
// first texel and group count; no texel is omitted or dispatched twice.
template <typename Func>
bool ForEachTilingDispatch(std::uint32_t groups, std::uint32_t limit, Func&& record) {
    if (limit == 0 || groups > UINT32_MAX / 64) {
        return false;
    }
    for (std::uint32_t base = 0; base < groups;) {
        const auto count = std::min(limit, groups - base);
        record(base * 64, count);
        base += count;
    }
    return true;
}
} // namespace VideoCore
