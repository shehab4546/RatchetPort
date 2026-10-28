# SPDX-License-Identifier: GPL-2.0-or-later
"""Exercise the actual C pool selection across separate process starts."""
from paths import ROOT
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


@unittest.skipUnless(sys.platform == 'linux' and shutil.which('cc'), 'Linux C compiler required')
class ResolutionMemoryTests(unittest.TestCase):
    def test_resolution_floor_and_manual_override_survive_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, exe = Path(tmp) / 'pool.c', Path(tmp) / 'pool'
            source.write_text('#include "runtime_memory.c"\n'
                              'int main(int argc, char **argv) {\n'
                              ' if (argc != 2) return 2;\n'
                              ' return pool_size_bytes() != strtoull(argv[1], NULL, 10) * 1024 * 1024;\n}\n')
            subprocess.run(['cc', '-O2', '-ffunction-sections', '-fdata-sections',
                            '-Wl,--gc-sections', '-pthread', '-I', str(ROOT / 'src'),
                            str(source), '-o', str(exe)], check=True, capture_output=True)
            cases = [(None, None, 5056), (None, '5440', 5440), (None, '5824', 5824),
                     ('8192', '5824', 8192), ('5056', '5824', 5824), ('4000', '5824', 5824),
                     ('20000', '5824', 5824), ('junk', '5824', 5824), ('8192', None, 8192),
                     (None, '20000', 5056), (None, '4000', 5056), (None, 'junk', 5056)]
            for manual, floor, expected in cases:
                with self.subTest(manual=manual, floor=floor):
                    env = dict(os.environ)
                    for key, value in (('RATCHET_DMEM_MB', manual), ('RATCHET_RESOLUTION_DMEM_MB', floor)):
                        env.pop(key, None)
                        if value is not None:
                            env[key] = value
                    subprocess.run([str(exe), str(expected)], env=env, check=True)
