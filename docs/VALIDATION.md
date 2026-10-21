# Windows Pre-Alpha validation

Target: Ratchet & Clank PS4, CUSA01047 USA v1.00. These results describe local testing on Windows with Intel UHD 730, driver 32.0.101.7088. They are not a stability or compatibility guarantee for other systems.

- Clean source configuration and Windows runtime/test compilation succeeded using MSYS2 CLANG64, with LTO and PGO off.
- Native regression suite: 46 passed, including GPU tiling dispatch, the local-shader zero-clear check, scissor, texture churn, Ratchet OPT11 and Windows crash unwinding. The captured shader is not distributed.
- The separate Liverpool command-race harness passed.
- Python suite: 399 passed, 51 skipped, zero failures after the synchronous-readback default change. Platform-dependent and optional checks remain explicitly skipped.
- Package smoke checks passed with a system-only PATH. The frozen launcher and required preparation imports ran without the development toolchain. Four package tests covered a valid ZIP and rejection of missing SDL3, missing iced-x86 and included user settings.

## Actual game observations

The extracted package launched the unmodified local dump with no binary patches, output at 1280x720, a 30 FPS limit, VSync on, upscaling off and zero-clear mirror off. The Ratchet & Clank title screen and its "PRESS ANY BUTTON" prompt were visually observed. Runtime logs showed Vulkan presentation, game threads, decoded ATRAC9 audio buffers and a mounted save directory. These observations do not establish audible sound or working gameplay saves.

An interactive run recorded about 213 seconds. An earlier unattended source run lasted about 295 seconds, with no visual gameplay assessment. No Device Lost was recorded in these short resume-session runs. Previously reproduced `VK_ERROR_DEVICE_LOST` on this GPU remains an unresolved known issue; these runs were too short and did not establish gameplay stability.

The user confirmed navigating New Game and difficulty selection. With deferred readbacks enabled, the screen remained black. A diagnostic executable logged linear image readbacks ON inside TextureCache and still reproduced the black screen. Linear image readbacks had already been forced on in the preserved Ratchet source; there was no demonstrated regression disabling that flag. The upstream backing-write invalidation repair also remained present.

Using the same diagnostic executable and changing only deferred readbacks to off, the user confirmed the loading screen and opening movie appeared. This matches the older successful test's recorded synchronous-readback mode. Launcher, startup-script and native settings now default to synchronous readbacks; the actual TextureCache linear-readback value is logged and defaults to on through EmulatorSettings. Existing configurations explicitly enabling deferral must be changed by the user. Stale-readback mode is inactive without deferral.

The user subsequently reported a freeze after pressing several keys while trying to skip the movie. The trigger is not isolated. That 220-second run recorded no fatal exception or Device Lost, and created a gameplay save file; successful gameplay save/load is still unverified. Actual playable movement, HUD correctness, physical controller behavior, audible audio, 1080p and a long session remain unverified. Windows memory-commit error 1450 also occurred on an earlier launch before unused applications were closed.

## Focused manual check still required

With the desktop unlocked, start a package containing the readback change at the defaults above, with deferred readbacks off. At the title prompt press Space (PS4 Cross), enter the main menu and start or load a game. First let the opening movie finish without skipping; confirm that the character responds to movement and Cross. Test skipping separately using Enter for Options and the displayed PS4-button prompt (Cross = Space, Circle = Left Shift, Square = E, Triangle = Q). If it freezes, press F10 once and preserve the log before closing. Check audible sound and a physical controller if available. Play for at least 30 minutes, record any graphical problems or Device Lost, then verify that progress loads after closing and reopening. Keep logs locally. Test 1080p separately only after the baseline session succeeds.

The source remains Pre-Alpha regardless of successful unit tests or package smoke checks. Publication must identify this validation boundary and the unresolved Device Lost issue.
