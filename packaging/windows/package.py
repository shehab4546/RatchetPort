#!/usr/bin/env python3
"""Assemble a fresh, portable Windows package without touching previous packages or user data."""
import argparse
import ctypes
from datetime import datetime
import importlib.metadata
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from release_info import VERSION, APP_TITLE, RELEASE_LABEL, WINDOWS_ARCHIVE, FILE_VERSION
FORBIDDEN = {'eboot.bin', 'sce_module', 'sce_sys', 'user', 'savedata', 'settings.json',
             'game_icon.ico', 'ratchet.ini', 'last_run.log', 'mods.json', 'patches.json'}

def audit(folder):
    for p in folder.rglob('*'):
        if p.relative_to(folder).as_posix() == '_internal/base_library.zip':
            continue  # Required frozen Python standard library, not a diagnostic archive.
        if p.name.lower() in FORBIDDEN or p.suffix.lower() in {'.pkg', '.prx', '.sprx', '.log', '.zip', '.spv'}:
            raise ValueError(f'Forbidden package content: {p.relative_to(folder)}')
        if p.is_file() and p.suffix.lower() in {'.exe', '.dll', '.pyd', '.py', '.txt', '.md'}:
            content = p.read_bytes().lower()
            roots = (str(ROOT).encode().lower(), ROOT.as_posix().encode().lower(),
                     ('/' + ROOT.drive[0].lower() + ROOT.as_posix()[2:]).encode().lower())
            if any(root in content or root.decode().encode('utf-16-le') in content for root in roots):
                raise ValueError(f'Local build path embedded in package: {p.relative_to(folder)}')


def dependencies(executable, destination, clang, ffmpeg):
    pending, done = [executable], set()
    files = {p.name.lower(): p for p in clang.glob('*.dll')}
    release_ffmpeg = {p.name.lower(): p for p in ffmpeg.glob('*.dll')}
    files.update(release_ffmpeg)
    system = Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'System32'
    while pending:
        current = pending.pop()
        output = subprocess.check_output([str(clang / 'llvm-objdump.exe'), '-p', str(current)], text=True)
        for name in re.findall(r'DLL Name:\s*(\S+)', output):
            key = name.lower()
            if key in done: continue
            done.add(key)
            if re.fullmatch(r'(?:avcodec|avformat|avutil|avfilter|avdevice|swscale|swresample)-\d+\.dll', key):
                if key not in release_ffmpeg:
                    raise FileNotFoundError(f'Release FFmpeg ABI does not match the executable: {name}')
            if key in files:
                source = files[key]
                shutil.copy2(source, destination / source.name)
                pending.append(source)
            elif not key.startswith(('api-ms-', 'ext-ms-')) and not (system / name).is_file():
                raise FileNotFoundError(f'Missing runtime dependency: {name}')

