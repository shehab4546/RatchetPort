# Red zone on Windows

## Symptom

On Windows, animated meshes show long spikes and
flicker, while static geometry is correct (#25; shadPS4 #3658 reports the same for shadPS4). In some
configurations (30 FPS, or the process limited to fewer cores) the game also crashes on every load:

```
Fault: write access to 0000000000000054 at guest offset 0x1830a81
```

The same PC under Linux does not show either problem. Timing changes (Windows 7 compatibility mode,
affinity, fewer write faults via `RATCHET_HOT_PAGES=1`) make both rarer or more frequent.

## Cause

The PS4 code uses the SysV x86-64 ABI. Its 128 bytes below RSP (the red zone) are guaranteed not to
be modified by signal or interrupt handlers, so leaf functions keep temporaries there without moving
RSP. Windows has no red zone: when a thread takes an exception, `KiUserExceptionDispatcher` writes
the exception record and CONTEXT directly below RSP.

The GPU page tracking write-protects guest memory and resolves the resulting access violations on
the guest thread that wrote. Every such fault inside a red-zone function destroys its temporaries.

- `0x1830900` (job worker, parallel-for over items): saves the job context in `[rsp-0x20]`; a fault in
  the loop leaves 0 there and `lock add [rax+0x54], r11d` crashes. The function is a leaf: nothing
  else writes `[rsp-0x20]`.
- `0x1836f20` (vertex skinning): keeps the position scale `1/2^n` in `[rsp-0x18]`, reads it for every
  vertex and writes the result to the vertex buffer the GPU reads. That buffer is tracked, so the
  loop faults almost every frame (RATCHET_FAULT_SITES: >= 26 000 faults per minute in this function
  alone) and every later vertex of the batch is scaled by garbage: the spikes.

## Fix

`scripts/redzone_rewrite.py` (run by `run.py` on Windows after linking) finds the functions in the
eh_frame tables of the image and its modules that address memory below RSP (254 in CUSA01047 v1.00:
eboot, libc.prx, libSceFios2.prx) and relocates the ones it can (231) into a blob after the image:

- `lea rsp,[rsp-256]` on entry, `lea rsp,[rsp+256]` before every exit (ret, tail jump, conditional
  exits through stubs); `lea` keeps the flags.
- every RSP-relative operand +256 and push/pop as `lea` + `mov` at the original slot: all stack data
  keeps its address (pointers into the frame stay valid) and now lies above RSP.
- 256 rather than 128 keeps the low byte of RSP, so the flags of `add/sub rsp` stay bit-identical.

Functions with calls, indirect branches or jump tables stay in place. The skinning function has a
jump table, so `IN_PLACE_FIXES` moves its single red-zone slot to its own stack arguments
(`[rsp+8]`, 16 bytes, read on entry and callee-owned in SysV): two one-byte displacement changes.

`probe --redzone out/redzone.bin` copies the blob after the image, writes `jmp rel32` at each original
entry whose bytes still match (CRC32) and applies the in-place fixes only over the expected bytes.
`RATCHET_REDZONE=0` disables it.

## Verification

- Each relocated function was run natively (Linux x86-64, which honours the red zone) next to the
  original on random register and memory states: all GPRs, RFLAGS, XMM0-15, the written memory and
  the caller frame matched for all 231 functions (30 states each). The skinning fix matched the
  original over 200 states except for the two argument slots it now uses.
- In game: the crash at 30 FPS is gone and the spikes are gone at
  60 FPS, without hot pages, Windows 7 compatibility mode or affinity changes.

## Diagnostics

`RATCHET_FAULT_SITES=1` prints the guest address of write-tracking faults at their 1st, 2nd, 4th, ...
occurrence. Faults in functions that still use the red zone are the ones to fix next.
