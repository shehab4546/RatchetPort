#include <algorithm>
#include <cassert>
#include <cstdio>
#include <memory>
#include <span>
#include <vector>

#include "video_core/renderer_vulkan/vk_record_chunk.h"

extern "C" {
std::uint64_t runtime_disabled_optimizations = RatchetToggle::RecordPrefetch;
}

using Vulkan::RecordChunk;

// Execute earlier chunks before the consuming command, matching the recorder thread.
// ASan must also be able to catch premature destruction of an overflow allocation.
static void CheckRollover(size_t remaining, size_t elements) {
    auto current = std::make_unique<RecordChunk>();
    std::vector<std::unique_ptr<RecordChunk>> queued;
    bool earlier_executed = false;
    assert(current->Push([&](vk::CommandBuffer) { earlier_executed = true; }));
    const size_t fill = RecordChunk::Capacity - remaining - current->Size();
    assert(current->Allocate(fill, 1));

    std::vector<std::uint64_t> source(elements);
    for (size_t i = 0; i < elements; ++i) source[i] = i ^ 0xfedcba9876543210ULL;
    auto copy = current->CopyData(std::span<const std::uint64_t>{source});
    if (copy.empty()) {
        queued.push_back(std::move(current));
        current = std::make_unique<RecordChunk>();
        copy = current->CopyData(std::span<const std::uint64_t>{source});
    }
    assert(!copy.empty());
    // Overwrite the source to ensure the deferred command owns a real copy.
    std::fill(source.begin(), source.end(), 0);
    bool consumed = false;
    auto command = [copy, &consumed, &earlier_executed](vk::CommandBuffer) {
        assert(earlier_executed);
        for (size_t i = 0; i < copy.size(); ++i)
            assert(copy[i] == (i ^ 0xfedcba9876543210ULL));
        consumed = true;
    };
    if (!current->Push(command)) {
        queued.push_back(std::move(current));
        current = std::make_unique<RecordChunk>();
        assert(current->Push(command));
    }
    for (auto& chunk : queued) chunk->Execute(vk::CommandBuffer{});
    queued.clear();
    current->Execute(vk::CommandBuffer{});
    assert(consumed);
    assert(current->Empty() && current->Size() == 0);
}

int main() {
    // Both inline and >128 KiB overflow data at full, almost full and safe boundaries.
    for (const size_t remaining : {size_t{0}, size_t{8}, size_t{64}, size_t{1023},
                                   size_t{1024}, size_t{4096}}) {
        for (const size_t count : {size_t{1}, size_t{64}, size_t{16256}, size_t{16384},
                                   size_t{32768}}) {
            CheckRollover(remaining, count);
        }
    }
    auto chunk = std::make_unique<RecordChunk>();
    assert(chunk->CopyData(std::span<const std::uint64_t>{}).empty());
    assert(chunk->Size() == 0);
    // Two overflow allocations in one chunk must both survive until consumption.
    const std::vector<std::uint64_t> source(32768, 0x1234);
    const auto first = chunk->CopyData(std::span<const std::uint64_t>{source});
    const auto second = chunk->CopyData(std::span<const std::uint64_t>{source});
    assert(first.data() != second.data());
    assert(chunk->Push([first, second](vk::CommandBuffer) {
        assert(first.front() == 0x1234 && first.back() == 0x1234);
        assert(second.front() == 0x1234 && second.back() == 0x1234);
    }));
    chunk->Execute(vk::CommandBuffer{});
    // Exercise the actual payload type used by Runtime::FlushBarriers().
    const std::vector<vk::ImageMemoryBarrier2> barriers(2048, vk::ImageMemoryBarrier2{
        .srcStageMask = vk::PipelineStageFlagBits2::eTransfer,
        .srcAccessMask = vk::AccessFlagBits2::eTransferWrite,
        .dstStageMask = vk::PipelineStageFlagBits2::eFragmentShader,
        .dstAccessMask = vk::AccessFlagBits2::eShaderRead,
    });
    const auto recorded = chunk->CopyData(std::span<const vk::ImageMemoryBarrier2>{barriers});
    assert(recorded.size() == barriers.size());
    assert(chunk->Push([recorded](vk::CommandBuffer) {
        for (const auto& barrier : recorded) {
            assert(barrier.sType == vk::StructureType::eImageMemoryBarrier2);
            assert(barrier.srcAccessMask == vk::AccessFlagBits2::eTransferWrite);
            assert(barrier.dstAccessMask == vk::AccessFlagBits2::eShaderRead);
        }
    }));
    chunk->Execute(vk::CommandBuffer{});
    std::puts("Deferred record data lifetime: PASS (30 rollover cases)");
}
