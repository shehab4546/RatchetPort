# SPDX-License-Identifier: GPL-2.0-or-later
import unittest
from paths import ROOT
import language_split as split
import graphics_presets as presets


class LanguageSplit(unittest.TestCase):
    def test_all_pairs_and_rejection(self):
        for text in split.GROUPS:
            for voice in split.GROUPS:
                groups = split.requested_groups(text, voice, ['Other'])
                self.assertEqual(groups[0], 'Other')
                self.assertEqual(split.launch_environment(text, voice, {'prepared': groups})['RATCHET_LANGUAGE'], voice)
                self.assertEqual(split.launch_environment(text, voice, {})['RATCHET_LANGUAGE'], text)

    def test_only_one_text_override_and_french_alias(self):
        groups = split.requested_groups('22', '1', list(split.GROUPS.values()))
        self.assertEqual(groups, [split.GROUPS['2']])
        self.assertEqual(split.normalize('19'), '1')

    def test_patch_lengths_and_immediates(self):
        for value in split.GROUPS:
            patch = split.writes(value)[0]
            code = bytes.fromhex(patch['replacement_hex'])
            self.assertEqual(len(code), len(bytes.fromhex(patch['original_hex'])))
            self.assertEqual(int.from_bytes(code[16:20], 'little'), split.TEXT_IDS[value])

    def test_presets_detect_manual_changes(self):
        for name, values in presets.PRESETS.items():
            self.assertEqual(presets.detect(values), name)
            self.assertEqual(presets.detect(dict(values, shadow_resolution='custom')), 'Custom')
            self.assertNotIn('language', values)
            self.assertNotIn('game_fps', values)
