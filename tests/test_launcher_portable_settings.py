"""Portable launcher settings: store settings.json in DATA_DIR next to ratchet.ini (#561)."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock

import sys
from paths import ROOT
sys.path.insert(0, str(ROOT / 'launcher'))
import ratchetport_launcher_win as launcher


class PortableSettingsPathsTest(unittest.TestCase):
    def test_config_dir_is_data_dir(self):
        self.assertEqual(launcher.CONFIG_DIR, launcher.DATA_DIR)
        self.assertEqual(launcher.CONFIG_FILE, launcher.DATA_DIR / 'settings.json')

    def test_user_files_includes_settings_and_icon(self):
        self.assertIn('settings.json', launcher.USER_FILES)
        self.assertIn('game_icon.ico', launcher.USER_FILES)


class PortableSettingsMigrationTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.data_dir = self.root / 'data'
        self.legacy_dir = self.root / 'legacy'
        self.data_dir.mkdir()
        self.legacy_dir.mkdir()
        self.target = self.data_dir / 'settings.json'
        self.legacy = self.legacy_dir / 'settings.json'

    def test_other_product_settings_are_not_imported(self):
        self.legacy.write_text('{"game_dir": "other-game"}', encoding='utf-8')
        launcher.migrate_portable_settings(config_file=self.target, legacy_file=self.legacy)
        self.assertFalse(self.target.exists())
        self.assertEqual(self.legacy.read_text(), '{"game_dir": "other-game"}')

    def test_does_not_overwrite_existing_portable_config(self):
        self.target.write_text('{"game_dir": "D:/Games/Portable"}', encoding='utf-8')
        self.legacy.write_text('{"game_dir": "D:/Games/OldAppData"}', encoding='utf-8')

        launcher.migrate_portable_settings(config_file=self.target, legacy_file=self.legacy)

        self.assertEqual(json.loads(self.target.read_text(encoding='utf-8')),
                         {'game_dir': 'D:/Games/Portable'})

    def test_missing_legacy_config_is_a_noop(self):
        launcher.migrate_portable_settings(config_file=self.target, legacy_file=self.legacy)
        self.assertFalse(self.target.is_file())

    def test_load_app_settings_migrates_and_merges_defaults(self):
        self.target.write_text('{"game_dir": "C:/Games/RatchetPort"}', encoding='utf-8')
        with mock.patch.object(launcher, 'CONFIG_FILE', self.target), \
                mock.patch.object(launcher, 'LEGACY_CONFIG_FILE', self.legacy):
            settings = launcher.load_app_settings(self.target)

        self.assertEqual(settings['game_dir'], 'C:/Games/RatchetPort')
        self.assertEqual(settings['ui_scale'], launcher.APP_DEFAULTS['ui_scale'])
        self.assertTrue(self.target.is_file())

    def test_packaging_rejects_user_files_without_modifying_them(self):
        import runpy
        audit = runpy.run_path(str(ROOT / 'packaging/windows/package.py'))['audit']
        for name in ('settings.json', 'game_icon.ico'):
            target = self.data_dir / name
            target.write_bytes(b'private user data')
            with self.assertRaises(ValueError):
                audit(self.data_dir)
            self.assertEqual(target.read_bytes(), b'private user data')
            target.unlink()

    def test_packaging_rejects_embedded_checkout_paths(self):
        import runpy
        audit = runpy.run_path(str(ROOT / 'packaging/windows/package.py'))['audit']
        target = self.data_dir / 'runtime.exe'
        for spelling in (str(ROOT), ROOT.as_posix()):
            for encoding in ('utf-8', 'utf-16-le'):
                target.write_bytes(b'MZ' + spelling.encode(encoding))
                with self.assertRaisesRegex(ValueError, 'Local build path'):
                    audit(self.data_dir)


if __name__ == '__main__':
    unittest.main()
