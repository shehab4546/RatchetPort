"""Ratchet launch preflight must reject other builds and never modify the game dump."""
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest import mock
from test_launcher_controls import launcher, sfo_bytes
from ratchet_game import validate_game
from playgo_fixture import playgo_bytes

class LauncherGameFilesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.game = Path(self.temp.name) / 'game'
        (self.game / 'sce_sys').mkdir(parents=True)
        (self.game / 'sce_module').mkdir()
        for name in ('eboot.bin', 'sce_module/libc.prx', 'sce_module/libSceFios2.prx'):
            (self.game / name).write_bytes(b'synthetic file')
        self.sfo()
        (self.game / "sce_sys/playgo-chunk.dat").write_bytes(playgo_bytes())

    def sfo(self, title='CUSA01047', version='01.00'):
        (self.game / 'sce_sys/param.sfo').write_bytes(sfo_bytes(TITLE_ID=title, APP_VER=version))

    def snapshot(self):
        return {str(p.relative_to(self.game)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in self.game.rglob('*') if p.is_file()}

    def test_supported_dump_is_accepted_without_changes(self):
        before = self.snapshot()
        self.assertEqual(validate_game(self.game)['TITLE_ID'], 'CUSA01047')
        self.assertTrue(launcher.ready_to_play(self.game))
        self.assertEqual(self.snapshot(), before)

    def test_other_titles_and_versions_are_rejected(self):
        for title, version in [('CUSA01623', '01.00'), ('CUSA01715', '01.00'),
                               ('CUSA01740', '01.00'), ('CUSA01047', '01.02'), ('', '01.00')]:
            with self.subTest(title=title, version=version):
                self.sfo(title, version)
                before = self.snapshot()
                with self.assertRaises(ValueError): validate_game(self.game)
                self.assertFalse(launcher.ready_to_play(self.game))
                self.assertEqual(self.snapshot(), before)

    def test_missing_or_empty_required_files_are_rejected(self):
        for name in ('eboot.bin', 'sce_sys/param.sfo', 'sce_module/libc.prx', 'sce_module/libSceFios2.prx', 'sce_sys/playgo-chunk.dat'):
            path = self.game / name
            data = path.read_bytes()
            for empty in (False, True):
                if empty: path.write_bytes(b'')
                else: path.unlink()
                with self.assertRaisesRegex(ValueError, 'Missing or empty'): validate_game(self.game)
                path.write_bytes(data)

    def test_separate_updates_are_not_accepted(self):
        self.assertFalse(launcher.ready_to_play(self.game, 'update'))

    def test_ui_refuses_invalid_dump_without_copying_or_launching(self):
        self.sfo('CUSA01623')
        before = self.snapshot()
        app = launcher.Launcher.__new__(launcher.Launcher)
        app.process = None
        app.collect = mock.Mock(return_value=True)
        app.app = {**launcher.APP_DEFAULTS, 'game_dir': str(self.game)}
        app.messagebox = mock.Mock()
        with mock.patch.object(launcher.subprocess, 'Popen') as start:
            app.play()
            start.assert_not_called()
        app.messagebox.showerror.assert_called_once()
        self.assertEqual(self.snapshot(), before)

if __name__ == '__main__': unittest.main()
