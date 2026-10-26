// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once

#include <array>
#include <atomic>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <initializer_list>
#include <limits>
#include <mutex>
#include <string_view>
#include <unordered_set>

// Read-only, bounded startup diagnostics for issue #19. Deliberately independent
// of RATCHET_GPU_LOG: the normal warning threshold hid the old size observations.
namespace RatchetResolutionDiagnostics {
inline bool Enabled() {
    static const bool enabled = [] {
        const char* value = std::getenv("RATCHET_RESOLUTION_DIAGNOSTICS");
        return !value || std::string_view(value) != "0";
    }();
    return enabled;
}

inline std::uint64_t Key(std::initializer_list<std::uint64_t> words) {
    std::uint64_t hash = 14695981039346656037ull;
    for (auto word : words) {
        hash = (hash ^ word) * 1099511628211ull;
        hash ^= hash >> 32;
    }
    return hash;
}

// Screen-sized families, including rounded/padded derivatives and the native
// display-width auxiliary target. This is a filter, NOT a resource-role classifier.
inline bool Relevant(unsigned width, unsigned height) {
    constexpr std::array<std::array<unsigned, 2>, 5> sizes{{
        {1280, 720}, {1600, 900}, {1920, 1080}, {2560, 1440}, {3840, 2160}}};
    for (const auto& size : sizes) {
        if (width == 1920 && height == size[1]) return true;
        for (unsigned divisor : {1u, 2u, 4u, 8u}) {
            const auto w = size[0] / divisor, h = size[1] / divisor;
            if (width >= w && width - w < 64 && height >= h && height - h < 64)
                return true;
        }
    }
    return false;
}

inline bool RangeValid(std::uint64_t address, std::uint64_t size) {
    return size && address <= std::numeric_limits<std::uint64_t>::max() - size;
}

// Lower bound for the base mip of an uncompressed image; tiling/alignment/mips
// can increase it. Zero means invalid/overflow, never a successful zero-byte image.
inline std::uint64_t BaseBytes(unsigned pitch, unsigned height, unsigned depth,
                               unsigned layers, unsigned samples, unsigned bits) {
    std::uint64_t value = 1;
    for (auto factor : {pitch, height, depth, layers, samples, bits}) {
        if (!factor || value > std::numeric_limits<std::uint64_t>::max() / factor) return 0;
        value *= factor;
    }
    return value / 8 + (value % 8 != 0);
}

// Independent budgets keep loading textures from consuming pass/error records.
// Once exhausted, the hot path is one atomic load; memory and output stay bounded.
class Budget {
public:
    explicit Budget(unsigned limit) : limit{limit} {}
    bool Admit(std::uint64_t key) {
        if (full.load(std::memory_order_relaxed)) return false;
        std::scoped_lock lock{mutex};
        if (seen.size() >= limit || !seen.insert(key).second) return false;
        if (seen.size() == limit) full.store(true, std::memory_order_relaxed);
        return true;
    }
    bool Full() const { return full.load(std::memory_order_relaxed); }
    bool AnnounceLimit() { return Full() && !announced.exchange(true, std::memory_order_relaxed); }
private:
    unsigned limit;
    std::atomic<bool> full{false};
    std::atomic<bool> announced{false};
    std::mutex mutex;
    std::unordered_set<std::uint64_t> seen;
};

enum class Channel { Resource, Binding, Pass, Viewport, Transfer, Mapping, Failure, Lookup, Cache, Count };
inline std::array<Budget, unsigned(Channel::Count)> budgets{
    Budget{256}, Budget{256}, Budget{128}, Budget{64}, Budget{64}, Budget{64}, Budget{32}, Budget{128}, Budget{32}};
inline constexpr std::array<const char*, unsigned(Channel::Count)> names{
    "resource", "binding", "pass", "viewport", "transfer", "mapping", "failure", "lookup", "cache"};
inline std::mutex output_mutex;

template <typename Describe>
inline void Once(Channel channel, std::uint64_t key, Describe&& describe) {
    auto& budget = budgets[unsigned(channel)];
    if (!Enabled() || !budget.Admit(key)) return;
    // Describe outside the output lock: it may read the GPU mapping registry.
    const auto message = describe();
    std::scoped_lock lock{output_mutex};
    std::fprintf(stderr, "ResolutionDiag %s: %s\n", names[unsigned(channel)], message.c_str());
    if (budget.AnnounceLimit())
        std::fprintf(stderr, "ResolutionDiag %s: limit reached; further records suppressed\n",
                     names[unsigned(channel)]);
}
} // namespace RatchetResolutionDiagnostics
