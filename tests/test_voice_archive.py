# SPDX-License-Identifier: GPL-2.0-or-later
import tempfile
import unittest
from pathlib import Path
from paths import ROOT
import voice_archive as voice


class ArchiveChecks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.path = self.root / 'asset_archive/a00s007.fr'
        self.path.parent.mkdir()

    def check(self):
        return voice.inspect(self.root, '2')

    def test_missing(self):
        self.assertEqual(self.check()['integrity'], 'WARNING')

    def test_empty_and_small(self):
        for data in (b'', b'RIFF', b'RIFF0000WAVE'):
            self.path.write_bytes(data)
            self.assertEqual(self.check()['integrity'], 'WARNING')

    def test_repeated_megabyte(self):
        block = b'RIFF0000WAVE' + bytes(voice.BLOCK - 12)
        with self.path.open('wb') as stream:
            for _ in range(197):
                stream.write(block)
        result = self.check()
        self.assertEqual(result['integrity'], 'FAILED')
        self.assertEqual(result['sampled_blocks'], 8)
        self.assertIn('French', voice.warning(result))
        self.assertIn('still start', voice.warning(result))

    def test_varied_valid_headers(self):
        with self.path.open('wb') as stream:
            for i in range(12):
                stream.write(b'RIFF0000WAVE' + bytes([i]) * (voice.BLOCK - 12))
        self.assertEqual(self.check()['integrity'], 'OK')

    def test_unrecognized_format_is_inconclusive(self):
        self.path.write_bytes(b'not audio' * 2048)
        self.assertEqual(self.check()['integrity'], 'UNKNOWN')

    def test_locale_mapping_is_not_renamed(self):
        self.assertEqual(voice.inspect(self.root, '20')['archive'], 'asset_archive/a00s017.mx')
        self.assertEqual(voice.inspect(self.root, '17')['archive'], 'asset_archive/a00s018.br')
