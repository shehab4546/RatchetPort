"""Game language selector: Brazilian Portuguese reaches the game as its system language id."""
import sys
import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from paths import ROOT
sys.path.insert(0, str(ROOT / 'launcher'))
import ratchetport_lang  # noqa: E402
import ratchetport_launcher_win as launcher  # noqa: E402


class GameLanguageTest(unittest.TestCase):
    def test_saved_latin_spanish_survives_loading_and_launch(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'settings.json'
            path.write_text(json.dumps({'language': '20', 'ui_language': 'es'}))
            with patch.object(launcher, 'CONFIG_FILE', path):
                settings = launcher.load_app_settings()
            self.assertEqual(settings['language'], '20')
            self.assertEqual(launcher.game_environment(settings)['RATCHET_LANGUAGE'], '20')
            self.assertIn('20', dict(launcher.game_language_options(settings['language'])))
            settings['ui_language'] = 'en'
            self.assertEqual(launcher.game_environment(settings)['RATCHET_LANGUAGE'], '20')

    def test_existing_custom_system_language_is_preserved(self):
        self.assertIn('21', dict(launcher.game_language_options('21')))
        self.assertEqual(launcher.game_environment({**launcher.APP_DEFAULTS, 'language': 20})['RATCHET_LANGUAGE'], '20')

    def test_only_na_supported_languages_are_offered(self):
        self.assertEqual(set(dict(launcher.LANGUAGES)), {'1', '2', '7', '17', '20'})
        for code in ('1', '2', '7', '17', '20', '22'):
            self.assertEqual(launcher.game_language_id(code), code)
        for code in ('0', '3', '4', '8', '16', '21', 'garbage'):
            self.assertEqual(launcher.game_language_id(code), '1')

    def test_brazilian_portuguese_is_offered_with_its_system_id(self):
        offered = {value: names[0] for value, names in launcher.LANGUAGES}
        self.assertEqual(offered.get('17'), 'Portuguese (Brazil)')

    def test_choosing_brazilian_portuguese_starts_the_game_with_id_17(self):
        env = launcher.game_environment({**launcher.APP_DEFAULTS, 'language': '17'})
        self.assertEqual(env['RATCHET_LANGUAGE'], '17')

    def test_brazilian_portuguese_label_is_translated_in_portuguese_and_spanish(self):
        self.assertEqual(ratchetport_lang.EXTRA['pt']['Portuguese (Brazil)'], 'Português (Brasil)')
        self.assertEqual(ratchetport_lang.EXTRA['es']['Portuguese (Brazil)'], 'Portugués (Brasil)')


if __name__ == '__main__':
    unittest.main()
