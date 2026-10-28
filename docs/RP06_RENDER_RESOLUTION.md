# Internal rendering resolution — Resolution Preview

The launcher now offers **Original, 720p, 900p, 1080p, 1440p and 4K** for
CUSA01047 USA 01.00. This changes the native scene-buffer dimensions. Output
resolution continues to control host presentation independently. All explicit
internal modes are experimental and require a game restart.

| Internal setting | Scene dimensions | Half-size targets | Quarter-size targets |
| --- | --- | --- | --- |
| Original | Game-controlled | Game-controlled | Game-controlled |
| 720p | 1280 × 720 | 640 × 360 | 320 × 180 |
| 900p | 1600 × 900 | 800 × 450 | 400 × 225 |
| 1080p | 1920 × 1080 | 960 × 540 | 480 × 270 |
| 1440p | 2560 × 1440 | 1280 × 720 | 640 × 360 |
| 4K | 3840 × 2160 | 1920 × 1080 | 960 × 540 |

These are native allocation **requests verified in isolation**, not captured GPU
frames. 4K contains four times as many scene pixels as 1080p; this does not predict
frame rate or total memory use. No minimum VRAM capacity or 4K stability result has
been established across hardware. Original removes the override rather than forcing 1080p.


## V1.7 investigation: black world at explicit resolutions

