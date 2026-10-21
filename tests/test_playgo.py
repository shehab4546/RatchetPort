"""Header/preflight regressions and real C resolver checks on synthetic metadata."""
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
from paths import ROOT
from playgo_fixture import playgo_bytes
from ratchet_game import playgo_header_chunks, validate_playgo


def invalid_metadata():
    valid = playgo_bytes()
    yield 'empty', b''
    yield 'twelve-byte-header', valid[:12]
    yield 'short-header', valid[:255]
    yield 'truncated-tables', valid[:-1]
    yield 'trailing-data', valid + b'x'
    for name, offset, fmt, value in (
            ('magic', 0, '<I', 0), ('zero-chunks', 10, '<H', 0),
            ('too-many-chunks', 10, '<H', 1001), ('too-many-mchunks', 12, '<H', 8001),
            ('too-many-scenarios', 14, '<H', 33), ('file-size', 16, '<I', 0xffffffff),
            ('range-overflow', 192, '<I', 0xfffffff0), ('range-in-header', 192, '<I', 32),
            ('short-attrs', 196, '<I', 32), ('unaligned-attrs', 196, '<I', 95),
            ('short-mchunk-table', 12, '<H', 1), ('short-scenario-table', 14, '<H', 1)):
        data = bytearray(valid)
        struct.pack_into(fmt, data, offset, value)
        yield name, bytes(data)
    data = bytearray(valid)
    struct.pack_into('<II', data, 200, 256, 2)
    yield 'overlapping-sections', bytes(data)
    data = bytearray(valid)
    struct.pack_into('<II', data, 248, len(valid), 16)
    yield 'last-section-outside-file', bytes(data)


class PlayGoMetadataTests(unittest.TestCase):
    def test_valid_counts_are_read_not_assumed(self):
        for count in (1, 3, 72, 1000):
            data = playgo_bytes(count)
            self.assertEqual(playgo_header_chunks(data[:256], len(data)), count)

    def test_invalid_header_and_ranges(self):
        for name, data in invalid_metadata():
            with self.subTest(case=name), self.assertRaises(ValueError):
                playgo_header_chunks(data[:256], len(data))

    def test_errors_name_full_path(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'playgo-chunk.dat'
            path.write_bytes(b'bad')
            with self.assertRaises(ValueError) as error:
                validate_playgo(path)
            self.assertIn(str(path.resolve()), str(error.exception))


EXE = Path(os.environ.get('RATCHET_PLAYGO_TEST', ROOT / 'out/playgo-tests/playgo-resolver-test'))

@unittest.skipUnless(EXE.is_file(), 'build playgo-resolver-test first')
class PlayGoResolverTests(unittest.TestCase):
    def run_fixture(self, data, invalid=False):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'sce_sys/playgo-chunk.dat'
            path.parent.mkdir()
            if data is not None:
                path.write_bytes(data)
            command = [str(EXE.resolve()), directory] + (['invalid'] if invalid else [])
            result = subprocess.run(command, capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('PASS:', result.stdout)

    def test_real_resolver_and_contracts(self):
        self.run_fixture(playgo_bytes())

    def test_missing_metadata_does_not_initialize(self):
        self.run_fixture(None, invalid=True)

    def test_invalid_metadata_does_not_initialize(self):
        for name, data in invalid_metadata():
            with self.subTest(case=name):
                self.run_fixture(data, invalid=True)


if __name__ == '__main__':
    unittest.main()
