"""packaging/windows/smoke-test.ps1 against a built package (RATCHET_WINDOWS_ZIP=path\\to\\RatchetPort-Windows-PreAlpha.zip):
it passes on the package as built and fails when a DLL, a frozen module or a shipped file is wrong."""
from paths import ROOT
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

SCRIPT = ROOT / 'packaging' / 'windows' / 'smoke-test.ps1'
PACKAGE = os.environ.get('RATCHET_WINDOWS_ZIP')


@unittest.skipUnless(sys.platform == 'win32' and PACKAGE, 'needs Windows and RATCHET_WINDOWS_ZIP')
class WindowsSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.tree = Path(cls.tmp.name) / 'tree'
        with zipfile.ZipFile(PACKAGE) as package:
            package.extractall(cls.tree)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def smoke(self, change=None):
        """Zips a copy of the package after `change(folder)` and returns the smoke test's exit code."""
        work = Path(tempfile.mkdtemp(dir=self.tmp.name))
        shutil.copytree(self.tree, work / 'tree')
        if change:
            change(work / 'tree' / 'RatchetPort')
        archive = shutil.make_archive(str(work / 'RatchetPort'), 'zip', work / 'tree')
        result = subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                                 str(SCRIPT), archive], capture_output=True, text=True, timeout=300)
        print(result.stdout, result.stderr, file=sys.stderr)
        return result.returncode

    def test_the_built_package_passes(self):
        self.assertEqual(self.smoke(), 0)

    def test_a_missing_dll_fails(self):
        self.assertNotEqual(self.smoke(lambda tree: (tree / 'bin' / 'SDL3.dll').unlink()), 0)

    def test_a_missing_frozen_module_fails(self):
        self.assertNotEqual(self.smoke(lambda tree: shutil.rmtree(tree / '_internal' / 'iced_x86')), 0)

    def test_a_shipped_player_file_fails(self):
        self.assertNotEqual(self.smoke(lambda tree: (tree / 'ratchet.ini').write_text('[ratchetport]\n')), 0)


if __name__ == '__main__':
    unittest.main()
