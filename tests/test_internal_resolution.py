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
            env = resolution.launch_environment({'prepared': names})
            self.assertEqual(env['RATCHET_INTERNAL_RESOLUTION'], mode)
            self.assertEqual('RATCHET_RESOLUTION_DMEM_MB' in env, mode in ('1440p', '4K'))
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

    def test_high_resolution_heap_and_backing_pool_are_coupled(self):
        for mode, heap, pool in (('1440p', 1549, 5440), ('4K', 1933, 5824)):
            report = {'prepared': [resolution.GROUPS[mode]]}
            self.assertEqual(resolution.launch_environment(report)['RATCHET_RESOLUTION_DMEM_MB'], str(pool))
            for invalid in (None, '', 'junk', '-1', '16385', '5000'):
                self.assertEqual(resolution.launch_environment(report, invalid)['RATCHET_RESOLUTION_DMEM_MB'], str(pool))
            self.assertEqual(resolution.launch_environment(report, '8192')['RATCHET_RESOLUTION_DMEM_MB'], '8192')
            self.assertEqual(resolution.launch_environment(report, '5056')['RATCHET_RESOLUTION_DMEM_MB'], str(pool))
            sites = resolution.writes(mode)
            self.assertEqual(len(sites), 3)
            self.assertEqual(sites[1]['elf_vaddr'], 0x1908724)
            self.assertEqual(bytes.fromhex(sites[1]['replacement_hex']), b'\xb8' + (heap << 20).to_bytes(4, 'little'))
            call = bytes.fromhex(sites[2]['replacement_hex'])
            self.assertEqual(call[0], 0xe8)
            self.assertEqual(sites[2]['elf_vaddr'] + 5 + int.from_bytes(call[1:], 'little', signed=True), 0x2c88338)
            self.assertLess(heap, 2048)  # stay within the original 2 GiB native address slot
        for mode in ('720p', '900p', '1080p'):
            self.assertEqual(len(resolution.writes(mode)), 1)
            self.assertNotIn('RATCHET_RESOLUTION_DMEM_MB', resolution.launch_environment({'prepared': [resolution.GROUPS[mode]]}))
        # Failed/ambiguous preparation cannot request the enlarged pool.
        for report in ({}, {'requested': [resolution.GROUPS['4K']]},
                       {'prepared': list(resolution.GROUPS.values())}):
            self.assertNotIn('RATCHET_RESOLUTION_DMEM_MB', resolution.launch_environment(report, '8192'))

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