def copy_launcher_assets(stage):
    (stage / 'launcher').mkdir()
    for name in ('Cinzel-Black.ttf', 'OFL-Cinzel.txt', 'ratchetport.ico', 'ratchetport.png',
                 'ratchet-probe.png'):
        shutil.copy2(ROOT / 'launcher' / name, stage / 'launcher' / name)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build-dir', type=Path, default=ROOT / 'out/ratchet-clean')
    parser.add_argument('--msys2', type=Path, default=Path(os.environ.get('MSYS2_ROOT', r'C:\msys64')))
    parser.add_argument('--ffmpeg-prefix', type=Path, default=ROOT / 'out/ffmpeg-lgpl')
    args = parser.parse_args()
    build = args.build_dir.resolve()
    ffmpeg = args.ffmpeg_prefix.resolve()
    # Reject the MSYS2 GPLv3 build: the public package uses our isolated LGPL build.
    codec_files = list((ffmpeg / 'bin').glob('avcodec-*.dll'))
    if len(codec_files) != 1:
        raise FileNotFoundError('Build the release dependency first: bash packaging/windows/build-ffmpeg.sh')
    with os.add_dll_directory(str(ffmpeg / 'bin')), os.add_dll_directory(str(args.msys2 / 'clang64/bin')):
        codec = ctypes.CDLL(str(codec_files[0]))
        codec.avcodec_license.restype = ctypes.c_char_p
        codec.avcodec_configuration.restype = ctypes.c_char_p
        license_name = codec.avcodec_license().decode()
        configuration = codec.avcodec_configuration().decode()
        if license_name != 'LGPL version 2.1 or later' or any(
                flag in configuration for flag in ('--enable-gpl', '--enable-version3', '--enable-nonfree')):
            raise ValueError(f'Unsupported FFmpeg distribution license: {license_name}')
    for name in ('ratchet-probe.exe', 'ratchet-gpu-capabilities.exe', 'ratchet-play.exe'):
        if not (build / name).is_file(): raise FileNotFoundError(f'Build first: {build / name}')
    work = ROOT / 'out' / ('package-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
    work.mkdir(parents=True, exist_ok=False)
    hidden = ['frame_timing', 'argparse', 'base64', 'collections', 'hashlib', 'json', 're', 'shutil', 'socket', 'struct',
              'tempfile', 'threading', 'uuid', 'xml.etree.ElementTree', 'urllib.request', 'ctypes.wintypes',
              'iced_x86', 'PIL.Image', 'PIL.ImageTk', 'release_info', 'ratchet_game', 'ratchet_patches', 'ratchet_binary_audit', 'prepare', 'patches', 'mods',
              'content_profile', 'link_libc', 'link_modules', 'isa_rewrite', 'guest_memory', 'discord_presence']
    version_file = work / 'version-info.txt'
    version_file.write_text(f"""VSVersionInfo(
      ffi=FixedFileInfo(filevers={FILE_VERSION!r}, prodvers={FILE_VERSION!r},
                       mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
      kids=[StringFileInfo([StringTable('040904B0', [
        StringStruct('FileDescription', {APP_TITLE!r}),
        StringStruct('FileVersion', {VERSION!r}),
        StringStruct('ProductName', 'RatchetPort'),
        StringStruct('ProductVersion', {VERSION!r}),
        StringStruct('OriginalFilename', 'RatchetPort.exe')])]),
        VarFileInfo([VarStruct('Translation', [1033, 1200])])])
""", encoding='utf-8')
    command = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--windowed', '--log-level', 'WARN',
               '--name', 'RatchetPort', '--version-file', str(version_file), '--distpath', str(work / 'frozen'), '--workpath', str(work / 'build'),
               '--specpath', str(work), '--paths', str(ROOT / 'scripts'),
               '--icon', str(ROOT / 'launcher/ratchetport.ico')]
    for module in hidden: command += ['--hidden-import', module]
    subprocess.run([*command, str(ROOT / 'launcher/ratchetport_launcher_win.py')], check=True, cwd=ROOT)
    stage = work / 'RatchetPort'
    shutil.copytree(work / 'frozen/RatchetPort', stage)
    (stage / 'bin').mkdir()
    clang = args.msys2 / 'clang64/bin'
    for name in ('ratchet-probe.exe', 'ratchet-gpu-capabilities.exe'):
        target = stage / 'bin' / name
        subprocess.run([str(clang / 'llvm-strip.exe'), '--strip-debug', '-o', str(target), str(build / name)], check=True)
        dependencies(target, target.parent, clang, ffmpeg / 'bin')
    subprocess.run([str(clang / 'llvm-strip.exe'), '-o', str(stage / 'Play RatchetPort.exe'),
                    str(build / 'ratchet-play.exe')], check=True)
    (stage / 'scripts').mkdir()
    for p in (ROOT / 'scripts').glob('*.py'): shutil.copy2(p, stage / 'scripts' / p.name)
    copy_launcher_assets(stage)
    for name in ('run.py', 'LICENSE', 'README.md', 'CREDITS.md'):
        shutil.copy2(ROOT / name, stage / name)
    (stage / 'docs/releases').mkdir(parents=True)
    (stage / 'docs/evidence').mkdir()
    for name in ('TESTING.md', 'DISTRIBUTION.md', 'releases/V1.md', 'releases/V1.1-PlayGo.md',
                 'releases/V1.3-Verified-Preview.md', 'PATCHES.md', 'RP04_FRAME_TIMING.md',
                 'RP04_RESEARCH_REVIEW.md', 'evidence/ratchet-research-signature-checks.json',
                 'evidence/ratchet-cusa01047-0100-clock.json', 'releases/V1.4-Frame-Timing-Preview.md'):
        shutil.copy2(ROOT / 'docs' / name, stage / 'docs' / name)
    (stage / 'README-Windows.txt').write_text(
        (ROOT / 'packaging/windows/README-Windows.txt').read_text(encoding='utf-8').replace(
            '@RELEASE_TITLE@', APP_TITLE), encoding='utf-8')
    notices = stage / 'licenses'
    notices.mkdir()
    # Include upstream/submodule license files and the licenses of bundled toolchain DLLs.
    for base in (ROOT / 'gpu/third_party', ROOT / 'third_party'):
        for project in base.iterdir():
            if not project.is_dir(): continue
            for p in project.iterdir():
                if p.is_file() and (p.name.upper().startswith(('LICENSE', 'COPYING', 'NOTICE')) or p.suffix.lower()=='.license'):
                    shutil.copy2(p, notices / (project.name + '-' + p.name))
    packaged_licenses = args.msys2 / 'clang64/share/licenses'
    if packaged_licenses.is_dir(): shutil.copytree(packaged_licenses, notices / 'msys2')
    shutil.copytree(ffmpeg / 'share/licenses/ffmpeg', notices / 'ffmpeg')
    shutil.copy2(Path(sys.base_prefix) / 'LICENSE.txt', notices / 'Python-LICENSE.txt')
    for package in ('Pillow', 'iced-x86', 'PyInstaller'):
        distribution = importlib.metadata.distribution(package)
        for path in distribution.files or []:
            if any(word in path.name.lower() for word in ('license', 'copying', 'notice')):
                source = Path(distribution.locate_file(path))
                if source.is_file(): shutil.copy2(source, notices / f'{package}-{path.name}')
    for path in (Path(sys.base_prefix) / 'tcl').glob('*/license.terms'):
        shutil.copy2(path, notices / f'{path.parent.name}-license.terms')
    source_commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    (stage / 'build-info.json').write_text(json.dumps({
        'release': RELEASE_LABEL, 'version': VERSION, 'app_title': APP_TITLE, 'source_commit': source_commit,
        'ffmpeg_license': license_name,
        'ffmpeg_source': 'ffmpeg-9.0.2.tar.xz',
        'ffmpeg_source_sha256': '8c3850283eb25fa026482078a04051e0be17347b09ef81a0849bec15a96e002e',
        'python': sys.version.split()[0],
        'packages': {name: importlib.metadata.version(name) for name in ('Pillow', 'iced-x86', 'PyInstaller')}
    }, indent=2) + '\n', encoding='utf-8')
    audit(stage)
    output = ROOT / 'dist' / WINDOWS_ARCHIVE
    output.parent.mkdir(exist_ok=True)
    if output.exists(): output.rename(output.with_name(output.stem + '-' + datetime.now().strftime('%Y%m%d-%H%M%S') + '.zip'))
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        for p in sorted(stage.rglob('*')):
            if p.is_file(): archive.write(p, Path('RatchetPort') / p.relative_to(stage))
    print(f'Package: {output}\nStaging: {stage}\nAudit: PASS')

if __name__ == '__main__': main()
