# SPDX-License-Identifier: GPL-2.0-or-later
"""Exercise run.main routing with preparation and the game process stubbed."""
from paths import ROOT
from pathlib import Path
import contextlib
import io
import os
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
import run
import frame_timing as timing
import motion_blur as blur
import shadow_resolution as shadows
import internal_resolution as resolution


class VisualLaunchTests(unittest.TestCase):
    def test_prepared_rejected_and_original_clear_inherited_state(self):
        stale = [timing.FPS60_GROUP, blur.BLUR_OFF_GROUP, *shadows.GROUPS.values(), *resolution.GROUPS.values()]
        for enabled, accepted in ((True, True), (True, False), (False, False)):
            with self.subTest(enabled=enabled, accepted=accepted), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                game = root/'game'
                game.mkdir()
                (game/'eboot.bin').touch()
                probe = root/'probe'
                probe.touch()
                (root/'ratchet.ini').write_text('game_fps=60\nmotion_blur=off\nshadow_resolution=512\ninternal_resolution=4K\n' if enabled else
                                                'game_fps=30\nmotion_blur=original\nshadow_resolution=original\ninternal_resolution=original\n')
                env = {'RATCHET_DATA_DIR': str(root), 'RATCHET_GAME_DIR': str(game), 'RATCHET_PROBE': str(probe),
                       'RATCHET_PATCHES': ';'.join(stale), 'RATCHET_DISCORD': '0', 'RATCHET_ISA_REWRITE': '0',
                       'RATCHET_FPS_LIMIT': '60', 'RATCHET_ENGINE_FPS': '60', 'RATCHET_MOTION_BLUR': 'off',
                       'RATCHET_SHADOW_RESOLUTION': '256', 'RATCHET_INTERNAL_RESOLUTION': '720p',
                       'RATCHET_DERIVED': 'RATCHET_FPS_LIMIT,RATCHET_ENGINE_FPS,RATCHET_MOTION_BLUR,RATCHET_SHADOW_RESOLUTION,RATCHET_INTERNAL_RESOLUTION'}
                requested = [timing.FPS60_GROUP, blur.BLUR_OFF_GROUP, shadows.GROUPS['512'], resolution.GROUPS['4K']] if enabled else []
                captured = {}
                def popen(*args, **kwargs):
                    captured.update(os.environ)
                    return types.SimpleNamespace(wait=lambda: 7, pid=123)
                def script(name, *args, **kwargs):
                    return str(game) if name == 'mods.py' else None
                cwd = Path.cwd()
                try:
                    with patch.dict(os.environ, env, clear=True), patch.object(run, 'PORT', ROOT), \
                            patch.object(run, 'WINDOWS', False), patch.object(sys, 'argv', ['run.py']), \
                            patch.object(run, 'run_script', side_effect=script), patch('ratchet_game.validate_game'), \
                            patch('ratchet_patches.prepare', return_value={'prepared': requested if accepted else []}) as prepare, \
                            patch('ratchet_patches.finish'), patch('discord_presence.Presence', return_value=None), \
                            patch.object(run.subprocess, 'run', return_value=types.SimpleNamespace(stdout='CPU: complete', returncode=0)), \
                            patch.object(run.subprocess, 'Popen', side_effect=popen), contextlib.redirect_stdout(io.StringIO()):
                        self.assertEqual(run.main(), 7)
                        self.assertEqual(prepare.call_args.args[2], requested)
                        self.assertEqual(captured['RATCHET_ENGINE_FPS'], '60' if accepted else '30')
                        self.assertEqual(captured['RATCHET_FPS_LIMIT'], '60' if accepted else '30')
                        self.assertEqual(captured['RATCHET_VBLANK_HZ'], '60')
                        self.assertEqual(captured['RATCHET_MOTION_BLUR'], 'off' if accepted else 'original')
                        self.assertEqual(captured['RATCHET_SHADOW_RESOLUTION'], '512' if accepted else 'original')
                        self.assertEqual(captured['RATCHET_INTERNAL_RESOLUTION'], '4K' if accepted else 'original')
                        self.assertIn('RATCHET_INTERNAL_RESOLUTION', captured['RATCHET_DERIVED'].split(','))
                        self.assertIn('RATCHET_SHADOW_RESOLUTION', captured['RATCHET_DERIVED'].split(','))
                finally:
                    os.chdir(cwd)


if __name__ == '__main__':
    unittest.main()
