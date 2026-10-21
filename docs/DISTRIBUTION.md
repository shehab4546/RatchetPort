# V1 source, licensing and third-party notices

RatchetPort retains the project's GPL-2.0 license, upstream copyright notices and
Git history. Files explicitly licensed GPL-2.0-or-later retain that permission.
Third-party components retain their own licenses; see CREDITS.md, LICENSE,
gpu/VENDOR.txt, the individual source files and the binary package's licenses/.
Changing a project name does not transfer authorship or ownership.

## Corresponding source

The V1 release provides `RatchetPort-V1-Source.zip`, built from its exact Git commit
and all six pinned submodule commits. `SOURCE_REVISION.txt` identifies the main
commit and `SUBMODULE_REVISIONS.txt` lists the submodule commits. The archive
includes the tracked FSR-Vulkan patches; the build script applies them to the
included unpatched submodule source. It contains no private build directories,
game-derived captures or game files. The Git tag and source archive identify the
same code; build-info.json in the Windows package records that commit.

GitHub's automatic source ZIP alone does not include submodule contents. Use the
explicit source attachment or clone recursively at the V1 tag.

Download the binaries and source attachments together from the
[V1 release](https://github.com/shehab4546/RatchetPort/releases/tag/v1).

## FFmpeg

This software uses libraries from [FFmpeg](https://ffmpeg.org/) under
**LGPL-2.1-or-later**. The public package uses FFmpeg 9.0.2 built from the unmodified
`ffmpeg-9.0.2.tar.xz` source attached to the same release. Its SHA256 is
`8c3850283eb25fa026482078a04051e0be17347b09ef81a0849bec15a96e002e`.

The complete configure/build recipe is `packaging/windows/build-ffmpeg.sh`.
It produces shared libraries, disables GPL, version3 and nonfree features, disables
automatic optional-library discovery and enables zlib. Built-in codecs and
demuxers remain enabled. GPLv3-enabled MSYS2 FFmpeg DLLs are not shipped in V1.
The packaging tool checks the actual codec library's license and configure flags.
The DLL names remain intact, and recipients may replace the shared libraries with
compatible builds. No restrictions on studying or modifying these libraries are added.
See [FFmpeg's licensing page](https://ffmpeg.org/legal.html) and the bundled LGPL text.

## Other components

The package preserves dependency license texts, including MSYS2 runtime notices,
Python's license, Pillow's license and bundled third-party notices, iced-x86's MIT
license, PyInstaller's license and bootloader exception, Tcl/Tk notices and the
Cinzel font's SIL Open Font License. Build tooling is not part of the game and
does not change ownership of any dependency. Original project icons are generated
from repository-owned geometry and distributed under the project license.

The game, proprietary PS4 modules, keys, captured game shaders and prepared game
executables are not distributed. Ratchet & Clank, PlayStation and related game
content/names belong to their rights holders. You must make your own dump from
your own original disc using your own PS4; the software license grants no rights
to game content. The project is unaffiliated with Sony or Insomniac Games.
