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
Zero-clear mirror is off. No binary game patches are applied.
The output size does not change the game's internal render targets.

Requires Windows 10 1903+ / 11 x64, an AVX-capable CPU and Vulkan 1.3 GPU/driver.
Python and runtime libraries are bundled. No MSYS2 installation is needed to play.

KNOWN ISSUE: VK_ERROR_DEVICE_LOST has occurred on Intel UHD 730, including with
zero-clear disabled. This is not a stable release or a guarantee of playable gameplay.

Earlier hardware evidence: the owner confirmed actual gameplay at steady 30 FPS
on an NVIDIA RTX 5070 Laptop GPU with V1.1 PlayGo. Intel UHD 730 reached the
menu/loading/opening movie and also exhibited device-loss failures. Neither
result establishes gameplay acceptance of this exact build. See docs/TESTING.md.

This preview contains verified patch loading and acknowledgement, but no enabled
FPS, motion-blur or internal-resolution feature patches. Version 1.3.1 corrects
stale launcher and package branding. See docs/releases/V1.3.1-Verified-Preview.md.

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
