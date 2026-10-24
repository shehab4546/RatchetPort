# RP-02: CUSA01047 / 01.00 static evidence

Static analysis of the target build is complete for the three requested
paths: frame interval/clock, motion-blur gate, and internal-resolution selector.
This is **not gameplay acceptance or a working 60 FPS/blur/resolution patch**.
All runtime capabilities remain disabled. RP-03 supplies guarded patching;
RP-04/05/06 implement and test the respective features.

## Build identity and reproducibility

The analyzed plaintext SELF is 79,129,828 bytes. Its matching SFO identifies
Ratchet & Clank, CUSA01047, APP_VER 01.00, CONTENT_ID
UP9000-CUSA01047_00-RCPS400000000000. These are the target build's labels;
metadata and a locally calculated hash do not independently authenticate an
unmodified retail dump. This evidence applies to **these exact bytes only**.

| Input | SHA-256 |
| --- | --- |
| Source SELF | `fdf72d683f305ab1a70adfe246e9ac1dbbd4ceb988b1327157b6bda55476697d` |
| Parsed ELF | `dc1a8862016cb80060928e911ab933d6e380014c1128e537642f9f569f3a05cf` |
| param.sfo | `838cfd8b1c0d9ecf3dbf1900cc10d822ce5e68d661cfda85d45e47f0ff02b1b4` |
| pkg_settings.set | `1204efa2621aaae040a05352fa74d2e855b96a80fb57ac6ed2ff0b09dc73b57f` |

The checked-in candidate manifest records eleven unique 32-byte signatures,
original instruction bytes, executable consumer anchors and initialization notes.
The static-check report records their independently translated coordinates.
The capability registry records research status separately from runtime support.
No source game files, extracted ELF, full disassembly or private diagnostics are
included. The short byte signatures are solely compatibility evidence.

Reproduce the mechanical checks against the target dump:

```powershell
python scripts/ratchet_binary_audit.py --game-dir "C:/path/to/CUSA01047" --manifest docs/evidence/ratchet-cusa01047-0100-candidates.json --output rp02-check.json
```

The tool intentionally reports semantic review required and rp02_complete false:
it cannot infer semantics or grant acceptance from a byte match. This document
records the separate disassembly review. A successful check never enables a
feature. Disassembly was inspected with Capstone 5.0.7; the audit command itself
needs neither Capstone nor NumPy.

All addresses below are **ELF virtual addresses / prepare.py pre-link offsets**,
not host pointers, SELF offsets, or an assumed 0x400000-based patch address.
For the RX segment, ELF file offset = address + 0x4000; SELF offset = address +
0x1c9f0. Other segments must use their own program-header mappings. Runtime
relocation and later ISA rewriting are separate steps; apply source evidence
before transformations or explicitly revalidate transformed instructions.

## FPS

1. The render-settings constructor at `0x17884e0` writes float **2.0** at
   settings +0x24 (`0x1788536`), and float **7.0** at +0x28. Renderer setup
   copies these to frame state +0x1c/+0x20 at `0x17b7669`/`0x17b7673` and sets
   +0x24 true at `0x17b7678`. The frame-state singleton is `0x4a49a60`.
2. Display creation initializes its base period to bits `0x3c88ac0c`
   (approximately 0.01668360084 seconds) at `0x1907e31`. Setup copies it into
   frame state +0x18 at `0x17b76f4`.
3. The per-frame wait path `0x17b78a0` reads that period and interval. When the
   state flag +0x24 is false it takes max(interval, alternate interval), rather
   than simply the normal interval. It converts the product to TSC ticks using
   sceKernelGetTscFrequency and calls the deadline-wait routine at `0x17b7a69`.
   Normal constructor values therefore imply about 33.3672 ms, not an exact
   30.000 Hz claim. This is guest pacing, separate from host caps or VSync.
4. Clock initialization `0x171e710` uses the same period-times-interval and
   caller-supplied limits. `0x171e7a1` takes a maximum with the caller minimum;
   the resulting lower/upper bounds go to clock +0x40/+0x48. Renderer init
   (`0x18710c7`) precedes clock init (`0x18713e1`) in `0x1871000`.
5. Tick routine `0xe6c760` reads sceKernelReadTsc, subtracts the starting counter,
   divides by stored frequency, limits the elapsed delta, optionally smooths
   history, applies the minimum at `0xe6c7f3`, and scales time before writing
   +0x38 at `0xe6c806`. Changing the wait interval after clock initialization
   can leave the old minimum active and speed up simulation.
6. The game-time update `0x171e9d0`, called at `0x183dfcd`, separately accumulates
   deltas. RP-04 must preserve this relationship, pause/slowdown behavior, audio,
   cutscenes and the alternate throttle; the static trace does not prove them.

Import identity was resolved from the binary's symbol/NID and relocation tables:
sceKernelGetTscFrequency uses GOT `0x3a6c618`, stub `0x2c88188`;
sceKernelReadTsc uses `0x3a6c620`, stub `0x2c88198`.
The VideoOut flip-rate call at `0x1908205` already passes **zero** in ESI.
Its import is sceVideoOutSetFlipRate (`0x3a6cc00`, stub `0x2c88d58`). It is
not a demonstrated interval-two patch site and is not the identified FPS control.

## Motion blur

