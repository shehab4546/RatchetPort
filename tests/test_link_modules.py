"""link_modules.module on a synthetic SELF: reads the file once and reports its hash."""
import hashlib
import copy
import json
import struct
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from paths import ROOT  # noqa: F401  (sys.path for scripts/)
import link_modules
from test_link_libc import self_fixture
import test_link_libc
from test_probe import package


class ModuleTests(unittest.TestCase):
    def test_third_module_binds_by_identity_and_gets_independent_tls(self):
        main, libc = test_link_libc.LinkTests().fixture()
        toolkit_key = ('toolkitFixture', ('libSceNpToolkit', 1), ('libSceNpToolkit', 0))
        main['identity'] = lambda name: toolkit_key
        fios, toolkit = copy.deepcopy(libc), copy.deepcopy(libc)
        fios['symbols'][1]['identity'] = ('fiosFixture', ('libSceFios2', 1), ('libSceFios2', 0))
        toolkit['symbols'][1]['identity'] = toolkit_key
        toolkit['relocs'] = [(64, 16, 0, 0)]
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            (out / 'boot.bin').write_bytes(package(b'\xc3', names=['toolkitFixture#d#b'], capabilities=1))
            with patch.object(link_modules, 'module', side_effect=[main, libc, fios, toolkit]):
                link_modules.link(Path('fixture-game'), out,
                                  ('libc.prx', 'libSceFios2.prx', 'libSceNpToolkit.prx'))
            raw = (out / 'boot-linked.bin').read_bytes()
            report = json.loads((out / 'link.json').read_text())
        self.assertEqual(report['unresolved_imports'], [])
        self.assertEqual([m['tls_module'] for m in report['modules']], [2, 3, 4])
        self.assertEqual(report['modules'][2]['tls_relocations'], 1)
        magic, size, _, ns, nr, ni, _ = struct.unpack_from('<8s6Q', raw)
        self.assertEqual(magic, b'G3PROBE5')
        nm = struct.unpack_from('<Q', raw, 96)[0]
        nb = struct.unpack_from('<Q', raw, 104 + nm * 56)[0]
        binding = struct.unpack_from('<3Q', raw, 112 + nm * 56)
        toolkit_base = int(report['modules'][2]['base'], 16)
        self.assertEqual(binding, (0, toolkit_base + 16, 1))
        image_at = 112 + nm * 56 + nb * 24 + ns * 24 + ni * 128 + nr * 32
        self.assertEqual(len(raw) - image_at, size)
        self.assertEqual(struct.unpack_from('<Q', raw, image_at + toolkit_base + 64)[0], 4)

    def test_module_accepts_unpacked_elf_with_the_same_exports(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'libc.prx'
            source = self_fixture()
            path.write_bytes(source)
            expected = link_modules.module(path)
            elf = link_modules.parse_self(source)[0]
            path.write_bytes(elf)
            actual = link_modules.module(path)
        self.assertEqual(actual['symbols'], expected['symbols'])
        self.assertEqual(actual['ph'], expected['ph'])
        self.assertEqual(actual['relocs'], expected['relocs'])
        self.assertEqual(actual['sha256'], hashlib.sha256(elf).hexdigest())

    def test_module_reads_the_file_once_and_reports_its_hash(self):
        data = self_fixture()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'libc.prx'
            path.write_bytes(data)
            info = link_modules.module(path)
        self.assertEqual(info['sha256'], hashlib.sha256(data).hexdigest())
        self.assertEqual(info['missing'], [])
        self.assertEqual(info['symbols'][0]['identity'], ('bzQExy189ZI', ('libc', 1), ('libc', 1)))


if __name__ == '__main__':
    unittest.main()
