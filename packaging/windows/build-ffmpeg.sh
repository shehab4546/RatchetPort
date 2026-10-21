#!/usr/bin/env bash
# Build the LGPL-only shared FFmpeg libraries used by the public Windows package.
set -euo pipefail
cd -- "$(dirname -- "$0")/../.."
source ./msys2-env.sh
for tool in clang make nasm cmp python curl tar; do
    command -v "$tool" >/dev/null || { echo "Missing build tool: $tool (install make nasm diffutils)." >&2; exit 1; }
done
version=9.0.2
sha256=8c3850283eb25fa026482078a04051e0be17347b09ef81a0849bec15a96e002e
root=$PWD
archive="$root/out/release-sources/ffmpeg-$version.tar.xz"
source_dir="$root/out/ffmpeg-source-$version"
build_dir="$root/out/ffmpeg-lgpl-build"
prefix="$root/out/ffmpeg-lgpl"
mkdir -p "$(dirname "$archive")" "$build_dir"
if [[ ! -f "$archive" ]]; then
    curl -fL --retry 3 "https://ffmpeg.org/releases/ffmpeg-$version.tar.xz" -o "$archive"
fi
printf '%s  %s\n' "$sha256" "$archive" | sha256sum -c -
if [[ ! -d "$source_dir" ]]; then
    mkdir "$source_dir"
    tar -xJf "$archive" --strip-components=1 -C "$source_dir"
fi
cd "$build_dir"
# Keep built-in codecs/demuxers. Disable optional external libraries and the GPL,
# version3 and nonfree feature sets; zlib is needed for PNG decoding.
"$source_dir/configure" --prefix="$prefix" --target-os=mingw32 --arch=x86_64 \
    --cc=clang --cxx=clang++ --enable-shared --disable-static --disable-programs \
    --disable-doc --disable-debug --disable-autodetect --enable-zlib \
    --disable-gpl --disable-version3 --disable-nonfree \
    --extra-cflags="-ffile-prefix-map=$root=. -fdebug-prefix-map=$root=." \
    --extra-ldflags=-Wl,--no-insert-timestamp
# The public runtime configuration string must not expose the local checkout.
# Keep the actual commands in this recipe; only redact the diagnostic string.
MSYS2_ARG_CONV_EXCL='*' python - "$root" <<'PY'
from pathlib import Path
import sys
path = Path('config.h')
lines = path.read_text().splitlines(keepends=True)
path.write_text(''.join(line.replace(sys.argv[1], '<build-root>')
                        if line.startswith('#define FFMPEG_CONFIGURATION ') else line
                        for line in lines))
PY
make -j "${RATCHET_BUILD_JOBS:-3}"
make install
mkdir -p "$prefix/share/licenses/ffmpeg"
cp "$source_dir/COPYING.LGPLv2.1" "$source_dir/LICENSE.md" "$prefix/share/licenses/ffmpeg/"
cp "$build_dir/ffbuild/config.log" "$prefix/build-config.log"
printf 'FFmpeg %s, LGPL-2.1-or-later; source SHA256 %s\n' "$version" "$sha256"
