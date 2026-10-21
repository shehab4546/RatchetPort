"""Run the built Windows native test targets in an isolated directory; preserve results locally."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build-dir', type=Path, default=ROOT / 'out/ratchet-clean')
    parser.add_argument('--zero-clear-shader', type=Path, help='Local captured cs_0540709a SPIR-V; never distributed')
    parser.add_argument('--msys2', type=Path, default=Path(os.environ.get('MSYS2_ROOT', r'C:\msys64')))
    parser.add_argument('--runtime-dir', type=Path, help='Test with release DLLs before toolchain DLLs')
    args = parser.parse_args()
    if sys.platform != 'win32':
        parser.error('This runner covers Windows targets; use the inherited Linux test workflow on Linux.')
    build = args.build_dir.resolve()
    names = sorted(set(n for n in re.findall(r'add_executable\(([^\s)]+)',
        (ROOT / 'gpu/CMakeLists.txt').read_text()) if n.endswith('-test')))
    work = ROOT / 'out' / ('native-tests-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    work.mkdir(parents=True)
    env = {k: v for k, v in os.environ.items() if not k.startswith(('RATCHET_', 'SPARTAN_', 'GOW3_'))}
    env['PATH'] = str(args.msys2 / 'clang64/bin') + os.pathsep + env.get('PATH', '')
    if args.runtime_dir:
        env['PATH'] = str(args.runtime_dir.resolve()) + os.pathsep + env['PATH']
    extra = {'mp3-test': [str(ROOT / 'tests/data/sine.mp3')],
             'videodec-test': [str(ROOT / 'tests/data/tiny.h264')],
             'isa-stub-test': [str(ROOT / 'tests/data/isa_fixture.bin')]}
    results = []
    for name in names:
        exe = build / (name + '.exe')
        if name == 'zero-clear-gpu-test' and not args.zero_clear_shader:
            results.append({'test': name, 'status': 'SKIP', 'reason': 'Needs a local captured shader'})
            print(name, 'SKIP: no captured shader', flush=True)
            continue
        if not exe.is_file():
            results.append({'test': name, 'status': 'FAIL', 'reason': 'Target not built'})
            print(name, 'FAIL: target not built', flush=True)
            continue
        command = [str(exe), *extra.get(name, [])]
        if name == 'zero-clear-gpu-test': command.append(str(args.zero_clear_shader.resolve()))
        if name == 'churn-trace-test':
            command = [sys.executable, str(ROOT / 'tests/test_texture_churn_trace.py'), str(exe)]
        try:
            run = subprocess.run(command, cwd=work, env=env, stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT, timeout=90, creationflags=subprocess.CREATE_NO_WINDOW)
            output, code = run.stdout, run.returncode
        except subprocess.TimeoutExpired as error:
            output, code = error.stdout or b'', 'TIMEOUT'
        except OSError as error:
            output, code = str(error).encode(), 'START_FAILED'
        (work / (name + '.log')).write_bytes(output)
        status = 'PASS' if code == 0 else 'FAIL'
        results.append({'test': name, 'status': status, 'exit_code': code})
        print(name, status, code, flush=True)
    (work / 'results.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
    print('Evidence:', work)
    print({status: sum(r['status'] == status for r in results) for status in ('PASS', 'FAIL', 'SKIP')})
    return int(any(r['status'] == 'FAIL' for r in results))

if __name__ == '__main__':
    raise SystemExit(main())
