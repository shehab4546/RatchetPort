import tempfile
from pathlib import Path
"""The title font (Cinzel Black): an optional launcher asset, never a reason the launcher cannot start."""
import ctypes
import sys
import unittest
from pathlib import Path
from unittest import mock

from paths import ROOT
sys.path.insert(0, str(ROOT / 'launcher'))
import ratchetport_launcher_win as launcher  # noqa: E402


class FontFileTest(unittest.TestCase):
    def test_font_file_is_a_launcher_asset_under_port_dir(self):
        # Frozen builds find launcher assets next to the exe (PORT_DIR / 'launcher'), like ratchetport.ico.
        self.assertEqual(launcher.FONT_FILE, launcher.PORT_DIR / 'launcher' / 'Cinzel-Black.ttf')
        self.assertTrue(launcher.FONT_FILE.is_file())

    def test_windows_package_ships_the_font_and_license(self):
        import runpy
        package = runpy.run_path(str(ROOT / 'packaging/windows/package.py'))
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            package['copy_launcher_assets'](target)
            for name in ('Cinzel-Black.ttf', 'OFL-Cinzel.txt'):
                self.assertEqual((target / 'launcher' / name).read_bytes(), (ROOT / 'launcher' / name).read_bytes())


class RegisterFontTest(unittest.TestCase):
    def test_missing_file_is_not_fatal(self):
        self.assertFalse(launcher.register_font(Path('no-such-font.ttf')))

    @unittest.skipUnless(sys.platform == 'win32', 'GDI font registration')
    def test_file_that_is_not_a_font_is_refused(self):
        self.assertFalse(launcher.register_font(Path(launcher.__file__)))

    @unittest.skipUnless(sys.platform == 'win32', 'GDI font registration')
    def test_font_file_registers(self):
        self.assertTrue(launcher.register_font(launcher.FONT_FILE))

    @unittest.skipUnless(sys.platform.startswith('linux'), 'fontconfig font registration')
    def test_font_file_registers_through_fontconfig(self):
        try:
            ctypes.CDLL('libfontconfig.so.1')
        except OSError:
            self.skipTest('no fontconfig')
        self.assertTrue(launcher.register_font(launcher.FONT_FILE))

    def test_a_missing_fontconfig_is_not_fatal(self):
        with mock.patch.object(launcher, 'WINDOWS', False), \
                mock.patch.object(launcher.ctypes, 'CDLL', side_effect=OSError('no fontconfig')):
            self.assertFalse(launcher.register_font(launcher.FONT_FILE))


class HeadingFontTest(unittest.TestCase):
    def setUp(self):
        self.saved = launcher.LANG, launcher.FONT_LOADED

    def tearDown(self):
        launcher.LANG, launcher.FONT_LOADED = self.saved

    def test_english_titles_use_the_loaded_font(self):
        launcher.LANG, launcher.FONT_LOADED = 'en', True
        self.assertEqual(launcher.heading_font(12), ('Cinzel Black', 12))

    def test_other_languages_keep_the_fallback(self):
        launcher.LANG, launcher.FONT_LOADED = 'ru', True
        self.assertEqual(launcher.heading_font(12), ('Georgia', 12))
        self.assertEqual(launcher.heading_font(11, 'Segoe UI'), ('Segoe UI', 11))

    def test_unloaded_font_keeps_the_fallback(self):
        launcher.LANG, launcher.FONT_LOADED = 'en', False
        self.assertEqual(launcher.heading_font(20), ('Georgia', 20))

    def test_game_name_uses_the_font_in_every_language(self):
        launcher.LANG, launcher.FONT_LOADED = 'ru', True
        self.assertEqual(launcher.heading_font(15, every_language=True), ('Cinzel Black', 15))
        launcher.FONT_LOADED = False
        self.assertEqual(launcher.heading_font(15, every_language=True), ('Georgia', 15))


class LatinHeadingsTest(unittest.TestCase):
    """Latin-script languages use the loaded face; the other scripts keep the fallback."""
    def setUp(self):
        self.saved = launcher.LANG, launcher.FONT_LOADED
        launcher.FONT_LOADED = True

    def tearDown(self):
        launcher.LANG, launcher.FONT_LOADED = self.saved

    def test_latin_script_languages_use_the_loaded_font(self):
        for lang in ('pt', 'es', 'fr', 'de', 'it', 'pl', 'tr'):
            launcher.LANG = lang
            self.assertEqual(launcher.heading_font(12), ('Cinzel Black', 12), lang)

    def test_other_scripts_keep_the_fallback(self):
        for lang in ('ru', 'ar'):
            launcher.LANG = lang
            self.assertEqual(launcher.heading_font(12), ('Georgia', 12), lang)

    def test_the_face_has_every_latin_ui_letter(self):
        """Headings keep their accents (GRÁFICOS, AVANÇADO): every letter of the Latin-script
        translations must be in the face, or Tk would draw it in another font."""
        try:
            from fontTools.ttLib import TTFont
        except ImportError:
            self.skipTest('fontTools reads the face')
        import ratchetport_lang
        cmap = TTFont(launcher.FONT_FILE).getBestCmap()
        for lang in launcher.LATIN_UI_LANGUAGES:
            text = ''.join(ratchetport_lang.table(lang).values()).upper()
            missing = {c for c in text if c.isalpha() and ord(c) not in cmap}
            self.assertFalse(missing, lang)


if __name__ == '__main__':
    unittest.main()
