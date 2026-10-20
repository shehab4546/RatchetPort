/* Bounded Windows x64 unwind of a saved exception context; no symbol server needed. */
#ifndef GOW3_CRASH_UNWIND_WIN_H
#define GOW3_CRASH_UNWIND_WIN_H
#include <windows.h>
#include <stdint.h>
#include <stddef.h>

typedef struct {
    DWORD64 pc;
    DWORD64 sp;
    DWORD64 image_base;
    DWORD function_begin;
    DWORD function_end;
    int has_unwind;
} Gow3CrashFrame;

static size_t gow3_crash_unwind(const CONTEXT *saved, Gow3CrashFrame *frames, size_t capacity) {
    CONTEXT current = *saved;
    const NT_TIB *tib = (const NT_TIB *)NtCurrentTeb();
    const DWORD64 stack_low = (DWORD64)(uintptr_t)tib->StackLimit;
    const DWORD64 stack_high = (DWORD64)(uintptr_t)tib->StackBase;
    size_t count = 0;
    while (count < capacity && current.Rip && current.Rsp >= stack_low &&
           current.Rsp <= stack_high - sizeof(DWORD64)) {
        DWORD64 image_base = 0;
        /* Later PCs are return addresses: lookup their preceding instruction. */
        const DWORD64 lookup_pc = current.Rip - (count != 0);
        PRUNTIME_FUNCTION function = RtlLookupFunctionEntry(lookup_pc, &image_base, NULL);
        frames[count++] = (Gow3CrashFrame){
            current.Rip, current.Rsp, image_base,
            function ? function->BeginAddress : 0,
            function ? function->EndAddress : 0, function != NULL};
        const DWORD64 old_sp = current.Rsp;
        if (function) {
            PVOID handler_data = NULL;
            DWORD64 establisher_frame = 0;
            RtlVirtualUnwind(UNW_FLAG_NHANDLER, image_base, lookup_pc, function,
                             &current, &handler_data, &establisher_frame, NULL);
        } else {
            /* Leaf functions have no .pdata entry; only their return slot is used. */
            DWORD64 return_pc = 0;
            SIZE_T got = 0;
            if (!ReadProcessMemory(GetCurrentProcess(), (const void *)(uintptr_t)current.Rsp,
                                   &return_pc, sizeof(return_pc), &got) || got != sizeof(return_pc))
                break;
            current.Rip = return_pc;
            current.Rsp += sizeof(DWORD64);
        }
        if (current.Rsp <= old_sp || current.Rsp > stack_high)
            break;
    }
    return count;
}
#endif
