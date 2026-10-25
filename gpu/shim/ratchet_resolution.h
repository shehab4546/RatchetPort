// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once

#include <array>
#include <cmath>
#include <cstdint>
#include <string_view>

namespace RatchetResolution {
inline constexpr std::array<std::string_view, 6> Names{
    "original", "720p", "900p", "1080p", "1440p", "4K"};
inline constexpr std::array<const char*, 6> Labels{
    "Original", "720p / 1280 x 720", "900p / 1600 x 900", "1080p / 1920 x 1080",
    "1440p / 2560 x 1440", "4K / 3840 x 2160"};
inline int Parse(std::string_view name) {
    for (int i = 0; i < static_cast<int>(Names.size()); ++i)
        if (name == Names[i]) return i;
    return 0;
}
inline int Valid(int index) {
    return index >= 0 && index < static_cast<int>(Names.size()) ? index : 0;
}
inline std::uint64_t Pack(unsigned width, unsigned height) {
    return (std::uint64_t(width) << 32) | height;
}
inline unsigned Width(std::uint64_t size) { return unsigned(size >> 32); }
inline unsigned Height(std::uint64_t size) { return unsigned(size); }

// Read-only diagnostic. Never infer observed dimensions from the requested mode,
// presentation image, or upscaler settings. Identification remains a candidate:
// five equal color attachments and matching depth do not identify temporal history.
struct Sample {
    unsigned width{}, height{}, viewport_width{}, viewport_height{};
    bool operator==(const Sample&) const = default;
};
inline Sample Candidate(unsigned colors, unsigned width, unsigned height,
                        unsigned depth_width, unsigned depth_height,
                        float viewport_width, float viewport_height) {
    const float vw = std::abs(viewport_width), vh = std::abs(viewport_height);
    if (colors < 5 || width < 640 || height < 360 || width > 8192 || height > 8192 ||
        width != depth_width || height != depth_height ||
        !std::isfinite(vw) || !std::isfinite(vh) || vw < 1 || vh < 1 || vw > 16384 || vh > 16384)
        return {};
    return {width, height, unsigned(std::lround(vw)), unsigned(std::lround(vh))};
}
// Bounded distinct samples: repeated frames do not spam the log, and returning
// to an earlier scene still refreshes the overlay even when no new log is needed.
struct Samples {
    std::array<Sample, 16> seen{};
    unsigned count{};
    bool New(const Sample& sample) {
        if (!sample.width) return false;
        for (unsigned i = 0; i < count; ++i) if (seen[i] == sample) return false;
        if (count == seen.size()) return false;
        seen[count++] = sample;
        return true;
    }
};
} // namespace RatchetResolution
