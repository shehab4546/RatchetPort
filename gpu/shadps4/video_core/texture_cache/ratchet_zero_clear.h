// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <array>
#include <cstdint>
#include <vulkan/vulkan_core.h>

namespace VideoCore {
struct RatchetZeroDispatch {
    std::uint64_t shader, address, bytes;
    std::array<std::uint32_t, 3> groups, threads;
    std::uint32_t stride, format, numfmt;
    bool written, formatted, swizzled, add_tid, identity_components, no_images;
};
inline bool IsFullRatchetZero(const RatchetZeroDispatch& d) {
    return d.shader == 0x0540709a && d.address && !(d.address & 15) && d.bytes &&
           d.groups[0] && d.groups[1] == 1 && d.groups[2] == 1 &&
           d.threads == std::array<std::uint32_t, 3>{64, 1, 1} &&
           std::uint64_t(d.groups[0]) * 64 * 16 == d.bytes && d.stride == 16 &&
           d.format == 14 && d.numfmt == 4 && d.written && d.formatted &&
           !d.swizzled && !d.add_tid && d.identity_components && d.no_images;
}
struct RatchetZeroImage {
    std::uint64_t address, bytes;
    std::uint32_t format, bits, depth, levels, layers, samples, guest_samples, backing_samples;
    bool tiled, depth_format, compressed, aliased, cpu_dirty, gpu_dirty, registered;
};
inline bool CanMirrorRatchetZero(const RatchetZeroImage& i, std::uint64_t address,
                                 std::uint64_t bytes, std::uint32_t overlaps) {
    return overlaps == 1 && i.address == address && i.bytes == bytes && i.bits == 32 &&
           (i.format == VK_FORMAT_R8G8B8A8_UNORM || i.format == VK_FORMAT_B10G11R11_UFLOAT_PACK32) &&
           i.depth == 1 && i.levels == 1 && i.layers == 1 && i.samples == 1 &&
           i.guest_samples == 1 && i.backing_samples == 1 && i.tiled && !i.depth_format &&
           !i.compressed && !i.aliased && !i.cpu_dirty && i.gpu_dirty && i.registered;
}
} // namespace VideoCore