The `MotionBlurEnable` string at `0x2f08a32` is linked through relative ELF
relocations: field-name slots `0x3e0fd28` and `0x3e0fda8` refer to that string.
The type descriptor at `0x3e0fef8` has size 0x18 and three fields; its name-array
pointer at `0x3e0ff18` refers to `0x3e0fd20`. The field names are RenderEnable,
MotionBlurEnable and WindowTitle. The offset array at `0x3b10a30` is **0, 1, 8**.
These pointers are relocation addends, not populated pointers in the raw SELF.

Descriptor function slots identify the allocating constructor `0x1a9a220` and
reset/default function `0x1a9a360`. Their writes at `0x1a9a286` and `0x1a9a38c`
set the first two bytes to 1 (word 0x0101). Registration at `0x1a9aaa6` names the
section Render and binds the global object `0x4ee6cb8`. Config parsing can replace
constructor defaults, so patching only a default is not proof of the final value.

The actual gate is `0x17cb0af`: it loads that global, compares **byte +1** to
zero at `0x17cb0b6`, combines the result with another disable condition, and
clears render-state float +0x200a4 at `0x17cb0c8` when disabled. A downstream
consumer at `0x176c349` reads that float, checks positive strength, applies a
frame-time-dependent scale, and stores the resulting value at +0x290. Another
consumer is `0x183c12b`. This establishes a live data path beyond the string.
The relevant gate runs during render-state preparation, after configuration.

The pkg_settings.set assignment `MotionBlurEnable = false` occurs at
line 428 **inside ?sceneeditor**, whose block starts at line 398. It is not
proof that normal gameplay disables blur. Shader labels alone also do not prove
this. RP-05 must test object/camera motion, rendering artifacts and actual pass
behavior; this evidence does not promise every blur-related shader is skipped.

## Internal resolution

The selector is read from `0x4a3d660 + 0x0c` at `0x183e064` and passed to
`0x178b4a0` at `0x183e06f`. That helper checks modes 1 through 6 and uses the
relative jump table at `0x178b510`:

| Mode | Width × height | Case address |
| --- | --- | --- |
| 1 | 320 × 240 | `0x178b4ba` |
| 2 | 640 × 480 | `0x178b4c8` |
| 3 | 1280 × 720 | `0x178b4d6` |
| 4 | 1600 × 900 | `0x178b4e4` |
| 5 | 1920 × 1080 | `0x178b4f2` |
| 6 | 1920 × 800 | `0x178b500` |

Other values return false; the caller falls back to existing dimensions at
object +0x2644/+0x2648. The selector is in BSS, so it has no source-file byte
that can safely be patched by pretending its virtual address is a SELF offset.
Its initial zero-filled state is not a claim about the final configured mode.
There are later writers, including `0x18b56a2` (5), `0x18b56b5` (4), and
`0x18b56d4` (3). The per-frame read is after these configuration/command paths;
RP-03/06 must choose an override point that remains effective after those writes.

The caller aligns selected dimensions to four pixels at `0x183e140` and calls
`0x177e330` at `0x183e1a5` when needed. That routine stores width/height in
+0x263c/+0x2640 (`0x177e37f`), calls the buffer-release path `0x177e110`, then
creation `0x177ccc0`. Creation reads those same dimensions at `0x177ccf0`.
The associated diagnostic string identifies **RenderBuffers::ResizeSharedBuffers**.
This is a shared rendering-buffer path, separate from display-output creation.
Actual bound render targets, viewport, HUD and output dimensions still require
RP-06 runtime verification, especially across scene changes.

Two misleading alternatives were excluded:

- `0x1907c0f` initializes 1920×1080 **display** dimensions later passed to
  VideoOut setup; it does not independently prove internal resolution.
- The table at `0x3b03d70` contains 0, 4:3, 16:9, 2.4. Its selector at
  `0x183e0c4` is an **aspect-ratio** path, not 720/900/1080 resolution modes.

No Neo/1.09 mode or signature is inferred from these base-game paths.

## Validation and handoff

Eleven candidate signatures were each found exactly once across every
file-backed PT_LOAD/SCE_RELRO segment. Original bytes and executable consumer
bytes matched both parsed ELF and translated SELF offsets. The originals were
read only. The committed static-check JSON is reproducible from the manifest.

The 27 new synthetic audit tests passed. A broader local Linux run executed
490 tests: 388 passed, 98 skipped, three errors and one failure. All four
failures were reproduced unchanged on baseline `8ea873c`: WindowsPath emulation
in test_game_update/test_mods, the Windows-drive packaging audit, and the legacy
fake-probe launcher fixture. These are not introduced by this PR; Windows CI is
reported separately on the pull request. No native/gameplay execution is claimed.

Static research is sufficient to design the following tasks, but its registry
is deliberately not loaded by the launcher or patch installer. There is no new
60 FPS, blur toggle, internal-resolution UI, tearing fix or cutscene-stutter fix
in this change. Do not publish a new gameplay test build merely for this report.

RP-03 must reject unknown hashes and original-byte mismatches, avoid source/BSS
coordinate confusion, preserve rollback, and account for prepare/link/ISA order.
RP-04/05/06 must separately validate the resulting behavior during gameplay on the test machine.
The static analysis uses eboot.bin, param.sfo and pkg_settings.set; additional
proprietary modules are not required for RP-02.
