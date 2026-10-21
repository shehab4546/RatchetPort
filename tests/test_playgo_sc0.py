"""Sc0 repair must not confuse a valid SFO with a complete system directory."""
from pathlib import Path
import tempfile
import unittest
from unittest import mock
from test_launcher_controls import launcher, sfo_bytes, BASE_SFO
from playgo_fixture import playgo_bytes


class Sc0PlayGoTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.game = Path(temp.name) / 'Image0'
        self.source = Path(temp.name) / 'Sc0'
        (self.game / 'sce_sys').mkdir(parents=True)
        self.source.mkdir()
        (self.game / 'eboot.bin').write_bytes(b'synthetic')
        for path in (self.game / 'sce_sys/param.sfo', self.source / 'param.sfo'):
            path.write_bytes(BASE_SFO)
        (self.source / 'playgo-chunk.dat').write_bytes(playgo_bytes())

    def test_missing_playgo_with_existing_sfo_is_offered_and_copied(self):
        sfo = self.game / 'sce_sys/param.sfo'
        before = sfo.stat().st_mtime_ns, sfo.read_bytes()
        self.assertEqual(launcher.system_files_beside(self.game), self.source)
        self.assertEqual(launcher.adopt_system_files(self.source, self.game), ['playgo-chunk.dat'])
        self.assertEqual((sfo.stat().st_mtime_ns, sfo.read_bytes()), before)
        self.assertEqual(launcher.playgo_state(self.game / 'sce_sys/playgo-chunk.dat'), 'ok')
        self.assertIsNone(launcher.system_files_beside(self.game))
        self.assertEqual(launcher.adopt_system_files(self.source, self.game), [])

    def test_good_files_are_preserved_including_different_valid_metadata(self):
        target = self.game / 'sce_sys/playgo-chunk.dat'
        target.write_bytes(playgo_bytes(5))
        (self.game / 'sce_sys/icon0.png').write_bytes(b'existing icon')
        (self.source / 'icon0.png').write_bytes(b'source icon')
        before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in target.parent.iterdir()}
        self.assertEqual(launcher.adopt_system_files(self.source, self.game), [])
        self.assertEqual(before, {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in target.parent.iterdir()})

    def test_reject_mismatched_title_version_and_content(self):
        for values in ({'TITLE_ID': 'CUSA00001', 'APP_VER': '01.00'},
                       {'TITLE_ID': 'CUSA01047', 'APP_VER': '01.02'},
                       {'TITLE_ID': 'CUSA01047'}):
            with self.subTest(values=values):
                (self.source / 'param.sfo').write_bytes(sfo_bytes(**values))
                self.assertIsNone(launcher.system_files_beside(self.game))
                with self.assertRaises(ValueError):
                    launcher.adopt_system_files(self.source, self.game)
                self.assertFalse((self.game / 'sce_sys/playgo-chunk.dat').exists())
        (self.source / 'param.sfo').write_bytes(BASE_SFO)
        (self.game / 'sce_sys/param.sfo').write_bytes(sfo_bytes(
            TITLE_ID='CUSA01047', APP_VER='01.00', CONTENT_ID='different-content'))
        self.assertIsNone(launcher.system_files_beside(self.game))
        with self.assertRaises(ValueError):
            launcher.adopt_system_files(self.source, self.game)

    def test_changed_source_is_rechecked_before_copy(self):
        self.assertEqual(launcher.system_files_beside(self.game), self.source)
        (self.source / 'param.sfo').write_bytes(sfo_bytes(TITLE_ID='CUSA00001', APP_VER='01.00'))
        with self.assertRaises(ValueError):
            launcher.adopt_system_files(self.source, self.game)
        self.assertFalse((self.game / 'sce_sys/playgo-chunk.dat').exists())

    def test_invalid_metadata_is_not_copied(self):
        (self.source / 'playgo-chunk.dat').write_bytes(b'broken')
        self.assertIsNone(launcher.system_files_beside(self.game))
        with self.assertRaises(ValueError):
            launcher.adopt_system_files(self.source, self.game)
        self.assertFalse((self.game / 'sce_sys/playgo-chunk.dat').exists())

    def test_invalid_target_can_be_repaired(self):
        (self.game / 'sce_sys/playgo-chunk.dat').write_bytes(b'broken')
        self.assertEqual(launcher.adopt_system_files(self.source, self.game), ['playgo-chunk.dat'])
        self.assertEqual(launcher.playgo_state(self.game / 'sce_sys/playgo-chunk.dat'), 'ok')

    def test_play_offers_repair_before_preflight_or_process_start(self):
        app = launcher.Launcher.__new__(launcher.Launcher)
        app.process = None
        app.collect = mock.Mock(return_value=True)
        app.offer_system_files = mock.Mock(return_value=False)
        with mock.patch('ratchet_game.validate_game') as validate, mock.patch.object(launcher.subprocess, 'Popen') as start:
            app.play()
        app.offer_system_files.assert_called_once()
        validate.assert_not_called()
        start.assert_not_called()


if __name__ == '__main__':
    unittest.main()
