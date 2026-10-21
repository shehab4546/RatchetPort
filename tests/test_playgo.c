/* Real runtime_resolve -> services -> runtime_lookup -> import_names, plus real
 * runtime file I/O. Only unrelated service/GPU backends are stubbed separately. */
#undef NDEBUG
#include "runtime.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

typedef struct { const void *buffer; uint32_t size, reserved; } InitParams;
typedef int32_t (ABI *Init)(const InitParams *);
typedef int32_t (ABI *Open)(uint32_t *,const void *);
typedef int32_t (ABI *Prefetch)(uint32_t,const uint16_t *,uint32_t,int8_t);
typedef int32_t (ABI *Eta)(uint32_t,const uint16_t *,uint32_t,int64_t *);
typedef int32_t (ABI *Close)(uint32_t);
typedef int32_t (ABI *Terminate)(void);
typedef int32_t (ABI *Chunks)(uint32_t,uint16_t *,uint32_t,uint32_t *);
#define ERR(n) ((int32_t)(0x80b20000u | (n)))
#define GET(type,nid) ((type)runtime_resolve(nid "#libScePlayGo",0))
int main(int argc,char **argv) {
    assert(argc==2 || argc==3);
    runtime_start(1);
    assert(runtime_file_mount("/app0",argv[1])==0);
    Init init=GET(Init,"ts6GlZOKRrE");
    Open open=GET(Open,"M1Gma1ocrGE");
    Prefetch prefetch=GET(Prefetch,"-Q1-u1a7p0g");
    Eta eta=GET(Eta,"v6EZ-YWRdMs");
    Close close=GET(Close,"Uco1I0dlDi8");
    Terminate term=GET(Terminate,"MPe0EeBGM-E");
    Chunks chunks=GET(Chunks,"73fF1MFU8hA");
    assert(init && open && prefetch && eta && close && term && chunks);
    assert(!runtime_resolve("unknown#libScePlayGo",0));
    assert(!runtime_resolve("-Q1-u1a7p0g#otherLibrary",0));
    assert(!runtime_resolve("-Q1-u1a7p0g#libScePlayGo",1));
    uint32_t handle=99; uint16_t ids[]={0,2}; int64_t remaining=123;
    assert(open(&handle,NULL)==ERR(5) && handle==99);
    assert(prefetch(1,ids,2,3)==ERR(5));
    assert(eta(1,ids,2,&remaining)==ERR(5) && remaining==123);
    char buffer; InitParams params={&buffer,0x200000,0}; /* API does not consume workspace */
    assert(init(NULL)==ERR(10));
    params.buffer=NULL; assert(init(&params)==ERR(10)); params.buffer=&buffer;
    params.size=1; assert(init(&params)==ERR(11)); params.size=0x200000;
    params.reserved=1; assert(init(&params)==ERR(4)); params.reserved=0;
    if (argc==3) {
        assert(init(&params)==ERR(14));
        assert(open(&handle,NULL)==ERR(5) && handle==99);
        assert(eta(1,ids,2,&remaining)==ERR(5) && remaining==123);
        puts("PASS: invalid/missing metadata leaves PlayGo uninitialized");
        return 0;
    }
    assert(init(&params)==0 && init(&params)==ERR(6));
    assert(open(NULL,NULL)==ERR(10));
    assert(open(&handle,&buffer)==ERR(4) && handle==99);
    assert(open(&handle,NULL)==0 && handle==1);
    uint32_t count=99; uint16_t found[4]={99,99,99,99};
    assert(chunks(handle,found,4,&count)==0 && count==3 && found[2]==2 && found[3]==99);
    for (int locus=0;locus<=3;++locus)
        assert(prefetch(handle,ids,2,(int8_t)locus)==(locus==1 ? ERR(16) : 0));
    assert(prefetch(handle,ids,2,-1)==ERR(16));
    assert(prefetch(handle,ids,2,4)==ERR(16));
    assert(prefetch(0,ids,2,3)==ERR(9) && prefetch(2,ids,2,3)==ERR(9));
    assert(prefetch(handle,NULL,2,3)==ERR(10));
    assert(prefetch(handle,ids,0,3)==ERR(11));
    assert(prefetch(handle,ids,UINT32_MAX,3)==ERR(11));
    assert(eta(handle,ids,2,&remaining)==0 && remaining==0);
    remaining=INT64_C(0x123456789abcdef);
    assert(eta(0,ids,2,&remaining)==ERR(9) && remaining==INT64_C(0x123456789abcdef));
    assert(eta(handle,NULL,2,&remaining)==ERR(10));
    assert(eta(handle,ids,2,NULL)==ERR(10));
    assert(eta(handle,ids,0,&remaining)==ERR(11));
    assert(eta(handle,ids,UINT32_MAX,&remaining)==ERR(11));
    ids[1]=3;
    assert(prefetch(handle,ids,2,3)==ERR(12));
    assert(eta(handle,ids,2,&remaining)==ERR(12) && remaining==INT64_C(0x123456789abcdef));
    ids[1]=UINT16_MAX; assert(prefetch(handle,ids,2,3)==ERR(12));
    ids[1]=0; assert(prefetch(handle,ids,2,3)==0); /* duplicates are valid */
    assert(close(handle)==0 && close(handle)==ERR(9));
    assert(eta(handle,ids,2,&remaining)==ERR(9));
    assert(open(&handle,NULL)==0 && term()==0 && term()==ERR(5));
    assert(eta(handle,ids,2,&remaining)==ERR(5));
    assert(init(&params)==0 && open(&handle,NULL)==0 && term()==0);
    puts("PASS: real PlayGo resolver, ABI, contracts and file I/O");
    return 0;
}
