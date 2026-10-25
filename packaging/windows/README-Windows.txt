@RELEASE_TITLE@ — Windows

Target: Ratchet & Clank PS4, CUSA01047 USA version 1.00 only.
You must own the original PS4 game disc and make your own dump from that disc
using your own PS4. Do not use or redistribute someone else's dump.
No game files, PS4 modules, keys or game artwork are included.

Extract the entire ZIP into a writable folder and open RatchetPort.exe.
Choose the folder containing eboot.bin, sce_sys/param.sfo and sce_module.
The required libc.prx and libSceFios2.prx must come from your own dump.
Separate updates and other title IDs are rejected.

Default: 30 FPS, VSync on, 1280x720 output, windowed, upscaling off.
Linear readbacks on; deferred GPU readbacks off.
Zero-clear mirror is off. Original mode applies no timing patches.
The output size does not change the game's internal render targets.

Requires Windows 10 1903+ / 11 x64, an AVX-capable CPU and Vulkan 1.3 GPU/driver.
Python and runtime libraries are bundled. No MSYS2 installation is needed to play.

KNOWN ISSUE: VK_ERROR_DEVICE_LOST has occurred on Intel UHD 730, including with
zero-clear disabled. This is not a stable release or a guarantee of playable gameplay.

Earlier testing: I observed steady 30 FPS gameplay on my NVIDIA RTX 5070 Laptop
GPU with V1.1 PlayGo. Intel UHD 730 reached the
menu/loading/opening movie and also exhibited device-loss failures. Neither
result establishes gameplay acceptance of this exact build. See docs/TESTING.md.

Choose Game frame rate: 30 FPS / Original (default) or 60 FPS (experimental), then
close and restart the game. 60 requires the exact reviewed game build and applies
pacing/clock patches together. Gameplay acceptance is pending.
Home / Graphics also offer Motion blur: On / Original or Off, and Shadow-map
resolution: Original, 1024, 512 or 256 px maximum. Save and restart to apply.
Lower caps reduce shadow detail; the fixed atlas allocation stays unchanged.
The in-game Graphics information rows show the launch mode. Restore Original
and restart to remove a feature.
Internal render resolution now offers Original, 720p, 900p, 1080p, 1440p and
4K (3840x2160). These experimental scene settings are independent of output
resolution and take effect after restarting. Higher resolutions need more GPU
power and memory. The overlay separately reports startup mode, observed scene
candidates and viewport, presented image and window size. An unobserved scene
remains unconfirmed. In-game image quality and 4K stability are not validated.
See docs/RP06_RENDER_RESOLUTION.md and docs/releases/V1.6-Resolution-Preview.md.
See docs/RP05_VISUAL_CONTROLS.md and docs/releases/V1.5-Visual-Controls-Preview.md.

Settings and generated data are kept beside the application unless a custom path is
selected. Preserve settings.json, ratchet.ini and user/ when replacing the application.
Keep the original game dump unchanged. Never redistribute prepared game images.

Generic controller and keyboard/mouse mappings are in the Game page.
Insert or R3+L2 opens the graphics overlay. See README.md for mappings and diagnostics.
Play RatchetPort.exe starts directly using saved settings.

Based on FelipePrado0/SpartanPort and shadPS4. See CREDITS.md, LICENSE and licenses/.
GPL-2.0 with original per-file and dependency license terms preserved.
Not affiliated with Sony or Insomniac Games. Game names/content belong to their
rights holders. See docs/TESTING.md and docs/DISTRIBUTION.md for details and sources.
