/* Real runtime resolver, kernel and file backends; no GPU or game image needed. */
#undef NDEBUG
#include "runtime.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

typedef int32_t (ABI *Query)(void);

static void test_heap_trace_contract(void) {
    typedef void (ABI *TraceQuery)(void *);
    const char *name="NWtTN10cJzE#libSceLibcInternalExt";
    TraceQuery query=(TraceQuery)runtime_resolve(name,0);
    assert(query && !strcmp(runtime_import_name(name),"sceLibcHeapGetTraceInfo"));
    assert(!runtime_resolve(name,1));
    assert(!runtime_resolve("NWtTN10cJzE#libc",0));
    assert(!runtime_resolve("NWtTN10cJzE#unrelated",0));
    /* Raw byte offsets deliberately independent of runtime.c's private struct.
     * The actual libc template is size=32, flags=1, with two output pointers. */
    uint64_t record[6]={UINT64_C(0x12345678abcdef01),32,1,0,0,UINT64_C(0x1122334455667788)};
    uint32_t enabled=99;
    memcpy((char *)&record[1]+12,&enabled,4);
    query(&record[1]);
    assert(record[0]==UINT64_C(0x12345678abcdef01) && record[5]==UINT64_C(0x1122334455667788));
    assert(record[1]==32 && record[2]==1); /* size/flags preserved, segment tracing disabled */
    uint64_t *mask=(uint64_t *)(uintptr_t)record[3];
    uint64_t *states=(uint64_t *)(uintptr_t)record[4];
    assert(mask && states && !*mask);
    for (unsigned i=0;i<64;++i) assert(!states[i]);
    *mask=UINT64_C(1)<<63;
    states[0]=0x1234; states[63]=0x5678;
    uint64_t again[4]={32,7,0,0};
    query(again);
    assert(again[0]==32 && again[1]==7 && again[2]==record[3] && again[3]==record[4]);
    assert(*mask==(UINT64_C(1)<<63) && states[0]==0x1234 && states[63]==0x5678);
    *mask=0; states[0]=states[63]=0;
}

int main(void) {
    const char *queries[]={"WslcK1FQcGI#libkernel",
        "mpxAdqW7dKY#libkernel_cpumode_platform", "mpxAdqW7dKY#libkernel"};
    runtime_start(1);
    for (unsigned i=0;i<sizeof(queries)/sizeof(queries[0]);++i) {
        Query query=(Query)runtime_resolve(queries[i],0);
        assert(query && query()==0); /* Same base PS4 model as the GPU bridge. */
        assert(!runtime_resolve(queries[i],1));
    }
    assert(!runtime_resolve("mpxAdqW7dKY#unrelated",0));
    const char *files[]={"ih4CD9-gghM#libScePosix","VAzswvTOCzI#libScePosix",
                         "FN4gaPmuFV8#libScePosix"};
    const char *symbols[]={"ftruncate","unlink","write"};
    for (unsigned i=0;i<3;++i) {
        assert(!strcmp(runtime_import_name(files[i]),symbols[i]));
        assert(runtime_resolve(files[i],0));
        assert(!runtime_resolve(files[i],1));
    }
    assert(!strcmp(runtime_import_name("TywrFKCoLGY#libSceSaveData"),"sceSaveDataInitialize3"));
    assert(!strcmp(runtime_import_name("0z45PIH+SNI#libSceSaveData"),"sceSaveDataMount2"));
    test_heap_trace_contract();
    puts("PASS: update console queries, exact SDK aliases and persistent heap-trace ABI");
    return 0;
}
