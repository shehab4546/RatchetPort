# Test records

## V2.0 preparation — 28 October 2026

I verified that the black 3D world is fixed at 1440p and 4K. This confirms the
symptom in issue #19; this confirmation does not specify a new hardware matrix,
frame-time benchmark or long-session duration.

The preceding candidate passed [Windows build 37](https://github.com/shehab4546/RatchetPort/actions/runs/40662791750),
including native build, Python tests, packaging and the separate package smoke
test. V2.0 changes the release identity and documentation and requires its own
version-matched package build. Silent non-English gameplay voice in issue #31,
RX 570 startup behavior and other open graphics reports are not certified fixed.

## RP-01 baseline — 22 October 2026

The independent source build, automated checks, and a short unattended UHD 730
boot session are recorded in [RP-01 baseline validation](RP01_BASELINE.md).
Gameplay, audible audio, save/load and the proposed 30-minute route remain pending.

## V1.1 PlayGo — RTX 5070 Laptop, 22 October 2026

I observed steady **30 FPS gameplay** on my **NVIDIA GeForce RTX 5070 Laptop GPU**
with the PlayGo update for CUSA01047 USA v1.00. This result comes from my gameplay
observations; it is not an automated frame-time benchmark.

The two runtime logs from 22 October 2026 record:

| Observation | Earlier session | Later session |
| --- | --- | --- |
| Selected GPU | NVIDIA GeForce RTX 5070 Laptop GPU | Same |
| Window / presentation | Fullscreen, VSync on (Fifo), 30 FPS limit | Same |
| PlayGo | 72 chunks initialized, all installed locally | Same |
| Runtime session duration | 621 s (10 min 21 s) | 294 s (4 min 54 s) |
| Exit | Code 0 | Code 0 |
| Input device | Xbox One Controller detected; 18,408 pad reads | Xbox One Controller detected; 8,769 pad reads |
| Unsupported Prefetch / Device Lost | Neither appears | Neither appears |

The durations cover the runtime session, not a measured continuous gameplay
interval. The logs record a 30 FPS limit, not sampled frame rates; steady 30 FPS
gameplay is my observation. CPU model, installed RAM, driver version and
output resolution are not identified in these logs. Audio output and save-mount
counters are present, but do not establish audible correctness or a successful
save/load round trip. Nonfatal Vulkan capability/format warnings remain; the
earlier log also reports an initially missing shader-profile cache file.
Raw logs and local paths are not published. Other GPUs, higher FPS, detailed rendering/audio/controller
checks, save/load and long-session stability are not established by this report.

The [V1.1 PlayGo release](https://github.com/shehab4546/RatchetPort/releases/tag/v1.1-playgo)
contains the package built from `0cd2570f4c2b9778b92df43cfedfaae871299679`.
[Windows CI run #1](https://github.com/shehab4546/RatchetPort/actions/runs/39695590075)
passed the full build, native services test, six PlayGo test methods with the
production resolver, packaging/source checks and a separate package-startup
smoke test without MSYS2 on PATH. Python: **463 discovered; 417 passed, 46 skipped,
zero failures/errors**. These automated checks are separate from my gameplay observations.

## Historical V1 test record

The following record describes local pre-release checks on 21 October 2026. It does not
certify general hardware compatibility or stable gameplay.

## Test machine

| Item | Observed configuration |
| --- | --- |
| OS | Windows 11 Pro x64, 10.0.26300 / build 26300 |
| CPU | Intel Core i5-12400 |
| GPU | Intel UHD Graphics 730 |
| Driver | 32.0.101.7088 |
| Installed RAM | 12 GB |
| Target | Ratchet & Clank PS4, CUSA01047, USA, 1.00 |
| Output settings | 1280x720, windowed, 30 FPS cap, VSync on |
| Readbacks | Linear on, deferred off |
| Other defaults | Upscaling off; zero-clear mirror off; no binary game patches |

## Game observations

| Check | Evidence / limit |
| --- | --- |
| Boot / title | Reached in local tests; title screen visually observed |
| Main menu / difficulty | New Game and difficulty selection tested |
| Loading / opening movie | Both appeared with deferred readbacks off |
| Attempted movie skip | Freeze reported after Enter and several unidentified keys; exact trigger unconfirmed |
| Gameplay movement / HUD | Not validated |
| Audible sound / physical controller | Not validated |
| Save and load | A save file was generated; successful gameplay save/load not validated |
| 1080p / higher FPS | Not validated |
| Long gameplay stability | Not validated; short boot sessions do not establish it |
| Device Lost | Historically reproduced on UHD 730, including zero-clear off; unresolved |
| Memory pressure | A subsequent launch failed allocating the 6080 MiB guest pool (Windows error 1450), before gameplay |

No game compatibility claim is made for other title IDs, versions, GPUs or Linux.
The release's LGPL FFmpeg dependency build is checked with decoder tests and the
packaged smoke test; the game observations above were made before that packaging
change. Full gameplay has not been revalidated against the final V1 package.

## Automated checks

- V1 native suite with the LGPL FFmpeg DLL directory first in the runtime search
  path: **46 passed, 0 failed, 0 skipped**, including MP3/H.264 fixture decoding and
  a zero-clear GPU check using a local captured shader. That shader is not distributed.
- V1 complete Python suite: **450 discovered; 399 passed, 51 skipped, 0 failed**.
- Liverpool command harness: pending, late-arrival, callback-arrival and startup
  command cases passed.
- Packaging's license check rejected the installed GPLv3 FFmpeg build as expected.
- Icon/launcher follow-up: **54 passed, 0 failed**; these overlap the Python suite
  and must not be added to its count as independent coverage.
- Windows product builds succeeded. The isolated ZIP smoke test verifies CPU
  feature querying, bundled Python imports and launcher startup without MSYS2 on PATH.
- All seven icon frames in each of four packaged executables match their original
  assets; the runtime manifest remains present.

Native decoder tests validate fixture decoding, not audible or visual correctness during
gameplay. Skipped tests are not counted as passes. Local private logs,
game-derived files and hardware diagnostics are excluded from the repository.
