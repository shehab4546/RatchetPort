/* Boundaries unrelated to PlayGo. Never replace runtime_resolve, runtime_symbol,
 * runtime_lookup, runtime_services_resolve or runtime_file_* in this test. */
#include "runtime.h"
#include "gpu/ratchetgpu.h"
#define RESOLVER(name) uintptr_t runtime_##name##_resolve(const char *nid) { (void)nid; return 0; }
RESOLVER(mutex) RESOLVER(thread) RESOLVER(content) RESOLVER(time) RESOLVER(sema)
RESOLVER(event) RESOLVER(rwlock) RESOLVER(memory) RESOLVER(kernel) RESOLVER(netctl)
RESOLVER(ajm) RESOLVER(videodec) RESOLVER(audio) RESOLVER(pad) RESOLVER(rtc) RESOLVER(savedata)
#define REPORT(name) void runtime_##name##_report(void) {}
REPORT(thread) REPORT(mutex) REPORT(rwlock) REPORT(sema) REPORT(event) REPORT(content)
REPORT(netctl) REPORT(memory) REPORT(ajm) REPORT(audio) REPORT(pad) REPORT(savedata)
uintptr_t ratchetgpu_resolve(const char *nid) { (void)nid; return 0; }
static int32_t guest_errno;
int32_t *runtime_errno(void) { return &guest_errno; }
int runtime_guest_errno(int value) { return value; }
int ratchetgpu_text_input_begin(const char *text,const char *prompt) { (void)text; (void)prompt; return 0; }
int ratchetgpu_text_input_poll(char *text,uint64_t size) { (void)text; (void)size; return 0; }
int ratchetgpu_choice_begin(const char *title,const char *const *items,const char *const *images,int count,int focus) {
    (void)title; (void)items; (void)images; (void)count; (void)focus; return 0;
}
int ratchetgpu_choice_poll(void) { return -1; }
int runtime_savedata_param(int32_t user,const char *dir,void *param) { (void)user; (void)dir; (void)param; return -1; }
int runtime_savedata_icon(int32_t user,const char *dir,char *out,size_t size) { (void)user; (void)dir; (void)out; (void)size; return -1; }