[Issue #19](https://github.com/shehab4546/RatchetPort/issues/19) reports a black
3D scene at 1440p/4K while HUD/menus remain visible, with confirmations on RTX
5080 and RX 7900 XTX. The supplied 4K logs confirm the override was applied;
they did not identify the failing render pass. **Update, 28 October 2026: I
verified that the black 3D world is corrected in gameplay at both 1440p and 4K.**
This closes the reported symptom in #19; it does not establish every scene, GPU
or long-session configuration. No resolution option has been removed.

The latest four-flip captures identify zero native color-target bases and formats
with color mode and write masks enabled. Isolated execution reproduces that
packet state when the native resource allocator returns zero. The allocator's
failure logger is a no-op in the retail binary; available host VRAM does not
establish free space in the game's separate 1165 MiB XMemGpu heap.

The experimental correction couples the verified resolution transaction with a
larger XMemGpu reservation and a failure-only printf redirect. 1440p uses a
1549 MiB heap and a 5440 MiB direct pool floor; 4K uses 1933 MiB and 5824 MiB.
These are bounded trial capacities, not measured minima. Windows commit grows
by 384/768 MiB. The native alignment/reservation path stays intact; Original and
720p/900p/1080p keep the retail heap policy. A rejected high-resolution transaction
cannot prepare its memory floor. Manual larger direct-pool overrides remain in
force, including after restart to Original.

The black-world correction is now gameplay-verified at 1440p and 4K; the
capacities remain experimental for broader hardware and scene coverage.
The selector, heap lookup and logging writes share the exact source/ELF,
original-byte, unique-signature and relocation guards. No MSAA, display-output
or host color-binding override is introduced. See
[evidence/issue19-paired-captures.md](evidence/issue19-paired-captures.md) for
addresses, captures, native probe coverage and remaining uncertainty.

### Captured evidence

Diagnostics are on by default for this investigation, including Original, and
can be disabled with `RATCHET_RESOLUTION_DIAGNOSTICS=0`. They do not depend on
`RATCHET_GPU_LOG=info` (the default warning filter hid the old observations).
`last_run.log` identifies the diagnostic version and records:

- Relevant native-size image creation/unregistration with a unique image ID,
  address, dimensions, layers, mip count, format, guest/host samples, pitch,
  tile mode, descriptor byte size, host Vulkan memory requirement/alignment and
  actual VMA allocation size. Unregistration does not imply immediate host destruction.
- Cache lookup requests against reused/new images, including mip/slice views.
  Repeated addresses with different IDs expose recreation; a difference between
  a view and its backing image is not automatically an error.
- Render/depth/sample/storage bindings and shader hashes, GPU mapped coverage,
  overflow-checked uncompressed base-level byte lower bounds, and partial mapping.
  GPU registry coverage is **not** the original guest heap allocation size. It
  must not be used as proof of an allocation overflow or as a fatal assertion.
- Render area, attachment identities and samples, viewport/scissor, copy/resolve
  source/destination dimensions, and cache logical bytes separately from measured
  driver heap usage/budget. Existing adaptive-GC reports cover bounded scan and
  eviction counts; they are not a census of all evictable images.

Each category deduplicates records and has a hard per-process budget: resource
256, binding 256, pass 128, viewport 64, transfer 64, mapping 64, failure 32,
lookup 128 and cache 32. A limit notice marks truncated coverage. Resource
filtering includes full/half/quarter/eighth families and padded dimensions; it
does not identify an image as TAA/history, GI, motion vectors or display output.
Those roles remain **unclassified** until shader/control-flow evidence identifies them.

The first screen-sized depth pass exporting at least three colors requests one automatic resource graph
in `user/captures/` (or the configured capture directory), without dumping
constant buffers. The Graphics panel also offers **Capture graphics frame** for
the failing scene. Captures include ordered graphics/compute passes,
sampled/storage addresses, geometry, sample counts and color-binding registers.
They record across four presentation flips, with a hard limit of 512 entries.
Reaching that entry limit marks `capture_truncated=1`. The file declares
`capture_scope=multi-flip-window`: this is not an exact game-frame boundary.
Repeated display-buffer writes do not stop recording; UI/composition can write
those buffers multiple times before world rendering. A capture is metadata,
not a screenshot or proof of correct pixels. If no candidate is detected, use
the manual capture button. The trigger does not update observed scene dimensions.

Skipped shader color exports log their address, format, write mask and color mode
under the bounded failure channel. Disabled writes can be intentional; these
records do not establish an allocation failure. See
[the paired RTX 5070 capture analysis](evidence/issue19-paired-captures.md).

The Graphics panel separates requested/prepared startup dimensions from the last
observed scene/depth candidate and viewport, marks mismatches, reports raster
samples and logical cache size, and leaves temporal/history explicitly unidentified.

### Runtime comparison required

Keep the save, camera, output size, blur, shadows and frame-rate setting identical.
Restart for each of Original, forced 1080p, 1440p and 4K; preserve each run's log,
`ratchet.ini`, screenshot and capture under a different name. Then repeat 1440p
and 4K with guest multisampling off/on. Disabling it is an isolation test, not a fix.
The next review must verify the logged heap reservation and allocation failures,
then compare matching shader/address relationships through scene, resolve and
post-processing to establish whether the native capacity correction restores color targets. Smaller images may be legitimate derived
or display-size targets; dimensions alone do not justify resizing them.

### Implementation files

- `gpu/shim/ratchet_resolution_diagnostics.h`: bounded, thread-safe event deduplication,
  screen-family filtering and checked diagnostic arithmetic.
- `texture_cache/image.cpp` and `texture_cache/texture_cache.cpp` under
  `gpu/shadps4/video_core/`: creation/allocation, cache identity/lifecycle and usage records.
- `renderer_vulkan/vk_rasterizer.{h,cpp}` and `vk_runtime.cpp` in the same directory:
  mapped coverage, pass/binding geometry and copy/resolve relationships.
- `renderer_vulkan/vk_frame_capture.{h,cpp}`: richer resource metadata, bounded capture,
  and automatic resource-only recording; `gpu/shim/ratchet_{overlay,resolution,settings}`
  files expose requested/observed values and capture controls.
- `tests/test_resolution_diagnostics.cpp`, `tests/test_frame_capture.cpp`,
  `gpu/CMakeLists.txt` and `.github/workflows/windows-zip.yml`: regression coverage and CI.

### Verification boundaries

- Source SHA-256 and reconstructed ELF SHA-256 were rechecked against the profile.
- On the current V1.7 code, the isolated selector/resize probe passed 50 selector
  cases and 160 native allocation requests; 96 graphics combinations passed
  fingerprint/original-byte/relocation and conflict checks (559,629 relocation slots).
- Native diagnostic tests cover all five size families and derivatives, MSAA/layer
  byte arithmetic, overflow/invalid ranges, requested-versus-observed dimensions,
  concurrent deduplication and log limits. Frame-capture tests exercise bounded
  recording without a display boundary. Graphics-settings tests passed.
- The Python suite ran 552 tests: 445 passed, 103 skipped, with the same four
  previously recorded Linux-only/environment baseline failures (WindowsPath mocks,
  Windows drive-path packaging, and a stub missing `prepare.load_sfo`).
- The earlier diagnostic build `b0cdfe7` passed Windows run 40394941135.
  Windows validation of the new heap-capacity change is pending CI. The new native
  probe passes six heap-init cases, allocation-failure logging and 30 texture/view/packet
  cases; the C memory-floor test passes 12 process-start cases.
  Successful high-resolution gameplay remains unverified.

## Implementation evidence

The exact source and ELF fingerprints are listed in
[evidence/ratchet-cusa01047-0100-resolution.json](evidence/ratchet-cusa01047-0100-resolution.json).
No UPDATE 01.09 addresses, Neo flags or VideoOut resolution patches are imported.

- BASE selector `0x178b4a0` returns a success flag in AL and writes width through
  RSI and height through RDX. Its only direct caller is `0x183e06f`. A 26-byte,
  whole-instruction replacement sets the selected dimensions and returns true.
  Each mode has a unique-source signature, original-byte check and exact binary
  fingerprint guard. Conflicting resolution groups are rejected together.
- The caller aligns dimensions to four pixels, compares them with the current
  shared buffers, synchronizes and calls `ResizeSharedBuffers` at `0x177e330`
  through `0x183e1a5`. All five offered sizes are 16:9 and already four-aligned.
- Resize updates width/height at manager offsets `0x263c`/`0x2640`, releases the
  old shared resources and calls `0x177ccc0` to recreate them. Repeating the same
  dimensions skips recreation. A scene reset can restore the game's defaults;
  the frame selector remains overridden until the next process starts.
- Native creation passes the selected dimensions to depth, linear depth,
  forward, G-buffer, resolved, post-effect and GI targets. Half-, quarter- and
  eighth-size derivatives are computed by the original code. Auxiliary cubic
  output retains the display width; it is not incorrectly counted as a full
  scene-resolution target.
- The caller separately updates the display rectangle via `0x17b7d10`. On the
  successful-selector path its flag is zero and the original display dimensions
  remain in use. Host window/output and final presented image need not equal
  the scene dimensions.

The isolated x86-64 experiment executes the actual selector and native
resize/creation control flow. GPU/resource dependencies are stubbed to record
allocation requests and populate the resource dimensions consumed by later
requests. It checks 50 selector cases, 160 target requests across five modes,
release/recreate versus unchanged-size behavior, and Original restoration.
It does **not** allocate real GPU surfaces or execute shaders. The separate
profile check covers all 96 combinations with frame-rate, blur and shadow
settings and the dump's relocation slots.

No heap-size patch is included. The native buffer builder's allocation tracking
is retained. Successful request arithmetic does not prove that guest heaps or
host VRAM can satisfy all requests in a real scene.

## Settings and runtime verification

`internal_resolution` is independent of `output_res` and the inherited
`render_resolution` option. Missing or invalid values become Original. Saved
patch names cannot override this explicit setting. Only a prepared reviewed
group supplies `RATCHET_INTERNAL_RESOLUTION`; rejected preparation reports
Original. The native loader must accept the patch transaction before guest entry.
Original starts from a fresh unmodified image. Saving from the overlay preserves
the requested internal setting, including when preparation falls back.

The in-game Graphics information panel separates:

- **Internal resolution (startup):** the prepared launch mode, not a measurement.
- **Scene candidate / depth:** the last draw with at least five active, equally
  sized color targets and matching depth, observed independently of upscaling.
- **Scene candidate viewport:** that draw's viewport dimensions.
- **Presented game image** and **Window:** the final image and host window.

Candidate identification is a heuristic. Menus may produce no candidate; the
panel then says **Not observed yet**. A previous sample stays labeled as the last
matching draw. Logs record at most 16 distinct size/viewport combinations; they
never substitute the selected resolution for a missing observation. A matching
sample does not identify or validate temporal history.

## Gameplay acceptance still pending

On the same save and camera position, compare Original against 720p, 900p,
1080p, 1440p and 4K, restarting between choices. Keep output fixed first to isolate
scene detail, then compare with 4K output on a suitable display. Record the
startup mode, observed target/viewport dimensions, screenshots and frame times.

Check gameplay, scene transitions, cutscenes, HUD/text placement, transparency,
depth of field, blur and any temporal reconstruction/history behavior. Look for
cropping, black edges, ghosting, stale frames, device loss and allocation errors.
Repeat scene changes and restore Original to check recovery. If 4K fails, return
to Original or a lower internal setting and restart; keep the failing run log.

The supplied BASE build's temporal-history dimensions have not been independently
measured. History, viewport observations, visual correctness, memory headroom and
sustained performance remain gameplay acceptance gates. This preview makes the
controls available for testing; it does not close those gates.
