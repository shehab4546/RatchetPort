# SPDX-License-Identifier: GPL-2.0-or-later
from paths import ROOT
import tempfile
from pathlib import Path
import unittest
import frame_timing as timing
import graphics_options as graphics
import ratchet_patches as patches
from ratchet_binary_audit import Binary
from test_prepare import fixture
from test_ratchet_patches import profile


class FrameTimingTests(unittest.TestCase):
    def test_legacy_rates_never_enable_60(self):
        for value in ('', 'original', '120', '240', '60junk', None):
            self.assertEqual(timing.normalize(value), '30')
        self.assertEqual(graphics.startup_options({'engine_fps': '240'})['game_fps'], '30')
        self.assertEqual(timing.normalize('60'), '60')

    def test_original_removes_stale_group_but_preserves_unrelated_names(self):
        self.assertEqual(timing.requested_groups('30', [timing.FPS60_GROUP, 'unreviewed']), ['unreviewed'])
        self.assertEqual(timing.requested_groups('60', [timing.FPS60_GROUP]), [timing.FPS60_GROUP])

    def test_only_prepared_group_raises_host_ceiling(self):
        for report in ({}, {'requested': [timing.FPS60_GROUP]},
                       {'skipped': {timing.FPS60_GROUP: 'hash mismatch'}}, {'prepared': ['unrelated']}):
            self.assertEqual(timing.launch_environment(report)['RATCHET_ENGINE_FPS'], '30')
        env = timing.launch_environment({'prepared': [timing.FPS60_GROUP]})
        self.assertEqual(env, {'RATCHET_ENGINE_FPS': '60', 'RATCHET_FPS_LIMIT': '60', 'RATCHET_VBLANK_HZ': '60'})

    def test_host_limit_never_raises_guest_target_or_display_clock(self):
        for mode in (30, 60):
            report = {'prepared': [timing.FPS60_GROUP] if mode == 60 else []}
            for limit in ('0', '-1', '240', 'bad', None):
                self.assertEqual(timing.launch_environment(report, limit)['RATCHET_FPS_LIMIT'], str(mode))
            self.assertEqual(timing.launch_environment(report, '20')['RATCHET_FPS_LIMIT'], '20')
            self.assertEqual(timing.launch_environment(report, '20')['RATCHET_VBLANK_HZ'], '60')

    def test_save_restart_original_and_rollback(self):
        with tempfile.TemporaryDirectory() as tmp:
            ini, state = Path(tmp)/'ratchet.ini', Path(tmp)/'state.json'
            graphics.prepare(ini, state)
            graphics.write_keys(ini, {'game_fps': '60', 'restart_unconfirmed': '1'})
            self.assertEqual(graphics.prepare(ini, state)[0]['game_fps'], '60')
            restored, reverted = graphics.prepare(ini, state)
            self.assertTrue(reverted)
            self.assertEqual(restored['game_fps'], '30')
            graphics.write_keys(ini, {'game_fps': '60', 'restart_unconfirmed': '0'})
            self.assertEqual(graphics.prepare(ini, state)[0]['game_fps'], '60')
            graphics.write_keys(ini, {'game_fps': '30'})
            self.assertEqual(timing.requested_groups(graphics.prepare(ini, state)[0]['game_fps'],
                                                   [timing.FPS60_GROUP]), [])

    def test_pair_is_atomic_when_clock_original_does_not_match(self):
        # Use real replacement lengths/bytes at synthetic addresses, never game data.
        source = bytearray(fixture())
        # Two separate four-byte writes fit the fixture; simulate the frame and clock group.
        binary = Binary(bytes(source))
        p = profile(binary)
        p['groups'] = {timing.FPS60_GROUP: {'writes': [
            {'signature': '02 03 04 05', 'offset': 0, 'elf_vaddr': 2,
             'original_hex': '02 03 04 05', 'replacement_hex': '90 90 90 90'},
            {'signature': '0a 0b 0c 0d', 'offset': 0, 'elf_vaddr': 10,
             'original_hex': '0a 0b 0c 0d', 'replacement_hex': '90 90 90 90'}]}}
        image = bytes(range(16)) + bytes(16)
        writes, prepared, skipped = patches.compile_groups(binary, image, [(0,32,5)], [], [timing.FPS60_GROUP], p)
        self.assertEqual(len(writes), 2)
        damaged = image[:10] + b'\xff' + image[11:]
        writes, prepared, skipped = patches.compile_groups(binary, damaged, [(0,32,5)], [], [timing.FPS60_GROUP], p)
        self.assertEqual((writes, prepared), ([], []))
        self.assertIn('linking changed', skipped[timing.FPS60_GROUP])


if __name__ == '__main__':
    unittest.main()
