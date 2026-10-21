# V1 test record

This record describes local pre-release checks on 21 October 2026. It does not
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
| Main menu / difficulty | Tester selected New Game and difficulty |
| Loading / opening movie | Tester confirmed both appeared with deferred readbacks off |
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

Native decoder tests validate fixture decoding, not the user's perception of
game audio/video. Skipped tests are not counted as passes. Local private logs,
game-derived files and hardware diagnostics are excluded from the repository.
