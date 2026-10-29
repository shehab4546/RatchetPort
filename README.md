# RatchetPort — Ratchet & Clank (2016) PC Port for Windows

RatchetPort is an **unofficial, experimental PC port project for Ratchet & Clank
(2016), the PS4 game**, using a native Windows runtime. It targets **CUSA01047 USA
v1.00**, with **experimental USA 1.09 support in development builds**, and requires a self-made dump of your own original disc. **Pre-Alpha:**
I observed steady **30 FPS gameplay on my NVIDIA GeForce RTX 5070 Laptop GPU**
with V1.1 PlayGo. General hardware compatibility and
long-session stability remain unverified.

![RatchetPort icon](launcher/ratchetport.png)

**V2.0 — Stellar Update · Windows x64 · CUSA01047 USA v1.00**

V2.0 brings the **1440p/4K black-world fix**, adaptive memory management,
Primary/Secondary keyboard bindings, stick presets and mapping-aware in-game
prompts. Independent text/voice selectors preserve the selected game language;
five graphics presets coordinate image quality and shadow settings.

The launcher checks the selected voice archive and reports missing or suspect
data. An OK sample check does not guarantee every voice works; silent non-English
gameplay dialogue remains tracked in [issue #31](https://github.com/shehab4546/RatchetPort/issues/31).
The [black-world report #19](https://github.com/shehab4546/RatchetPort/issues/19)
is confirmed corrected in gameplay at 1440p and 4K. Other graphics and driver
reports remain separate.

See [V2.0 features and fixes](docs/releases/V2.0-Stellar-Update.md),
[controls and diagnostics](docs/CONTROLS_AND_DIAGNOSTICS.md),
[USA languages](docs/USA_LANGUAGES.md) and [test records](docs/TESTING.md).

[Download V2.0](https://github.com/shehab4546/RatchetPort/releases/tag/v2.0)
· [Latest release](https://github.com/shehab4546/RatchetPort/releases/latest)
· [All releases](https://github.com/shehab4546/RatchetPort/releases)
· [Project website](https://shehab4546.github.io/RatchetPort/)
· [Report an issue](https://github.com/shehab4546/RatchetPort/issues)
· [Support development](https://ko-fi.com/shehab4546)

## Support RatchetPort

RatchetPort is a free, community-driven project.

If you'd like to support continued development, testing, research, and maintenance, you can support the project on [Ko-fi](https://ko-fi.com/shehab4546).

Support is completely optional. RatchetPort, its releases, fixes, and source code are not sold through Ko-fi, and supporting the project does not provide access to copyrighted game files or exclusive builds.


**PlayGo update:** the [Windows build and package checks passed](https://github.com/shehab4546/RatchetPort/actions/runs/39695590075).
V1.1 requires valid `sce_sys/playgo-chunk.dat`; the launcher
can restore missing system files from a matching sibling Sc0 in your own dump.
Automated checks do not establish game compatibility.

A Windows-first, **Pre-Alpha** native runtime for **Ratchet & Clank (PS4), CUSA01047, USA, version 1.00**. RatchetPort is derived directly from [FelipePrado0/SpartanPort](https://github.com/FelipePrado0/SpartanPort) and uses renderer and shader-recompiler work from [shadPS4](https://github.com/shadps4-emu/shadPS4).

This is experimental software. Intel UHD 730 has previously reproduced `VK_ERROR_DEVICE_LOST`, including with the zero-clear mirror disabled. Successful compilation or a launcher opening does not establish playable or stable gameplay. The development build also recognizes the fingerprinted USA 1.09 update; gameplay validation is pending. Other title IDs, updates, regions and add-ons remain unreviewed. See [update compatibility and feature limits](docs/UPDATE_COMPATIBILITY.md).

## Requirements

- Windows 10 1903+ or Windows 11, 64-bit; an x86-64 CPU with AVX.
- A Vulkan 1.3-capable GPU and driver. Compatibility depends on the device's reported features; there is no validated minimum performance specification yet.
- Enough RAM and page-file capacity for the guest memory pool and renderer. Out-of-memory errors remain possible.
- **You must own the original PS4 game disc and make your own dump from that disc using your own PS4.** The published V2.0 package targets CUSA01047 USA v1.00. Development builds can layer the matching USA 1.09 update over that base. Extract your dump into a directory containing nonempty `eboot.bin`, `sce_sys/param.sfo`, `sce_sys/playgo-chunk.dat`, and `sce_module/libc.prx` and `sce_module/libSceFios2.prx`.

**No game files, PS4 system modules, keys or game artwork are included.** RatchetPort does not download or decrypt a game. Keep the original dump unchanged.

Do not use or share someone else's dump. Ownership of a disc does not make this
project a source of downloadable game files. Use your own hardware and files in
accordance with applicable law; this repository provides no bypass keys or game downloads.

**بالعربية:** يجب أن تمتلك قرص اللعبة الأصلي وأن تعمل dump بنفسك من قرصك باستخدام
جهاز PS4 الخاص بك. المشروع لا يتضمن اللعبة أو ملفات نظام PS4 أو المفاتيح، ولا يوفر
روابط لتنزيلها. اختبرت اللعب الفعلي بمعدل **30 إطارًا/ثانية ثابتًا على جهازي
المزوّد بـ RTX 5070 Laptop** مع تحديث V1.1 PlayGo. يبقى الإصدار تجريبيًا؛ هذه النتيجة
خاصة بالجهاز المختبر ولا تثبت التوافق مع جميع الأجهزة أو استقرار الجلسات الطويلة.

RatchetPort مشروع غير رسمي لنقل راتشت أند كلانك (Ratchet & Clank 2016) من PS4
إلى الكمبيوتر بنظام Windows. هذه نسخة تجريبية تتطلب ملفات قرصك الخاص، وليست
تنزيلًا للعبة كاملة. المشروع مخصص للعبة PS4 لعام 2016، وليس Ratchet & Clank: Rift Apart.

## What was actually tested

| Tested hardware | Version / evidence | Result |
| --- | --- | --- |
| NVIDIA GeForce RTX 5070 Laptop GPU | V1.1 PlayGo; my gameplay observations and two runtime logs on 22 October 2026 | I observed steady **30 FPS gameplay**; logged sessions of **621 s** and **294 s** both ended with exit code **0** |
| Intel Core i5-12400, Intel UHD Graphics 730 (driver 32.0.101.7088), 12 GB RAM, Windows 11 Pro build 26300 | Earlier V1 bring-up tests | Title/menu, difficulty selection, loading and opening movie reached; a freeze and `VK_ERROR_DEVICE_LOST` were reported; sustained 30 FPS gameplay was not validated |

The RTX 5070 Laptop logs show fullscreen, VSync on, a 30 FPS limit, PlayGo
initialized with 72 chunks and an Xbox One Controller detected. They contain no
Prefetch unsupported-import stop or `VK_ERROR_DEVICE_LOST`. The steady 30 FPS
gameplay result is my observation; the logs record the frame limit,
not a sampled FPS trace. CPU model, RAM, driver and output resolution are not
identified in these logs. This evidence does not establish performance on other GPUs, higher
FPS, reliable cutscene skipping, audio/controller behavior, save/load or long
sessions. AMD and Linux gameplay remain unvalidated.

The earlier UHD 730 settings were 30 FPS limit, VSync on, 1280x720 output,
upscaling off, zero-clear mirror off, linear readbacks on and deferred readbacks
off. Those settings are not a measured 30 FPS result for that device.
See [the detailed evidence and test counts](docs/TESTING.md).

## Starting on Windows

1. Extract the downloaded Windows ZIP into a new writable folder.
2. Open `RatchetPort.exe`, choose the game directory and save the settings.
3. Leave the initial settings at **30 FPS, VSync on, 1280x720 output, windowed, upscaling off, Deferred GPU readbacks off** and start the game.
4. `Play RatchetPort.exe` can subsequently start using the saved configuration.

The launcher validates the title ID and version before preparation. Development builds add an optional **Update folder** for USA 1.09 and verify its executable and asset-index fingerprints. Update files are combined with the base through a temporary view; clearing the update field returns to the installed version. See [the version-specific feature table](docs/UPDATE_COMPATIBILITY.md). Original mode applies no timing patch. Experimental 60 FPS applies the verified pacing/clock pair for the exact supported build; saved patch selections cannot activate another game's patches. Output resolution is a host presentation setting, not a claim that the game's internal rendering resolution was patched.

Settings (`settings.json`, `ratchet.ini`), prepared executable files (`out/`), shader caches, logs and saves are generated beside the extracted application by default. A custom data/saves directory can be selected. Preserve these user files when replacing a package. Never distribute the generated prepared executable or shader dumps.

## Controls and graphics

Generic SDL controller support and remappable keyboard/mouse input are retained. The Game page configures PS4 button mappings. Default keyboard mappings include WASD for movement, arrows for the right stick, Space/Left Shift/E/Q for Cross/Circle/Square/Triangle, 1/3 for L1/R1, R/F for L2/R2, Enter for Options, and Tab/Backspace for the touchpad regions. These are mappings to PS4 buttons; they do not inject game-specific actions.

Insert or R3+L2 opens the runtime graphics overlay. Window mode, output size, VSync, graphics diagnostics and advanced renderer options remain available. Higher FPS, upscalers, higher output sizes and advanced options are not validated Ratchet features. The launcher offers Original/30 and experimental 60 FPS; changing the target requires restarting the game. Home / Graphics offers general motion blur, shadow-map caps and internal scene resolution through experimental 4K. The information panel separates startup choices from observed scene/depth candidates, viewport, presented image and window size. `RATCHET_ZERO_CLEAR=0` remains the default; enabling it is a diagnostic experiment, not a Device Lost fix.

## Known issues and reporting

- `VK_ERROR_DEVICE_LOST` has been reproduced on Intel UHD 730 around scheduler submission. Stability is not established.
- Linear image readbacks default to on. Deferred GPU readbacks default to off: enabling them reproduced a black screen after difficulty selection. If using an older configuration, turn that option off explicitly. Stale readbacks are inactive while deferral is off. This scene-entry correction does not fix Device Lost.
- Earlier UHD 730 testing reported a freeze after pressing several buttons during the opening movie. The exact trigger and cause remain unconfirmed; reliable cutscene skipping still requires validation.
- Rendering correctness, long play sessions, audio, controller behavior and save/load require real-game verification; automated unit tests cannot validate these.
- Shader compilation can stall or omit effects. Linux support is inherited and unvalidated for this Pre-Alpha Windows delivery.
- Windows error 1450 means the guest memory pool could not be committed (6080 MiB at the default). The renderer needs additional memory. Close unused applications and ensure sufficient Windows commit capacity before retrying.
- No game-specific cheats, QTE hooks, automatic patches or God of War assets are shipped.

For a failure, retain `user/last_run.log` (or the log in the selected data directory), GPU/driver details and the steps taken. Advanced diagnostics can enable Vulkan validation if the Khronos validation layer is installed. Keep diagnostic archives local; inspect paths and personal data before sharing. Do not clear caches or change PRT mappings to conceal an error.

## Building and testing

See [Windows build and package instructions](packaging/windows/README.md). In an MSYS2 CLANG64 shell with the documented dependencies:

```bash
git submodule update --init --recursive
RATCHET_BUILD_DIR=out/ratchet-clean bash build.sh
```

The build script applies the tracked FSR-Vulkan patches, checks already-applied patches, and configures CMake. Targets are `ratchetgpu`, `ratchet-probe`, `ratchet-gpu-capabilities` and `ratchet-play`. PGO configuration is `RATCHET_PGO` / `RATCHET_PGO_DIR`; Windows defaults to PGO off and LTO off. FSR profiling uses `RATCHET_FSR4_PROFILE` / `RATCHET_FSR4_STATS` in both the patch and its caller.

With Windows Python and the dependencies installed:

```powershell
out/ratchet-tools/Scripts/python.exe -m unittest discover -s tests
out/ratchet-tools/Scripts/python.exe tests/test_liverpool_commands.py
```

Native test targets are listed in `gpu/CMakeLists.txt`. They include tiling dispatch, scissor handling, deferred submission support, churn trace semantics, Ratchet OPT11 and Windows crash unwinding. `test_texture_churn_trace.py` takes the built `churn-trace-test.exe` path. The zero-clear GPU test requires a locally captured compute shader; no captured game shader ships in the source or package.

## Credits and license

See [CREDITS.md](CREDITS.md), [LICENSE](LICENSE), `gpu/VENDOR.txt` and dependency licenses. RatchetPort is distributed under **GPL-2.0** (source files that specify GPL-2.0-or-later retain that grant); third-party components keep their own licenses and attribution. Original history and copyright notices remain credited to their authors. This community project is not affiliated with Sony or Insomniac Games.

Ratchet & Clank, PlayStation and related names and game content belong to their
respective rights holders. The software license grants no rights to the game.
The project icons are original geometric artwork, not extracted game assets.

The Windows release uses shared FFmpeg libraries built with GPL, version3 and
nonfree features disabled, under LGPL-2.1-or-later. The release includes the exact
FFmpeg source archive alongside the binaries and a RatchetPort source archive
containing the pinned submodules and tracked patches. See
[source and dependency notices](docs/DISTRIBUTION.md).
