"""Archive the release commit and pinned submodules, never the local working tree."""
import io
from pathlib import Path
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from release_info import ARCHIVE_STEM, SOURCE_ARCHIVE


def git(*args, cwd=ROOT):
    return subprocess.check_output(['git', *args], cwd=cwd)


def main():
    commit = git('rev-parse', 'HEAD').decode().strip()
    output = ROOT / 'dist' / SOURCE_ARCHIVE
    if output.exists():
        raise FileExistsError(f'Preserve or rename the previous source archive first: {output}')
    modules = []
    for record in git('ls-tree', '-rz', 'HEAD').split(b'\0'):
        if record.startswith(b'160000 '):
            metadata, path = record.split(b'\t', 1)
            modules.append((path.decode(), metadata.split()[2].decode()))
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as target:
        for path, revision in [('', commit), *modules]:
            prefix = ARCHIVE_STEM + '/' + (path + '/' if path else '')
            data = git('archive', '--format=zip', f'--prefix={prefix}', revision, cwd=ROOT / path)
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                for item in archive.infolist():
                    if not item.is_dir(): target.writestr(item, archive.read(item.filename))
        target.writestr(ARCHIVE_STEM + '/SOURCE_REVISION.txt', commit + '\n')
        target.writestr(ARCHIVE_STEM + '/SUBMODULE_REVISIONS.txt',
                        ''.join(f'{revision} {path}\n' for path, revision in modules))
    print(f'Source archive: {output}\nCommit: {commit}\nPinned submodules: {len(modules)}')


if __name__ == '__main__':
    main()
