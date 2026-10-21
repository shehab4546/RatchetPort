RatchetPort v0.1.0 Pre-Alpha — Windows

Target: Ratchet & Clank PS4, CUSA01047 USA version 1.00 only.
No game files included. Requires your own legally obtained, extracted PS4 dump.

Extract the entire ZIP into a writable folder and open RatchetPort.exe.
Choose the folder containing eboot.bin, sce_sys/param.sfo and sce_module.
The required libc.prx and libSceFios2.prx must come from your own dump.
Separate updates and other title IDs are rejected.

Default: 30 FPS, VSync on, 1280x720 output, windowed, upscaling off.
Zero-clear mirror is off. No binary game patches are applied.
The output size does not change the game's internal render targets.

Requires Windows 10 1903+ / 11 x64, an AVX-capable CPU and Vulkan 1.3 GPU/driver.
Python and runtime libraries are bundled. No MSYS2 installation is needed to play.

KNOWN ISSUE: VK_ERROR_DEVICE_LOST has occurred on Intel UHD 730, including with
zero-clear disabled. This is not a stable release or a guarantee of playable gameplay.

Settings and generated data are kept beside the application unless a custom path is
selected. Preserve settings.json, ratchet.ini and user/ when replacing the application.
Keep the original game dump unchanged. Never redistribute prepared game images.

Generic controller and keyboard/mouse mappings are in the Game page.
Insert or R3+L2 opens the graphics overlay. See README.md for mappings and diagnostics.
Play RatchetPort.exe starts directly using saved settings.

Based on FelipePrado0/SpartanPort and shadPS4. See CREDITS.md, LICENSE and licenses/.
GPL-2.0 with original per-file and dependency license terms preserved.
