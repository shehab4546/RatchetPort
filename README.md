# RatchetPort

A Windows-first, **Pre-Alpha** native runtime for **Ratchet & Clank (PS4), CUSA01047, USA, version 1.00**. RatchetPort is derived directly from [FelipePrado0/SpartanPort](https://github.com/FelipePrado0/SpartanPort) and uses renderer and shader-recompiler work from [shadPS4](https://github.com/shadps4-emu/shadPS4).

This is experimental software. Intel UHD 730 has previously reproduced `VK_ERROR_DEVICE_LOST`, including with the zero-clear mirror disabled. Successful compilation or a launcher opening does not establish playable or stable gameplay. Other title IDs, updates and regions are not supported by this configuration.

## Requirements

- Windows 10 1903+ or Windows 11, 64-bit; an x86-64 CPU with AVX.
- A Vulkan 1.3-capable GPU and driver. Compatibility depends on the device's reported features; there is no validated minimum performance specification yet.
- Enough RAM and page-file capacity for the guest memory pool and renderer. Out-of-memory errors remain possible.
- Your **own legally obtained PS4 game dump** of CUSA01047 USA v1.00, already extracted into a directory containing nonempty `eboot.bin`, `sce_sys/param.sfo`, and `sce_module/libc.prx` and `sce_module/libSceFios2.prx`.

**No game files, PS4 system modules, keys or game artwork are included.** RatchetPort does not download or decrypt a game. Keep the original dump unchanged.

## Starting on Windows

1. Extract `RatchetPort-Windows-PreAlpha.zip` into a writable folder.
2. Open `RatchetPort.exe`, choose the game directory and save the settings.
3. Leave the initial settings at **30 FPS, VSync on, 1280x720 output, windowed, upscaling off, Deferred GPU readbacks off** and start the game.
4. `Play RatchetPort.exe` can subsequently start using the saved configuration.

The launcher validates the title ID and version before preparation. Separate update directories are rejected. There are no verified Ratchet binary patches in this release; saved patch selections cannot turn on another game's patches. Output resolution is a host presentation setting, not a claim that the game's internal rendering resolution was patched.

Settings (`settings.json`, `ratchet.ini`), prepared executable files (`out/`), shader caches, logs and saves are generated beside the extracted application by default. A custom data/saves directory can be selected. Preserve these user files when replacing a package. Never distribute the generated prepared executable or shader dumps.

## Controls and graphics

Generic SDL controller support and remappable keyboard/mouse input are retained. The Game page configures PS4 button mappings. Default keyboard mappings include WASD for movement, arrows for the right stick, Space/Left Shift/E/Q for Cross/Circle/Square/Triangle, 1/3 for L1/R1, R/F for L2/R2, Enter for Options, and Tab/Backspace for the touchpad regions. These are mappings to PS4 buttons; they do not inject game-specific actions.

Insert or R3+L2 opens the runtime graphics overlay. Window mode, output size, VSync, graphics diagnostics and advanced renderer options remain available. Higher FPS, upscalers, higher output sizes and advanced options are not validated Ratchet features. The launcher offers only the conservative 30 FPS limit. `RATCHET_ZERO_CLEAR=0` remains the default; enabling it is a diagnostic experiment, not a Device Lost fix.

## Known issues and reporting

- `VK_ERROR_DEVICE_LOST` has been reproduced on Intel UHD 730 around scheduler submission. Stability is not established.
- Linear image readbacks default to on. Deferred GPU readbacks default to off: enabling them reproduced a black screen after difficulty selection. If using an older configuration, turn that option off explicitly. Stale readbacks are inactive while deferral is off. This scene-entry correction does not fix Device Lost.
- A user reported a freeze after pressing several buttons during the opening movie. The exact trigger and cause remain unconfirmed; gameplay and cutscene skipping still require validation.
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
