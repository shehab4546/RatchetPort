/* Real runtime resolver, kernel and file backends; no GPU or game image needed. */
#undef NDEBUG
#include "runtime.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

typedef int32_t (ABI *Query)(void);

static unsigned toolkit_callback_calls;
static ABI void toolkit_callback(void) { ++toolkit_callback_calls; }
static void test_toolkit_callbacks(void) {
    const char *names[]={"0c7HbXRKUt4#libSceNpManagerForToolkit",
        "YIvqqvJyjEc#libSceNpManagerForToolkit","JELHf4xPufo#libSceNpManagerForToolkit",
        "JELHf4xPufo#libSceNpManager"};
    const char *symbols[]={"sceNpRegisterStateCallbackForToolkit",
        "sceNpUnregisterStateCallbackForToolkit","sceNpCheckCallbackForLib","sceNpCheckCallbackForLib"};
    for (unsigned i=0;i<4;++i) {
        assert(runtime_resolve(names[i],0) && !runtime_resolve(names[i],1));
        assert(!strcmp(runtime_import_name(names[i]),symbols[i]));
    }
    typedef int32_t (ABI *Register)(void *,void *);
    Register reg=(Register)runtime_resolve(names[0],0);
    Query unreg=(Query)runtime_resolve(names[1],0);
    Query poll=(Query)runtime_resolve(names[2],0);
    assert(runtime_resolve(names[2],0)==runtime_resolve(names[3],0));
    assert(unreg()==(int32_t)0x80550009);
    assert(reg(NULL,NULL)==(int32_t)0x80550003);
    int context=123;
    assert(reg((void *)toolkit_callback,&context)==0);
    Query net_poll=(Query)runtime_resolve("iQw3iQPhvUQ#libSceNetCtl",0);
    Query np_poll=(Query)runtime_resolve("3Zl8BePTh9Y#libSceNpManager",0);
    assert(net_poll && np_poll);
    /* The native toolkit worker polls all three services each iteration. */
    for (unsigned i=0;i<16;++i) assert(net_poll()==0 && np_poll()==0 && poll()==0);
    assert(!toolkit_callback_calls && context==123);
    assert(reg((void *)toolkit_callback,NULL)==0 && unreg()==0 && poll()==0);
    assert(!toolkit_callback_calls && unreg()==(int32_t)0x80550009);
    assert(!runtime_resolve("0c7HbXRKUt4#unrelated",0));
    assert(!runtime_resolve("0c7HbXRKUt4#libSceNpManager",0));
    assert(!runtime_resolve("JELHf4xPufo#libSceNpToolkit",0));
}

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
    test_toolkit_callbacks();
    const char *recording_name="Fc8qxlKINYQ#libSceVideoRecording";
    typedef int32_t (ABI *RecordingInfo)(uint32_t,const void *,uint64_t);
    RecordingInfo set_info=(RecordingInfo)runtime_resolve(recording_name,0);
    assert(set_info && !runtime_resolve(recording_name,1));
    assert(!strcmp(runtime_import_name(recording_name),"sceVideoRecordingSetInfo"));
    assert(!runtime_resolve("Fc8qxlKINYQ#unrelated",0));
    uint32_t recording_value=1;
    assert(set_info(0xa007,&recording_value,4)==0 && recording_value==1);
    assert(set_info(0xd,&recording_value,4)==0);
    recording_value=2;
    assert(set_info(0xd,&recording_value,4)==0 && recording_value==2);
    assert(set_info(0xa007,NULL,4)==(int32_t)0x80A80003);
    assert(set_info(0xd,&recording_value,0)==(int32_t)0x80A80003);
    assert(set_info(0xa008,&recording_value,4)==(int32_t)0x80A80008);
    const char *stream_names[]={"kvYEw2lBndk#libSceGameLiveStreaming",
        "dWM80AX39o4#libSceGameLiveStreaming","9yK6Fk8mKOQ#libSceGameLiveStreaming"};
    for (unsigned i=0;i<3;++i) {
        assert(runtime_resolve(stream_names[i],0));
        assert(!runtime_resolve(stream_names[i],1));
    }
    typedef int32_t (ABI *StreamInit)(uint64_t);
    typedef int32_t (ABI *StreamEnable)(int32_t);
    StreamInit init=(StreamInit)runtime_resolve(stream_names[0],0);
    StreamEnable enable=(StreamEnable)runtime_resolve(stream_names[1],0);
    Query terminate=(Query)runtime_resolve(stream_names[2],0);
    assert(init(0x4000)==0 && enable(1)==0 && enable(0)==0 && terminate()==0);
    assert(!runtime_resolve("kvYEw2lBndk#unrelated",0));
    assert(!runtime_resolve("caqgDl+V9qA#libSceGameLiveStreaming_debug",0));
    puts("PASS: update SDK imports, heap-trace ABI, offline streaming, toolkit callbacks and recording metadata");
    return 0;
}
