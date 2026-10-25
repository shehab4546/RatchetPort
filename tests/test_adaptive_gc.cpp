// Stateful pressure transitions and cursor mutation, without a GPU.
#include <cassert>
#include <cstddef>
#include <vector>
#include <limits>
#include "common/lru_cache.h"
#include "video_core/texture_cache/gc_policy.h"
int main() {
    VideoCore::GcPolicy p;
    assert(!p.Update(77,78,71));
    assert(p.Update(78,78,71));
    assert(p.Update(72,78,71));
    assert(!p.Update(70,78,71));
    assert(!p.Update(77,78,71));
    const uint64_t big=std::numeric_limits<uint64_t>::max();
    assert(p.Percent(big,95)<big);
    assert(p.Percent(1000,85)==850);
    assert(!p.Update(4000,p.Percent(16000,78),p.Percent(16000,71)));
    assert(p.Update(9000,p.Percent(10000,78),p.Percent(10000,71)));
    assert(p.MinimumAge(true,true)>0 && p.DeletionLimit(true,true)<p.ScanLimit);
    Common::LeastRecentlyUsedCache<int,uint64_t> lru;
    std::vector<size_t> ids;
    for (int i=0;i<600;++i) ids.push_back(lru.Insert(i,0));
    std::vector<int> visited;
    auto see=[&](int i) { visited.push_back(i); return false; };
    lru.ResumeItemsBelow(1,256,see);
    assert(visited.size()==256 && visited.back()==255);
    // Removing the next candidate must not leave a cursor pointing at a recycled slot.
    lru.Free(ids[256]);
    lru.Insert(900,100);
    lru.ResumeItemsBelow(1,256,see);
    assert(visited[256]==257 && visited.back()==512);
    lru.Touch(ids[513],100); // Moving the cursor target must also repair it.
    lru.ResumeItemsBelow(1,256,see);
    assert(visited[512]==514 && visited.back()==599);
    // At the age boundary the next sweep starts from the head, not from recent items.
    visited.clear();
    lru.ResumeItemsBelow(1,1,see);
    assert(visited==std::vector<int>{0});
    // Callback deletion and bounded early exit must advance exactly once.
    lru.ResumeItemsBelow(1,256,[&](int i) { assert(i==1); lru.Free(ids[i]); return true; });
    visited.clear(); lru.ResumeItemsBelow(1,1,see);
    assert(visited==std::vector<int>{2});
    Common::LeastRecentlyUsedCache<int,uint64_t> small;
    const auto x=small.Insert(1,0);
    small.ResumeItemsBelow(0,4,[&](int) { small.Free(x); return false; });
    small.ResumeItemsBelow(0,4,[](int) { assert(false); return false; });
    small.Insert(2,10);
    small.ResumeItemsBelow(9,4,[](int) { assert(false); return false; });
    unsigned count=0;
    small.ResumeItemsBelow(10,4,[&](int i) { assert(i==2); ++count; return false; });
    assert(count==1);
}
