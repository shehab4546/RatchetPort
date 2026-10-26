// SPDX-FileCopyrightText: Copyright 2025 shadPS4 Emulator Project
// SPDX-License-Identifier: GPL-2.0-or-later

#pragma once

#include <cstddef>
#include <cstring>
#include <memory>
#include <new>
#include <span>
#include <type_traits>
#include <utility>
#include <vector>

#include "ratchet_toggles.h"
#include "video_core/renderer_vulkan/vk_common.h"

namespace Vulkan {

/// Deferred Vulkan commands and their copied data, executed in order by the recorder.
class RecordChunk {
public:
    static constexpr size_t Capacity = 128 * 1024;
    // Space for the consuming closure after its variable-length data.
    static constexpr size_t CommandReserve = 1024;

    /// Returns an empty span if a nonempty payload and its command need a new chunk.
    /// Overflow allocations must obey the same ownership rule as inline payloads.
    template <typename T>
    std::span<const T> CopyData(std::span<const T> data) {
        static_assert(std::is_trivially_copyable_v<T>);
        static_assert(alignof(T) <= __STDCPP_DEFAULT_NEW_ALIGNMENT__);
        if (data.empty()) {
            return data;
        }
        const size_t bytes = data.size_bytes();
        const size_t offset = (used + alignof(T) - 1) & ~(alignof(T) - 1);
        const bool oversized = bytes > Capacity - CommandReserve - (alignof(T) - 1);
        // An overflow allocation still belongs to this chunk. Without command room,
        // Push() would move the closure to the next chunk and leave a dangling span.
        if (Capacity - used < CommandReserve ||
            (!oversized && (offset > Capacity - CommandReserve ||
                            bytes > Capacity - CommandReserve - offset))) {
            return {};
        }
        auto* dst = static_cast<T*>(oversized ? AllocateOverflow(bytes)
                                              : Allocate(bytes, alignof(T)));
        std::memcpy(dst, data.data(), bytes);
        return {dst, data.size()};
    }

    /// Returns false (and leaves `func` untouched) when the chunk has no room.
    template <typename Func>
    bool Push(Func&& func) {
        using Command = TypedCommand<std::decay_t<Func>>;
        static_assert(sizeof(Command) <= Capacity, "recorded command is too large");
        const size_t offset = (used + alignof(Command) - 1) & ~(alignof(Command) - 1);
        if (offset + sizeof(Command) > Capacity) {
            return false;
        }
        auto* command = new (storage + offset) Command(std::forward<Func>(func));
        if (last) {
            last->next = command;
        } else {
            first = command;
        }
        last = command;
        used = offset + sizeof(Command);
        PrefetchAhead();
        return true;
    }

    /// Raw storage in the chunk for a command's variable-length data; null when full.
    void* Allocate(size_t bytes, size_t align) {
        const size_t offset = (used + align - 1) & ~(align - 1);
        if (offset + bytes > Capacity) {
            return nullptr;
        }
        used = offset + bytes;
        PrefetchAhead();
        return storage + offset;
    }

    /*
     * Storage for deferred command data that is larger than the fixed
     * 128 KiB recording chunk.
     *
     * The allocation belongs to this RecordChunk, so pointers captured by
     * deferred Vulkan commands remain valid until Execute() has consumed
     * every command in the chunk.
     */
    void* AllocateOverflow(size_t bytes) {
        overflow.push_back(std::make_unique<std::byte[]>(bytes));
        return overflow.back().get();
    }

    void Execute(vk::CommandBuffer cmdbuf) {
        for (CommandBase* command = first; command;) {
            CommandBase* const next = command->next;
            command->Execute(cmdbuf);
            command->~CommandBase();
            command = next;
        }
        first = last = nullptr;
        used = 0;
        overflow.clear();
    }

    [[nodiscard]] bool Empty() const noexcept {
        return first == nullptr;
    }

    [[nodiscard]] size_t Size() const noexcept {
        return used;
    }

private:
    /// The recording thread last read these cache lines: the first write to each has to take
    /// it back from that core. Requesting ownership a few lines ahead overlaps those
    /// transfers instead of stalling on each (RecordPrefetch).
    void PrefetchAhead() const {
        if (!RatchetToggle::Disabled(RatchetToggle::RecordPrefetch)) {
            __builtin_prefetch(storage + used + 384, 1, 3);
            __builtin_prefetch(storage + used + 448, 1, 3);
        }
    }

    struct CommandBase {
        virtual ~CommandBase() = default;
        virtual void Execute(vk::CommandBuffer cmdbuf) = 0;
        CommandBase* next{};
    };
    template <typename Func>
    struct TypedCommand final : CommandBase {
        explicit TypedCommand(Func&& func_) : func{std::move(func_)} {}
        explicit TypedCommand(const Func& func_) : func{func_} {}
        void Execute(vk::CommandBuffer cmdbuf) override {
            func(cmdbuf);
        }
        Func func;
    };

    alignas(64) std::byte storage[Capacity];

    /*
     * Large RecordData() payloads which cannot fit in storage[].
     * Cleared only after Execute(), preserving deferred-command lifetime.
     */
    std::vector<std::unique_ptr<std::byte[]>> overflow;

    size_t used = 0;
    CommandBase* first{};
    CommandBase* last{};
};

} // namespace Vulkan
