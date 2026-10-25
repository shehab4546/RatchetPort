# SPDX-License-Identifier: GPL-2.0-or-later
from paths import ROOT
from pathlib import Path
import itertools
import tempfile
import unittest
import graphics_options as graphics
import internal_resolution as resolution
import motion_blur as blur
import shadow_resolution as shadows
import frame_timing as timing
import ratchet_patches as patches


class InternalResolutionTests(unittest.TestCase):
    def test_all_modes_replace_stale_groups_and_keep_other_controls(self):
        stale = [*resolution.GROUPS.values(), timing.FPS60_GROUP, blur.BLUR_OFF_GROUP,
                 *shadows.GROUPS.values(), 'unreviewed']
        for mode, fps, mb, cap in itertools.product(('original', *resolution.SIZES), ('30', '60'),
                                                    ('original', 'off'), ('original', *shadows.CAPS)):
            names = timing.requested_groups(fps, stale)
            names = blur.requested_groups(mb, names)
            names = shadows.requested_groups(cap, names)
            before = [n for n in names if n not in resolution.GROUPS.values()]
            names = resolution.requested_groups(mode, names)
            self.assertEqual(names, before + ([resolution.GROUPS[mode]] if mode != 'original' else []))
            self.assertEqual(resolution.launch_environment({'prepared': names}), {'RATCHET_INTERNAL_RESOLUTION': mode})
            self.assertEqual(timing.FPS60_GROUP in names, fps == '60')
            self.assertEqual(blur.BLUR_OFF_GROUP in names, mb == 'off')

    def test_rejected_ambiguous_and_unknown_modes_cannot_enable_override(self):
        for value in ('', '4k', '8K', '3840x2160', '1080pjunk', None):
            self.assertEqual(resolution.normalize(value), 'original')
        for report in ({}, {'requested': list(resolution.GROUPS.values())},
                       {'skipped': dict.fromkeys(resolution.GROUPS.values(), 'hash mismatch')},
                       {'prepared': list(resolution.GROUPS.values())}):
            self.assertEqual(resolution.launch_environment(report), {'RATCHET_INTERNAL_RESOLUTION': 'original'})

    def test_restart_rollback_original_and_output_independence(self):
        with tempfile.TemporaryDirectory() as tmp:
            ini, state = Path(tmp)/'ratchet.ini', Path(tmp)/'state.json'
            graphics.write_keys(ini, {'output_res': '1280x720', 'render_resolution': 'native'})
            graphics.prepare(ini, state)
            graphics.write_keys(ini, {'internal_resolution': '4K', 'restart_unconfirmed': '1'})
            options, reverted = graphics.prepare(ini, state)
            self.assertFalse(reverted)
            self.assertEqual(options['internal_resolution'], '4K')
            self.assertEqual(options['render_resolution'], 'native')
            self.assertEqual(graphics.read_ini(ini)['output_res'], '1280x720')
            options, reverted = graphics.prepare(ini, state)
            self.assertTrue(reverted)
            self.assertEqual(options['internal_resolution'], 'original')
            for mode in resolution.SIZES:
                graphics.write_keys(ini, {'internal_resolution': mode, 'restart_unconfirmed': '0'})
                self.assertEqual(graphics.prepare(ini, state)[0]['internal_resolution'], mode)
            graphics.write_keys(ini, {'internal_resolution': 'original'})
            options, _ = graphics.prepare(ini, state)
            self.assertEqual(resolution.requested_groups(options['internal_resolution'], resolution.GROUPS.values()), [])

    def test_selector_replacement_contract_and_alignment(self):
        for mode, (width, height) in resolution.SIZES.items():
            site = patches.PROFILE['groups'][resolution.GROUPS[mode]]['writes'][0]
            before, after = bytes.fromhex(site['original_hex']), bytes.fromhex(site['replacement_hex'])
            self.assertEqual((len(before), len(after)), (26, 26))
            self.assertEqual(after[:2], b'\xc7\x06')
            self.assertEqual(int.from_bytes(after[2:6], 'little'), width)
            self.assertEqual(after[6:8], b'\xc7\x02')
            self.assertEqual(int.from_bytes(after[8:12], 'little'), height)
            self.assertEqual(after[12:], b'\xb0\x01\xc3' + b'\x90'*11)
            self.assertEqual((width % 4, height % 4, width*9 == height*16), (0, 0, True))


if __name__ == '__main__':
    unittest.main()
