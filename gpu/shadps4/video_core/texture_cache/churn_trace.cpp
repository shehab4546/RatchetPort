// SPDX-License-Identifier: GPL-2.0-or-later
#include "video_core/texture_cache/churn_trace.h"

#include <algorithm>
#include <array>
#include <atomic>
#include <chrono>
#include <cstdio>
#include <limits>
#include <map>
#include <mutex>
#include <tuple>
#include <unordered_map>
#include <vector>

namespace VideoCore::ChurnTrace {
namespace {
using u64 = std::uint64_t;
using u32 = std::uint32_t;
constexpr u64 MaxImages = 8192;
constexpr u64 MaxGaps = 128;
constexpr u64 MaxProducers = 8192;
constexpr u64 NoEpoch = std::numeric_limits<u64>::max();
struct Counts {
    u64 created{}, refreshes{}, legacy{}, uploads{}, payload{}, span{}, mips{};
    u64 hash_clean{}, empty{}, same_epoch{}, adjacent_epoch{};
    u64 cpu{}, maybe{}, backing{}, gpu{}, alias{};
    u64 ram_source{}, gpu_source{}, upload_causes{};
    u64 zero_mirrors{}, zero_bytes{};
};
struct Entry {
    Meta meta{};
    Counts window{};
    u64 last_upload_epoch = NoEpoch;
    u64 pending_causes{};
    Producer first_producer{}, last_producer{};
    u64 pending_gpu_events{};
    bool multiple_producers{};
};
struct ProducerCounts {
    u64 invalidations{}, last_uploads{}, last_payload{}, multi_events{}, multi_producers{};
};
struct State {
    std::mutex mutex;
    std::unordered_map<u64, Entry> images;
    std::map<std::tuple<u64, u64, bool, bool>, u64> gaps;
    std::map<std::pair<u64, Producer>, ProducerCounts> producers;
    std::atomic<u64> flip_epoch{0};
    u64 dropped{}, dropped_gaps{}, generation_misses{}, window_index{};
    u64 dropped_producers{};
    std::chrono::steady_clock::time_point last = std::chrono::steady_clock::now();
};
State& Get() {
    static State state;
    return state;
}
thread_local u64 refresh_uid = 0;
thread_local Producer current_producer{};

std::FILE* Output() {
    static std::FILE* output = [] {
        const char* path = std::getenv("RATCHET_IMAGE_CHURN_LOG");
        if (path && *path) {
            if (auto* file = std::fopen(path, "wb")) return file;
            std::fprintf(stderr, "RATCHET CHURN: cannot open dedicated log; using stderr\n");
        }
        return stderr;
    }();
    return output;
}

ProducerCounts* FindProducer(State& state, u64 uid, const Producer& producer) {
    const auto key = std::make_pair(uid, producer);
    auto found = state.producers.find(key);
    if (found != state.producers.end()) return &found->second;
    if (state.producers.size() == MaxProducers) {
        ++state.dropped_producers;
        return nullptr;
    }
    return &state.producers[key];
}

void ClearPending(Entry& entry) {
    entry.pending_causes = 0;
    entry.pending_gpu_events = 0;
    entry.multiple_producers = false;
}

Entry* Find(State& state, const Meta& meta) {
    auto found = state.images.find(meta.uid);
    if (found != state.images.end()) {
        found->second.meta = meta;
        return &found->second;
    }
    if (state.images.size() == MaxImages) {
        ++state.dropped;
        return nullptr;
    }
    return &state.images.emplace(meta.uid, Entry{.meta = meta}).first->second;
}
} // namespace

void Record(const Meta& meta, Event event, u64 bytes, u64 span_bytes, u32 mips) {
    if (!Enabled()) return;
    auto& state = Get();
    std::scoped_lock lock{state.mutex};
    auto* entry = Find(state, meta);
    if (!entry) return;
    auto& count = entry->window;
    switch (event) {
    case Event::Created: ++count.created; entry->pending_causes |= 16; break;
    case Event::CpuWrite: ++count.cpu; entry->pending_causes |= 1; break;
    case Event::MaybeWrite: ++count.maybe; entry->pending_causes |= 8; break;
    case Event::BackingWrite: ++count.backing; entry->pending_causes |= 2; break;
    case Event::GpuWrite: {
        ++count.gpu;
        entry->pending_causes |= 4;
        if (!entry->pending_gpu_events) entry->first_producer = current_producer;
        entry->multiple_producers |= entry->first_producer != current_producer;
        entry->last_producer = current_producer;
        ++entry->pending_gpu_events;
        if (auto* p = FindProducer(state, meta.uid, current_producer)) ++p->invalidations;
        break;
    }
    case Event::AliasCopy: ++count.alias; break;
    case Event::Refresh: ++count.refreshes; break;
    case Event::LegacyCharge: count.legacy += bytes; break;
    case Event::HashClean: ++count.hash_clean; ClearPending(*entry); break;
    case Event::EmptyCopies: ++count.empty; ClearPending(*entry); break;
    case Event::ZeroMirror:
        ++count.zero_mirrors; count.zero_bytes += bytes; ClearPending(*entry); break;
    case Event::Upload: {
        ++count.uploads;
        count.payload += bytes;
        count.span += span_bytes;
        count.mips += mips;
        count.upload_causes |= entry->pending_causes;
        if (entry->pending_gpu_events) {
            if (auto* p = FindProducer(state, meta.uid, entry->last_producer)) {
                ++p->last_uploads;
                p->last_payload += bytes;
                p->multi_events += entry->pending_gpu_events > 1;
                p->multi_producers += entry->multiple_producers;
            }
        }
        ClearPending(*entry);
        const u64 epoch = state.flip_epoch.load(std::memory_order_relaxed);
        if (entry->last_upload_epoch != NoEpoch) {
            count.same_epoch += entry->last_upload_epoch == epoch;
            count.adjacent_epoch += entry->last_upload_epoch + 1 == epoch;
        }
        entry->last_upload_epoch = epoch;
        break;
    }
    }
}

ProducerScope::ProducerScope(const Producer& producer) : previous{current_producer} {
    if (Enabled()) current_producer = producer;
}
ProducerScope::~ProducerScope() {
    if (Enabled()) current_producer = previous;
}

RefreshScope::RefreshScope(const Meta& meta) : previous{refresh_uid} {
    if (!Enabled()) return;
    Record(meta, Event::Refresh);
    refresh_uid = meta.uid;
}
RefreshScope::~RefreshScope() {
    refresh_uid = previous;
}

void Source(u64 bytes, bool gpu_branch) {
    if (!Enabled()) return;
    auto& state = Get();
    std::scoped_lock lock{state.mutex};
    if (const auto found = state.images.find(refresh_uid); found != state.images.end()) {
        auto& count = found->second.window;
        (gpu_branch ? count.gpu_source : count.ram_source) += bytes;
    }
}

void PageGap(u64 address, u64 size, bool track, bool read_watch) {
    if (!Enabled()) return;
    auto& state = Get();
    std::scoped_lock lock{state.mutex};
    const auto key = std::make_tuple(address, size, track, read_watch);
    if (state.gaps.size() < MaxGaps || state.gaps.contains(key)) ++state.gaps[key];
    else ++state.dropped_gaps;
}

void GenerationMiss() {
    if (!Enabled()) return;
    auto& state = Get();
    std::scoped_lock lock{state.mutex};
    ++state.generation_misses;
}

void OnFlip() {
    if (!Enabled()) return;
    Get().flip_epoch.fetch_add(1, std::memory_order_relaxed);
    Report();
}

void Report(bool force) {
    if (!Enabled()) return;
    auto& state = Get();
    std::scoped_lock lock{state.mutex};
    const auto now = std::chrono::steady_clock::now();
    const double seconds = std::chrono::duration<double>(now - state.last).count();
    if (!force && seconds < 5.0) return;
    const auto window = ++state.window_index;
    auto* output = Output();
    // Print all active rows, at most MaxImages. The opt-in trace may affect timing.
    std::vector<Entry*> active;
    u64 legacy = 0, payload = 0, uploads = 0, repeats = 0, adjacent = 0;
    for (auto& [uid, entry] : state.images) {
        auto& c = entry.window;
        if (c.refreshes || c.uploads || c.cpu || c.backing || c.gpu || c.maybe || c.alias || c.created || c.zero_mirrors) {
            active.push_back(&entry);
            legacy += c.legacy;
            payload += c.payload;
            uploads += c.uploads;
            repeats += c.same_epoch;
            adjacent += c.adjacent_epoch;
        }
    }
    std::sort(active.begin(), active.end(), [](const Entry* a, const Entry* b) {
        return a->window.payload > b->window.payload;
    });
    std::fprintf(output, "RATCHET CHURN summary window=%llu seconds=%.3f flip_epoch=%llu "
                 "images=%zu uploads=%llu legacy_bytes=%llu copy_payload_bytes=%llu "
                 "same_epoch=%llu adjacent_epoch=%llu generation_misses=%llu "
                 "dropped_image_events=%llu dropped_gap_events=%llu producer_rows=%zu "
                 "dropped_producer_events=%llu\n",
                 window, seconds, state.flip_epoch.load(), active.size(), uploads,
                 legacy, payload, repeats, adjacent, state.generation_misses,
                 state.dropped, state.dropped_gaps, state.producers.size(), state.dropped_producers);
    for (const auto* entry : active) {
        const auto& m = entry->meta;
        const auto& c = entry->window;
        std::fprintf(output, "RATCHET CHURN image window=%llu uid=%llu addr=0x%llx "
                     "guest_bytes=%llu width=%u height=%u levels=%u format=%u tiled=%u "
                     "flags=0x%x created=%llu refreshes=%llu uploads=%llu legacy_bytes=%llu "
                     "copy_payload_bytes=%llu copy_span_bytes=%llu copied_mips=%llu "
                     "same_epoch=%llu adjacent_epoch=%llu cpu=%llu maybe=%llu backing=%llu "
                     "gpu=%llu alias=%llu hash_clean=%llu empty=%llu ram_source_bytes=%llu "
                     "gpu_source_bytes=%llu upload_cause_mask=0x%llx "
                     "zero_mirrors=%llu zero_mirror_texel_bytes=%llu\n",
                     window, m.uid, m.address, m.guest_bytes, m.width, m.height, m.levels,
                     m.format, m.tiled, m.flags, c.created, c.refreshes, c.uploads, c.legacy,
                     c.payload, c.span, c.mips, c.same_epoch, c.adjacent_epoch, c.cpu,
                     c.maybe, c.backing, c.gpu, c.alias, c.hash_clean, c.empty,
                     c.ram_source, c.gpu_source, c.upload_causes, c.zero_mirrors, c.zero_bytes);
    }
    for (const auto& [key, count] : state.producers) {
        const auto& [uid, p] = key;
        std::fprintf(output, "RATCHET CHURN producer window=%llu uid=%llu kind=%u "
                     "stage=%u slot=%u binding=%u producer_flags=0x%x shader=0x%llx "
                     "write_addr=0x%llx write_bytes=%llu copy_src=0x%llx "
                     "invalidations=%llu last_writer_uploads=%llu last_writer_payload_bytes=%llu "
                     "multi_event_uploads=%llu multi_producer_uploads=%llu\n",
                     window, uid, unsigned(p.kind), p.stage, p.slot, p.binding, p.flags,
                     p.shader, p.address, p.size, p.source, count.invalidations,
                     count.last_uploads, count.last_payload, count.multi_events,
                     count.multi_producers);
    }
    for (const auto& [key, count] : state.gaps) {
        const auto [address, size, track, read_watch] = key;
        std::fprintf(output, "RATCHET CHURN gap window=%llu addr=0x%llx bytes=%llu "
                     "track=%u read_watch=%u calls=%llu\n", window, address, size,
                     unsigned(track), unsigned(read_watch), count);
    }
    for (auto& [uid, entry] : state.images) entry.window = {};
    state.gaps.clear();
    state.producers.clear();
    state.dropped_producers = 0;
    state.generation_misses = state.dropped = state.dropped_gaps = 0;
    state.last = now;
    std::fflush(output);
}
} // namespace VideoCore::ChurnTrace
