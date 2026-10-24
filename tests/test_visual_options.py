# SPDX-License-Identifier: GPL-2.0-or-later
from paths import ROOT
from pathlib import Path
import itertools
import tempfile
import unittest
import graphics_options as graphics
import motion_blur as blur
import shadow_resolution as shadows
import frame_timing as timing


class VisualOptionsTests(unittest.TestCase):
    def test_unknown_values_restore_original(self):
        for value in ('', 'OFF', 'on', '512px', '1024junk', '2048', None):
            self.assertEqual(blur.normalize(value), 'original')
            self.assertEqual(shadows.normalize(value), 'original')
        self.assertEqual(blur.normalize('off'), 'off')

    def test_every_combination_replaces_stale_groups_independently(self):
        stale = [timing.FPS60_GROUP, blur.BLUR_OFF_GROUP, *shadows.GROUPS.values(), 'unreviewed']
        for fps, mb, cap in itertools.product(('30', '60'), ('original', 'off'), ('original', *shadows.CAPS)):
            names = timing.requested_groups(fps, stale)
            names = blur.requested_groups(mb, names)
            names = shadows.requested_groups(cap, names)
            expected = ['unreviewed']
            if fps == '60': expected.append(timing.FPS60_GROUP)
            if mb == 'off': expected.append(blur.BLUR_OFF_GROUP)
            if cap != 'original': expected.append(shadows.GROUPS[cap])
            self.assertEqual(names, expected)
            report = {'prepared': names}
            self.assertEqual(blur.launch_environment(report)['RATCHET_MOTION_BLUR'], mb)
            self.assertEqual(shadows.launch_environment(report)['RATCHET_SHADOW_RESOLUTION'], cap)

    def test_requested_or_rejected_is_not_applied(self):
        names = [blur.BLUR_OFF_GROUP, *shadows.GROUPS.values()]
        for report in ({}, {'requested': names}, {'skipped': dict.fromkeys(names, 'hash mismatch')},
                       {'prepared': [timing.FPS60_GROUP]}, {'prepared': list(shadows.GROUPS.values())}):
            self.assertEqual(blur.launch_environment(report)['RATCHET_MOTION_BLUR'], 'original')
            self.assertEqual(shadows.launch_environment(report)['RATCHET_SHADOW_RESOLUTION'], 'original')

    def test_save_restart_rollback_and_original(self):
        with tempfile.TemporaryDirectory() as tmp:
            ini, state = Path(tmp)/'ratchet.ini', Path(tmp)/'state.json'
            graphics.prepare(ini, state)
            graphics.write_keys(ini, {'motion_blur': 'off', 'shadow_resolution': '512', 'restart_unconfirmed': '1'})
            options, reverted = graphics.prepare(ini, state)
            self.assertFalse(reverted)
            self.assertEqual((options['motion_blur'], options['shadow_resolution']), ('off', '512'))
            options, reverted = graphics.prepare(ini, state)
            self.assertTrue(reverted)
            self.assertEqual((options['motion_blur'], options['shadow_resolution']), ('original', 'original'))
            graphics.write_keys(ini, {'motion_blur': 'off', 'shadow_resolution': '256', 'restart_unconfirmed': '0'})
            self.assertEqual(graphics.prepare(ini, state)[0]['shadow_resolution'], '256')
            graphics.write_keys(ini, {'motion_blur': 'original', 'shadow_resolution': 'original'})
            options, _ = graphics.prepare(ini, state)
            names = blur.requested_groups(options['motion_blur'], [blur.BLUR_OFF_GROUP])
            names = shadows.requested_groups(options['shadow_resolution'], names + list(shadows.GROUPS.values()))
            self.assertEqual(names, [])


if __name__ == '__main__':
    unittest.main()
