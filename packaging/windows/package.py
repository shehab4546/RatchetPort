#!/usr/bin/env python3
"""Assemble a fresh, portable Windows package without touching previous packages or user data."""
import argparse
from datetime import datetime
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
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
            roots = (str(ROOT).encode().lower(), ROOT.as_posix().encode().lower())
            if any(root in content or root.decode().encode('utf-16-le') in content for root in roots):
                raise ValueError(f'Local build path embedded in package: {p.relative_to(folder)}')


def dependencies(executable, destination, clang):
    pending, done = [executable], set()
    files = {p.name.lower(): p for p in clang.glob('*.dll')}
    system = Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'System32'
    while pending:
        current = pending.pop()
        output = subprocess.check_output([str(clang / 'llvm-objdump.exe'), '-p', str(current)], text=True)
        for name in re.findall(r'DLL Name:\s*(\S+)', output):
            key = name.lower()
            if key in done: continue
            done.add(key)
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
    args = parser.parse_args()
    build = args.build_dir.resolve()
    for name in ('ratchet-probe.exe', 'ratchet-gpu-capabilities.exe', 'ratchet-play.exe'):
        if not (build / name).is_file(): raise FileNotFoundError(f'Build first: {build / name}')
    work = ROOT / 'out' / ('package-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
    work.mkdir(parents=True, exist_ok=False)
    hidden = ['argparse', 'base64', 'collections', 'hashlib', 'json', 're', 'shutil', 'socket', 'struct',
              'tempfile', 'threading', 'uuid', 'xml.etree.ElementTree', 'urllib.request', 'ctypes.wintypes',
              'iced_x86', 'PIL.Image', 'PIL.ImageTk', 'ratchet_game', 'prepare', 'patches', 'mods',
              'content_profile', 'link_libc', 'link_modules', 'isa_rewrite', 'guest_memory', 'discord_presence']
    command = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--windowed', '--log-level', 'WARN',
               '--name', 'RatchetPort', '--distpath', str(work / 'frozen'), '--workpath', str(work / 'build'),
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
        dependencies(target, target.parent, clang)
    subprocess.run([str(clang / 'llvm-strip.exe'), '-o', str(stage / 'Play RatchetPort.exe'),
                    str(build / 'ratchet-play.exe')], check=True)
    (stage / 'scripts').mkdir()
    for p in (ROOT / 'scripts').glob('*.py'): shutil.copy2(p, stage / 'scripts' / p.name)
    copy_launcher_assets(stage)
    for name in ('run.py', 'LICENSE', 'README.md', 'CREDITS.md'):
        shutil.copy2(ROOT / name, stage / name)
    shutil.copy2(ROOT / 'packaging/windows/README-Windows.txt', stage / 'README-Windows.txt')
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
    audit(stage)
    output = ROOT / 'dist/RatchetPort-Windows-PreAlpha.zip'
    output.parent.mkdir(exist_ok=True)
    if output.exists(): output.rename(output.with_name(output.stem + '-' + datetime.now().strftime('%Y%m%d-%H%M%S') + '.zip'))
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        for p in sorted(stage.rglob('*')):
            if p.is_file(): archive.write(p, Path('RatchetPort') / p.relative_to(stage))
    print(f'Package: {output}\nStaging: {stage}\nAudit: PASS')

if __name__ == '__main__': main()
