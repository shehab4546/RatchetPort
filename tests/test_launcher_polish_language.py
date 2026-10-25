"""Keep UI translations separate from the supported USA game-language list."""
import re
import sys
import unittest

from paths import ROOT
sys.path.insert(0, str(ROOT / 'launcher'))
import ratchetport_lang  # noqa: E402
import ratchetport_launcher_win as launcher  # noqa: E402


class PolishLanguageTest(unittest.TestCase):
    def test_polish_is_not_advertised_as_supported_by_usa(self):
        self.assertNotIn('16', dict(launcher.LANGUAGES))
        self.assertIn('Unavailable in USA', dict(launcher.game_language_options('16'))['16'][0])

    def test_old_polish_preference_has_explicit_english_fallback(self):
        env = launcher.game_environment({**launcher.APP_DEFAULTS, 'language': '16'})
        self.assertEqual(env['RATCHET_LANGUAGE'], '1')

    def test_polish_label_is_translated_across_ui_languages(self):
        expected_translations = {
            'pt': 'Polonês',
            'es': 'Polaco',
            'pl': 'Polski',
            'fr': 'Polonais',
            'de': 'Polnisch',
            'it': 'Polacco',
            'tr': 'Lehçe',
            'ar': 'البولندية',
            'zh': '波兰语',
            'ja': 'ポーランド語',
            'ko': '폴란드어',
        }
        for lang, expected in expected_translations.items():
            with self.subTest(lang=lang):
                self.assertEqual(ratchetport_lang.table(lang).get('Polish'), expected)

    def test_russian_and_english_fallbacks(self):
        saved = launcher.LANG
        try:
            launcher.LANG = 'ru'
            self.assertEqual(launcher._('Polish', 'Польский'), 'Польский')
            launcher.LANG = 'en'
            self.assertEqual(launcher._('Polish', 'Польский'), 'Polish')
        finally:
            launcher.LANG = saved

    def test_system_service_contract_maps_parameter_1_to_ratchetport_language(self):
        services_src = (ROOT / 'src' / 'runtime_services.c').read_text(encoding='utf-8')
        # SystemService system_param: case 1 returns language()
        self.assertRegex(services_src, r'case\s+1:\s*\*value\s*=\s*language\(\);')
        # language() parses getenv("RATCHET_LANGUAGE")
        self.assertRegex(services_src, r'getenv\("RATCHET_LANGUAGE"\)')


if __name__ == '__main__':
    unittest.main()
