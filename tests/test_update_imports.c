/* Real runtime resolver, kernel and file backends; no GPU or game image needed. */
#undef NDEBUG
#include "runtime.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

typedef int32_t (ABI *Query)(void);

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
    puts("PASS: update console queries and exact SDK aliases");
    return 0;
}
