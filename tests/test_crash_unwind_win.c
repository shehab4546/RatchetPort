#include <stdio.h>
#include <stdlib.h>
#include "crash_unwind_win.h"

static volatile size_t frame_count;
static volatile int validated;
static volatile size_t exception_frames;

static LONG CALLBACK exception_handler(EXCEPTION_POINTERS *info) {
    if (info->ExceptionRecord->ExceptionCode != 0xe0010007)
        return EXCEPTION_CONTINUE_SEARCH;
    RatchetCrashFrame frames[32];
    exception_frames = ratchet_crash_unwind(info->ContextRecord, frames, 32);
    return EXCEPTION_CONTINUE_EXECUTION;
}

__attribute__((noinline)) static int capture(void) {
    CONTEXT context;
    RtlCaptureContext(&context);
    RatchetCrashFrame frames[32];
    frame_count = ratchet_crash_unwind(&context, frames, 32);
    for (size_t i = 0; i < frame_count; ++i) {
        if (!frames[i].pc || (i && frames[i].sp <= frames[i-1].sp))
            return 1;
    }
    if (frame_count < 4 || !frames[0].has_unwind)
        return 2;
    CONTEXT invalid = context;
    invalid.Rsp = 0;
    if (ratchet_crash_unwind(&invalid, frames, 32) != 0)
        return 3;
    validated = 1;
    return 0;
}

__attribute__((noinline)) static int middle(void) {
    int result = capture();
    validated += 1;
    return result;
}

int main(void) {
    int result = middle();
    if (result || validated != 2) {
        fprintf(stderr, "FAIL: result=%d frames=%zu validated=%d\n", result, frame_count, validated);
        return EXIT_FAILURE;
    }
    PVOID handler = AddVectoredExceptionHandler(1, exception_handler);
    if (!handler) return EXIT_FAILURE;
    RaiseException(0xe0010007, 0, 0, NULL);
    RemoveVectoredExceptionHandler(handler);
    if (exception_frames < 4) {
        fprintf(stderr, "FAIL: only %zu saved-exception frames\n", exception_frames);
        return EXIT_FAILURE;
    }
    printf("PASS: %zu captured frames, %zu saved-exception frames; invalid stack rejected\n",
           frame_count, exception_frames);
    return EXIT_SUCCESS;
}
