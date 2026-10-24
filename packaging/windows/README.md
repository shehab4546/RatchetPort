# Build RatchetPort on Windows

Use MSYS2 CLANG64 and a separate Windows Python 3.12+ with Tcl/Tk support.
The runtime target is Windows x64. Linux build scripts are inherited and are not validated for this release.

In CLANG64 install dependencies:

```bash
pacman -S --needed git patch \
  mingw-w64-clang-x86_64-{toolchain,cmake,ninja,pkgconf,python} \
  mingw-w64-clang-x86_64-{vulkan-headers,vulkan-loader,vulkan-memory-allocator,glslang} \
  mingw-w64-clang-x86_64-{sdl3,fmt,boost,robin-map,xxhash,ffmpeg,zydis} \
  mingw-w64-clang-x86_64-{spirv-tools,spirv-headers,spirv-cross}
git submodule update --init --recursive
RATCHET_BUILD_DIR=out/ratchet-clean bash build.sh
```

Before making a public Windows package, build its isolated LGPL FFmpeg dependency:

```bash
pacman -S --needed make nasm diffutils
bash packaging/windows/build-ffmpeg.sh
```

This does not replace the installed MSYS2 libraries. The packager selects these
shared DLLs ahead of the MSYS2 versions and verifies their license/configuration.
They use the same FFmpeg 9.0.2 ABI as the CLANG64 build; test the final package with
these libraries. The generated diagnostic configuration string redacts the local
checkout path. The complete actual build command is retained in the script.

Use a previously nonexistent `RATCHET_BUILD_DIR` for a clean configure/build. Existing diagnostics and build directories are not deleted. The script applies `gpu/patches/fsr-vulkan/*.patch` only when not already applied; a conflicting submodule change stops the build. The resulting FSR submodule worktree is intentionally dirty, with its complete changes represented by those patches. No submodule commit is invented or pushed.

For explicit CMake configuration after applying these patches:

```bash
cmake -S gpu -B out/ratchet-clean -G Ninja -DCMAKE_BUILD_TYPE=RelWithDebInfo \
  -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ -DRATCHET_LTO=OFF -DRATCHET_PGO=off
cmake --build out/ratchet-clean --target ratchet-probe ratchet-gpu-capabilities ratchet-play --parallel 4
```

In PowerShell, create the packaging/testing environment with Windows Python:

```powershell
py -3.12 -m venv out/ratchet-tools
out/ratchet-tools/Scripts/python.exe -m pip install -r packaging/windows/requirements.txt
out/ratchet-tools/Scripts/python.exe -m unittest discover -s tests
out/ratchet-tools/Scripts/python.exe tests/test_liverpool_commands.py
out/ratchet-tools/Scripts/python.exe tests/run_native.py --build-dir out/ratchet-clean --runtime-dir out/ffmpeg-lgpl/bin
out/ratchet-tools/Scripts/python.exe packaging/windows/package.py --build-dir out/ratchet-clean
powershell -NoProfile -File packaging/windows/smoke-test.ps1 dist/RatchetPort-V1.4-Frame-Timing-Preview-Windows.zip
```

Build the `*-test` targets listed in `gpu/CMakeLists.txt` before running the native suite. Pass `--zero-clear-shader` with your local captured shader to run that GPU check; otherwise the runner explicitly reports it skipped.

The ZIP is assembled in a new timestamped staging directory. Packaging preserves older ZIPs with a timestamp. It bundles the frozen launcher, runtime executables, recursively discovered CLANG64 DLL dependencies, preparation scripts, fonts and licenses. It rejects known game files, modules, caches, settings and logs. The smoke check extracts the ZIP to a new temporary directory and runs with a system-only PATH so an installed MSYS2 cannot mask missing packaged DLLs. Its logs are retained locally.

The package contains no game dump. Only the local owner can validate actual gameplay, audio, controller input and saves using their own CUSA01047 USA v1.00 files. The build workflow does not publish releases. Dedicated publishing workflows promote an owner-authorized, tested build and record any pending gameplay validation.

Python, source and native tests remain separate from packaged game data. Never stage `out/`, `dist/`, captures, prepared game binaries or private logs in Git.

After committing the release changes, run `python packaging/windows/source_archive.py`
to create the explicit source ZIP, which includes the pinned submodules. Attach it
and `out/release-sources/ffmpeg-9.0.2.tar.xz` alongside the Windows ZIP and checksums.
See [distribution notes](../../docs/DISTRIBUTION.md). Frame Timing Preview remains experimental even
when these automated checks pass. Version labels and archive names come from
`scripts/release_info.py`; package smoke checks compare the executable resource,
frozen metadata and visible launcher title with `build-info.json`.
