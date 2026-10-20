#include "video_core/renderer_vulkan/staging_budget.h"
#include "video_core/texture_cache/ratchet_zero_clear.h"
#include <cassert>
#include <cstdio>
int main() {
    using namespace VideoCore;
    RatchetZeroDispatch d{0x0540709a, 0x108eb90000, 8355840, {8160,1,1}, {64,1,1},
                           16,14,4,true,true,false,false,true,true};
    assert(IsFullRatchetZero(d));
    for (auto bytes : {8355839ull, 8355841ull, 0ull}) { auto x=d; x.bytes=bytes; assert(!IsFullRatchetZero(x)); }
    auto partial=d; --partial.groups[0]; assert(!IsFullRatchetZero(partial));
    auto extra=d; ++extra.groups[0]; assert(!IsFullRatchetZero(extra));
    auto indirect=d; indirect.groups[1]=2; assert(!IsFullRatchetZero(indirect));
    auto swizzle=d; swizzle.swizzled=true; assert(!IsFullRatchetZero(swizzle));
    auto remap=d; remap.identity_components=false; assert(!IsFullRatchetZero(remap));
    RatchetZeroImage image{d.address,d.bytes,VK_FORMAT_R8G8B8A8_UNORM,32,1,1,1,1,1,1,
                           true,false,false,false,false,true,true};
    const auto eligible = [&](const auto& i) { return CanMirrorRatchetZero(i,d.address,d.bytes,1); };
    assert(eligible(image));
    assert(!CanMirrorRatchetZero(image,d.address,d.bytes,2));
    for (unsigned reason=0; reason<10; ++reason) {
        auto x=image;
        switch(reason) {
        case 0:x.bytes--;break; case 1:x.aliased=true;break; case 2:x.cpu_dirty=true;break;
        case 3:x.samples=4;break; case 4:x.levels=2;break; case 5:x.layers=2;break;
        case 6:x.compressed=true;break; case 7:x.depth_format=true;break;
        case 8:x.format=VK_FORMAT_R8G8B8A8_SRGB;break; case 9:x.backing_samples=4;break;
        }
        assert(!eligible(x));
    }
    using namespace Vulkan;
    // The soft budget may remain exceeded: held CPU readbacks and pending GPU work survive.
    const std::vector<StagingBudgetEntry> entries{{64,1,true,false}, {64,2,true,true},
        {64,3,false,false}, {64,10,true,false}, {64,0,true,false}};
    const auto trim=PlanStagingTrim(entries,128,10);
    assert((trim==std::vector<std::size_t>{4,0}));
    assert(PlanStagingTrim(entries,320,10).empty());
    assert(PlanStagingTrim(entries,0,10)==trim);
    // Exhaust all completion/hold combinations for several budgets.
    for (unsigned mask=0; mask<256; ++mask) for (unsigned budget=0; budget<100; budget+=11) {
        std::vector<StagingBudgetEntry> e;
        for (unsigned i=0;i<4;++i) e.push_back({10u*(i+1),i,bool(mask&(1u<<i)),bool(mask&(16u<<i))});
        auto selected=PlanStagingTrim(e,budget,3);
        unsigned remaining=100;
        for (auto index:selected) {
            assert(e[index].completed && !e[index].held && e[index].last_frame<3);
            remaining-=e[index].bytes;
        }
        if (remaining>budget) for (unsigned i=0;i<e.size();++i)
            assert(!e[i].completed || e[i].held || e[i].last_frame>=3 ||
                   std::find(selected.begin(),selected.end(),i)!=selected.end());
    }
    std::puts("PASS: exact zero coverage, format/alias/MSAA guards, and protected staging lifetimes");
}
