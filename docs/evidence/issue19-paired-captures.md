# Paired Original and 4K captures — RTX 5070 Laptop

The October 26 reports pair `frame_20261026-230916_1.txt` with the 4K startup override and `frame_20261026-231200_1.txt` with Original. Both sessions selected the RTX 5070 Laptop GPU and exited with code 0. The running build includes resolution diagnostics; the exact executable commit is not recorded in these logs.

## Confirmed difference

For the shared shader pair VS `202a23e2` / PS `81f2d46d`, both runs export three colors (`mrt=0x7`). Original binds three 1920x1080 color targets and depth. The 4K run records 3840x2160 depth with no bound color targets. Forty-five three-export shader pairs occur in both logs: all 45 have no recorded color bindings in 4K, while 44 have all three bindings in Original. The remaining Original line is not counted as complete.

This localizes a reproducible binding difference. It does not prove which register gate or earlier resource-creation step caused it. `PrepareRenderState()` can skip color bindings for disabled color mode, an invalid descriptor (zero base address or format), or a zero per-target write mask. The previous diagnostics did not record those gates. Forcing bindings or removing the guards would therefore be unjustified.

## Capture defect

The supplied files contain only eight and eleven entries, primarily display and 256x256 targets. Neither includes the main offscreen world rendering. The old recorder treated each new single-display-target pass as a frame boundary; a second UI/composition write ended capture prematurely even though `capture_truncated=0` was reported. The flag described only limit truncation, not verified completeness of a game frame.

The recorder now starts at the first GPU-thread poll after arming and records a bounded four-presentation-flip window, capped at 512 entries. It declares the capture scope explicitly and does not finish on display writes. Geometry/state changes on otherwise identical attachments remain distinct entries. Automatic capture accepts a screen-sized depth pass with three or more shader color exports, even when the color bindings are missing; this does not classify it as a verified scene observation.

Both the default log and capture now retain color mode, base address, format and write-mask evidence. This is a diagnostic correction, not a claim that 4K rendering is fixed.

## Validation and remaining evidence

The native frame-capture regression test covers repeated writes to the same and alternate display buffers before an offscreen world pass, changed geometry on the same target, four-flip completion, the 512-entry limit, subsequent capture recovery, compute-only capture and idle callbacks. No Vulkan device is required by this test. Windows build validation and a fresh affected-hardware run remain necessary.

The first captures did not establish a memory-exhaustion cause. Unmapped-region warnings also occur in Original, so their presence alone does not identify the cause of black output.

## Follow-up: missing native backing allocations

The four-flip captures now include the main world passes. In
`frame_20261026-235547_1.txt`, all 16 three-export passes have enabled color mode,
write masks `0xf`, and zero base/format for all three color targets. In
`frame_20261026-235908_1.txt`, all 12 corresponding three-export passes have
nonzero bases, formats 9/10/10, and all three bindings. Neither file hit the
512-entry limit. These observations put the failure before Vulkan attachment
selection; forcing host bindings would not supply valid backing memory.

The earlier 4K startup log maps XMemGpu at `0x1080000000` with 1,221,591,040
bytes (1165 MiB). This is the game's fixed resource heap, separate from available
driver VRAM. Native analysis of the fingerprinted BASE executable shows:

- `0x19086b0` obtains the XMemGpu size through the call at `0x1908724`, aligns
  it, reserves direct memory, then initializes the heap at `0x4edb9a8`.
- The allocation path at `0x1908830` returns zero on exhaustion. Its error
  message goes to `0xeb3e20`, a no-op logger in this binary.
- Texture creation `0x17b0680` and view creation `0x17b2460` can both return
  success even with a zero backing address. The native command writer at
  `0x21364a0` then emits a zero CB_COLOR_INFO instead of the target registers.
  This reproduces the zero-format gate in the captures.

## Experimental capacity correction

1440p now prepares a 1549 MiB XMemGpu heap and a minimum 5440 MiB direct pool;
4K prepares 1933 MiB and 5824 MiB respectively. The additional 384/768 MiB is
bounded investigation headroom, not a measured minimum or proof that every
level fits. Both heaps remain below the native 2 GiB virtual-address slot.
High-resolution modes replace only this heap's size lookup; native alignment,
mapping and heap setup remain in use. Original and modes through 1080p keep the
retail heap policy. Windows startup commit increases by the selected extra
amount; this is not a reduction in RAM use.

Each high-resolution group atomically verifies the selector, heap-size write,
and failure-log call. The last write routes the existing allocator failure
arguments to the native printf PLT (`0x2c88338`), exposing heap, resource label
and requested bytes in the log. Original restores all three sites on a fresh
launch. A separate derived `RATCHET_RESOLUTION_DMEM_MB` floor preserves manual
`RATCHET_DMEM_MB` overrides across Apply and restart.

`python tests/probe_resolution_heap.py /path/to/eboot.bin` requires the exact
private dump and runs on Linux x86-64. It passed six native heap initialization
cases with 16/64 KiB pages, the allocation-failure logging ABI/NULL-result check,
and 30 real texture/view/command-packet cases with successful and failed backing
allocations. OS/GPU dependencies are stubbed; this does not execute shaders or
replay a level's allocator history. Profile checks passed 96 graphics combinations
against 559,629 relocation slots. Eight negative checks at the two new sites
reject the entire group on byte/relocation mismatch. The C pool test covers 12 separate starts,
including a larger manual override and removal of the derived floor.

The evidence supports guest heap exhaustion as a concrete hypothesis. It does
not yet prove it caused the captured session or establish a successful 4K image.
Windows build and affected-hardware gameplay validation of this capacity change
remain pending. The earlier diagnostic build `b0cdfe7` completed successfully
in Windows run 40394941135.
