# RP-01 baseline validation

Recorded 22 October 2026. **Build and automated verification passed; gameplay
acceptance remains pending.** This is a development baseline, not a new gameplay
compatibility claim or a replacement release.

## Source and build

- Base: `bee97d693fce069ce53a3a09334585e4cbb1973b` in `shehab4546/RatchetPort`.
- All submodules checked out at the revisions pinned by that commit. The FSR
  worktree was checked against the three tracked `gpu/patches/fsr-vulkan` patches;
  all six affected files matched. No submodule reference changed.
- Windows 11 Pro 10.0.26300, Intel Core i5-12400, Intel UHD Graphics 730,
  driver 32.0.101.7088, approximately 12 GB RAM.
- MSYS2 CLANG64: Clang 23.1.3, CMake 4.4.4, Ninja 1.13.2.
- Fresh `RelWithDebInfo` build, PGO off, LTO off, two parallel compile jobs.
- Built `ratchet-probe`, `ratchet-gpu-capabilities`, `ratchet-play`, and all 47
  native test targets. Dependencies came from the local CLANG64 installation.

Git's CRLF conversion initially prevented the supplied FSR patches from applying.
The isolated submodule's patch targets were normalized to LF; global Git settings
were preserved. The local build helper also stripped CR from Python-generated
target names before passing them to Ninja. No renderer changes were needed.

## Fresh-checkout test repair

`churn-trace-test` reached its analyzer checks and then failed because its Python
harness imported an untracked developer-only path,
`ratchet_opt10_stability/analyze_churn.py`. The tracked replacement is now
[`scripts/analyze_churn.py`](../scripts/analyze_churn.py).

The analyzer verifies image/producer row counts, upload totals and writer
attribution. It excludes incomplete or inconsistent windows. The production-trace
harness covers missing rows, duplicate image and summary rows, altered totals,
dropped producer events and empty logs. Windows CI now builds and executes that
harness as well. Producer associations describe declared writers, not proof that
the GPU changed the contents of a resource.

## Local verification

| Check | Result |
| --- | --- |
| Full Python discovery | 463 discovered: 416 passed, 47 skipped, zero failures/errors |
| Native runner after the analyzer repair | 47 passed, zero failures, zero skips |
| Liverpool command harness | Pending, late-arrival, callback-arrival and startup cases passed |
| CPU feature check | Complete; exit 0 |
| Live scene-scaling capability | Unsupported: D32S8 blit support absent on this GPU; left disabled |

Python skips: 29 inherited native-path checks, 12 platform/symlink checks, four
ZIP smoke tests requiring a packaged artifact, and two ultrawide-tool checks.
For the last two, the inherited skip message says capstone is absent, but capstone
was installed: `tools/make_ultrawide_patch.py` is missing from this checkout.
Skipped tests are not counted as passes. Native and Python totals are separate.

The zero-clear GPU test used an existing, local captured shader read-only; it is
not distributed. Decoder fixtures passed with local MSYS2 FFmpeg DLLs. This does
not establish audible correctness or validate a final package's LGPL dependency
set. No distributable ZIP was produced as part of RP-01.

## Short runtime check

Target: CUSA01047 USA 01.00, with 72 PlayGo chunks initialized. The original dump
was read-only; settings, preparation output, caches and saves used a separate
local profile. No game-byte patches or mods were applied.

Settings: 30 FPS limit, VSync on, 1280x720 **output**, upscaling off, linear
readback on, deferred readback off, zero-clear mirror off. Output dimensions do
not establish a change to internal rendering resolution. Frame diagnostics were
enabled.

The unattended session lasted **109.531 seconds including preparation** and
exited with code 0 after a normal window-close request. The log contains rendered
frames and no Device Lost or Unsupported Prefetch message. No visual inspection
or interactive gameplay route was performed.

There were 20 reported frame-statistics samples: 20.1–30.0 FPS, median 30.0.
Per-window median frame times ranged from 31.64 to 33.45 ms; the largest reported
p99 was 279.28 ms during boot. These are boot-rendering samples, not a gameplay
benchmark, a time-weighted average or evidence of sustained combat performance.

Audio buffers and ATRAC9 decoding were logged, but sound was not assessed by a
listener. Save mounts were zero; save/load was not tested. Metadata for all 58
original game files and hashes of the five critical boot/metadata/module files
remained unchanged. Raw logs, local paths, game-derived data and private captures
are excluded from this repository.

## Remaining acceptance

- Actual movement, camera control, jumping and combat on a recorded route.
- Audible music, effects and dialogue assessment.
- A save/load round trip that restores real gameplay progress.
- A proposed 30-minute repeatable gameplay session, with start/end scene and
  settings recorded; diagnosis of any crash before relying on performance data.

The tester was unavailable for gameplay validation. RP-01 therefore remains
pending that acceptance. Higher FPS, motion blur, internal-resolution changes and
keyboard/mouse stick customization belong to subsequent tasks.

## Reproduce the automated checks

Follow [the Windows build instructions](../packaging/windows/README.md), keep the
FSR patch targets at LF, and use a new build directory. Build every `*-test`
target declared in `gpu/CMakeLists.txt`, then run the Python suite, Liverpool
harness and `tests/run_native.py` against that directory. Supply a local captured
shader only when available; otherwise retain the explicit zero-clear skip.

To reproduce the repaired trace test after building `churn-trace-test`:

```powershell
out/ratchet-tools/Scripts/python.exe tests/test_texture_churn_trace.py out/ratchet-clean/churn-trace-test.exe
```

The local run reported above used the baseline products built from the pinned
base commit plus the diagnostic analyzer/harness repair. CI results for this PR
are independent checks and should be read from the Actions run itself.
