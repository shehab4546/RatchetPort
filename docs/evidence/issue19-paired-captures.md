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

The captured resources do not establish a GPU-memory exhaustion cause. Unmapped-region warnings also occur in Original, so their presence alone does not identify the cause of black output. The next relevant evidence is which color-binding gate differs for the same world shaders.
