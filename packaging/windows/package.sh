#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")/../.."
source ./msys2-env.sh
python=${WINPYTHON:-out/ratchet-tools/Scripts/python.exe}
[[ -x $python ]] || { echo 'Create out/ratchet-tools with Windows Python and install PyInstaller, Pillow, iced-x86.' >&2; exit 1; }
"$python" packaging/windows/package.py --build-dir "${RATCHET_BUILD_DIR:-out/ratchet-clean}"
