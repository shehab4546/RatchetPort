"""Version isolation, update preflight and read-only launch lifecycle with synthetic files."""
from paths import ROOT
import contextlib
import hashlib
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

import game_update
import ratchet_game as game
import ratchet_patches as patches
import voice_archive
from test_launcher_controls import launcher, sfo_bytes
from playgo_fixture import playgo_bytes
from test_prepare import fixture
from test_ratchet_patches import linked, profile
from ratchet_binary_audit import Binary


class UpdateCompatibility(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.base, self.update, self.out = (self.root / x for x in ('base', 'update', 'out'))
        self.old = bytes(fixture())
        newer = bytearray(self.old)
        newer[0x208] ^= 1
        self.new = bytes(newer)
        for folder, version, executable in ((self.base, '01.00', self.old),
                                             (self.update, '01.09', self.new)):
            self.write(folder / 'eboot.bin', executable)
            self.write(folder / 'sce_sys/param.sfo', sfo_bytes(TITLE_ID='CUSA01047',
                       APP_VER=version, VERSION='01.00', CATEGORY='gp' if version == '01.09' else 'gd'))
            self.write(folder / game.PLAYGO_PATH, playgo_bytes())
            for name in ('libc.prx', 'libSceFios2.prx'):
                self.write(folder / 'sce_module' / name, version.encode())
        self.write(self.base / 'asset_archive/g00s000', b'base archive')
        self.write(self.base / 'asset_archive/toc', b'base toc')
        self.write(self.update / 'asset_archive/toc', b'update toc')
        self.write(self.update / 'sce_module/libSceNpToolkit.prx', b'update toolkit')
        self.enterContext(mock.patch.object(game, 'UPDATE_TOOLKIT_SHA256',
                                            hashlib.sha256(b'update toolkit').hexdigest()))
        for name in game.UPDATE_ARCHIVES:
            self.write(self.update / name, b'patch archive')
        self.enterContext(mock.patch.object(game, 'UPDATE_TOC_SHA256',
                                            hashlib.sha256(b'update toc').hexdigest()))
        self.enterContext(mock.patch.dict(game.BUILD_FINGERPRINTS, {
            ('CUSA01047', '01.09'): (hashlib.sha256(self.new).hexdigest(),
                                    hashlib.sha256(Binary(self.new).elf).hexdigest())}))

    def write(self, path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def snapshot(self):
        return {str(p.relative_to(self.root)): hashlib.sha256(p.read_bytes()).hexdigest()
                for folder in (self.base, self.update) for p in folder.rglob('*') if p.is_file()}

    def test_select_update_and_return_to_base_without_changing_files(self):
        before = self.snapshot()
        for update, version in (('', '01.00'), (self.update, '01.09'), ('', '01.00')):
            with game_update.selected_view(self.base, update, self.out) as (view, values):
                self.assertEqual(values['APP_VER'], version)
                self.assertEqual(game.validate_game(view)['APP_VER'], version)
                self.assertEqual((view / 'sce_module/libc.prx').read_bytes(), version.encode())
                self.assertEqual((view / 'asset_archive/g00s000').read_bytes(), b'base archive')
                if update:
                    self.assertEqual((view / 'asset_archive/toc').read_bytes(), b'update toc')
            if update:
                self.assertFalse(view.exists())
        self.assertEqual(before, self.snapshot())

    def test_update_only_is_not_a_complete_game(self):
        with self.assertRaisesRegex(ValueError, 'g00s000'):
            game.validate_game(self.update)
        self.assertFalse(launcher.ready_to_play(self.update))

    def test_toolkit_is_required_only_for_the_reviewed_update(self):
        base = game.validate_game(self.base)
        update = game.validate_selection(self.base, self.update)
        self.assertEqual(game.linked_modules(base), ('libc.prx', 'libSceFios2.prx'))
        self.assertEqual(game.linked_modules(update),
                         ('libc.prx', 'libSceFios2.prx', 'libSceNpToolkit.prx'))
        path = self.update / 'sce_module/libSceNpToolkit.prx'
        for content in (b'wrong toolkit', b'', None):
            if content is None:
                path.unlink()
            else:
                path.write_bytes(content)
            with self.assertRaisesRegex(ValueError, 'Toolkit'):
                game.validate_selection(self.base, self.update)
            self.assertFalse(launcher.ready_to_play(self.base, self.update))
            self.assertEqual(game.validate_game(self.base)['APP_VER'], '01.00')
        with self.assertRaisesRegex(ValueError, 'Unreviewed'):
            game.linked_modules({'TITLE_ID': 'CUSA01047', 'APP_VER': '01.08'})

    def test_spoofed_metadata_and_changed_executable_are_rejected(self):
        for content in (self.old, self.new + b'changed'):
            (self.update / 'eboot.bin').write_bytes(content)
            with self.assertRaisesRegex(ValueError, 'fingerprint'):
                game.validate_selection(self.base, self.update)
            self.assertFalse(launcher.ready_to_play(self.base, self.update))

    def test_wrong_region_version_and_category_are_rejected(self):
        for title, version, category in (('CUSA01073', '01.09', 'gp'),
                ('CUSA01047', '01.08', 'gp'), ('CUSA01047', '01.00', 'gd'),
                ('CUSA01047', '01.09', 'gd')):
            (self.update / 'sce_sys/param.sfo').write_bytes(
                sfo_bytes(TITLE_ID=title, APP_VER=version, CATEGORY=category))
            with self.assertRaises(ValueError):
                game.validate_selection(self.base, self.update)

    def test_missing_update_archive_does_not_create_a_view(self):
        (self.update / game.UPDATE_ARCHIVES[-1]).unlink()
        with self.assertRaisesRegex(ValueError, 'p000048'):
            with game_update.selected_view(self.base, self.update, self.out):
                self.fail('must reject before creating the view')
        self.assertFalse(self.out.exists())

    def test_base_toc_cannot_be_combined_with_update_executable(self):
        (self.update / 'asset_archive/toc').write_bytes(b'base toc')
        with self.assertRaisesRegex(ValueError, 'TOC fingerprint'):
            game.validate_selection(self.base, self.update)

    def test_output_cannot_be_inside_either_dump(self):
        before = self.snapshot()
        for folder in (self.base, self.update):
            with self.assertRaisesRegex(ValueError, 'outside both'):
                game_update.create_view(self.base, self.update, folder / 'out')
            self.assertFalse((folder / 'out').exists())
        self.assertEqual(before, self.snapshot())

    def test_runner_rejects_update_output_before_resetting_patch_files(self):
        import run
        before = self.snapshot()
        self.addCleanup(os.chdir, os.getcwd())
        with mock.patch.dict(os.environ, {'RATCHET_GAME_DIR': str(self.base),
                'RATCHET_PATCH_DIR': str(self.update), 'RATCHET_DATA_DIR': str(self.update)}, clear=True), \
                mock.patch.object(sys, 'argv', ['run.py']), \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                run.main()
        self.assertFalse((self.update / 'out').exists())
        self.assertEqual(before, self.snapshot())

    def test_context_cleans_up_on_preparation_failure(self):
        before = self.snapshot()
        with self.assertRaisesRegex(RuntimeError, 'preparation failed'):
            with game_update.selected_view(self.base, self.update, self.out) as (view, _):
                raise RuntimeError('preparation failed')
        self.assertFalse(view.exists())
        self.assertEqual(before, self.snapshot())

    def test_launcher_preserves_optional_selection_and_clears_stale_environment(self):
        settings = {**launcher.APP_DEFAULTS, 'game_dir': str(self.base), 'update_dir': str(self.update)}
        self.assertTrue(launcher.ready_to_play(self.base, self.update))
        self.assertEqual(launcher.game_environment(settings)['RATCHET_PATCH_DIR'], str(self.update))
        with mock.patch.dict(os.environ, {'RATCHET_PATCH_DIR': str(self.update)}):
            self.assertNotIn('RATCHET_PATCH_DIR', launcher.game_environment(dict(settings, update_dir='')))

    def test_voice_check_uses_update_file_or_inherits_base(self):
        relative = 'asset_archive/a00s007.fr'
        self.write(self.base / relative, b'RIFF0000WAVE' + bytes(2048))
        self.assertEqual(voice_archive.inspect(self.base, '2', self.update)['integrity'], 'OK')
        self.write(self.update / relative, b'')
        self.assertEqual(voice_archive.inspect(self.base, '2', self.update)['size'], 0)
        self.assertEqual(voice_archive.inspect(self.base, '2', self.update)['integrity'], 'WARNING')

    def test_patch_dispatch_and_receipts_do_not_cross_versions(self):
        old_profile, new_profile = profile(Binary(self.old)), profile(Binary(self.new))
        new_profile['app_version'] = '01.09'
        new_profile['groups']['synthetic']['writes'][0].update(
            signature='0a 0b 0c 0d', offset=0, elf_vaddr=10, original_hex='0a 0b')
        with mock.patch.dict(patches.PROFILES, {('CUSA01047', '01.00'): old_profile,
                                               ('CUSA01047', '01.09'): new_profile}):
            previous = None
            for folder, version, address in ((self.base, '01.00', 4), (self.update, '01.09', 10),
                                              (self.base, '01.00', 4)):
                image = bytearray(range(16)) + bytes(16)
                if version == '01.09':
                    image[8] ^= 1
                self.write(self.out / 'boot-linked.bin', linked(bytes(image)))
                report = patches.prepare(folder, self.out, ['synthetic'])
                self.assertEqual(report['app_version'], version)
                self.assertEqual(report['prepared'], ['synthetic'])
                self.assertNotEqual(report['transaction'], previous)
                self.assertFalse((self.out / 'patch_receipt.bin').exists())
                packet = (self.out / 'patches.bin').read_bytes()
                self.assertEqual(int.from_bytes(packet[72:80], 'little'), address)
                previous = report['transaction']
                self.write(self.out / 'patch_receipt.bin', b'old receipt')
            # Declaring update metadata around the old binary never picks the old profile.
            (self.update / 'eboot.bin').write_bytes(self.old)
            report = patches.prepare(self.update, self.out, ['synthetic'])
            self.assertEqual(report['prepared'], [])
            self.assertIn('fingerprint mismatch', report['skipped']['synthetic'])
            self.assertEqual((self.out / 'patches.bin').stat().st_size, 72)

    def test_update_features_have_independent_graphics_sites(self):
        selected = patches.select_profile({'TITLE_ID': 'CUSA01047', 'APP_VER': '01.09'})
        self.assertNotIn(patches.FPS60_GROUP, selected['groups'])
        self.assertIn(patches.FPS60_GROUP, patches.PROFILE['groups'])
        self.assertNotIn(patches.BLUR_OFF_GROUP, selected['groups'])
        self.assertEqual(set(selected['groups']), set(patches.LANGUAGE_GROUPS) |
                         set(patches.RESOLUTION_GROUPS) | set(patches.SHADOW_GROUPS))
        for name in patches.RESOLUTION_GROUPS.keys() | patches.SHADOW_GROUPS.keys():
            old = {w['elf_vaddr'] for w in patches.PROFILE['groups'][name]['writes']}
            new = {w['elf_vaddr'] for w in selected['groups'][name]['writes']}
            self.assertTrue(old.isdisjoint(new))

    def test_run_mounts_update_under_mods_and_cleans_both_views(self):
        import run
        import mods
        for fail_preparation in (False, True):
            with self.subTest(fail_preparation=fail_preparation), contextlib.ExitStack() as stack:
                before = self.snapshot()
                probe = self.root / 'probe'
                probe.write_bytes(b'not executed')
                mod = self.root / 'mod'
                self.write(mod / 'asset_archive/g00s000', b'mod archive')
                views = []
                def script(name, folder, *args, **kwargs):
                    if name == 'mods.py':
                        views.append(Path(folder))
                        view = mods.build_overlay(folder, self.out, [('test', mod)])
                        views.append(view)
                        return str(view)
                    if name == 'link_modules.py':
                        self.assertEqual(args[args.index('--modules') + 1:],
                            ('libc.prx', 'libSceFios2.prx', 'libSceNpToolkit.prx'))
                        self.assertEqual((Path(folder) / 'sce_module/libSceNpToolkit.prx').read_bytes(),
                                         b'update toolkit')
                        if fail_preparation:
                            raise RuntimeError('link failed')
                    return ''
                def wait():
                    command = start.call_args.args[0]
                    mounted = Path(command[command.index('--app0') + 1])
                    self.assertEqual(mounted, views[-1])
                    self.assertEqual((mounted / 'eboot.bin').read_bytes(), self.new)
                    self.assertEqual((mounted / 'asset_archive/g00s000').read_bytes(), b'mod archive')
                    self.assertEqual(os.environ['RATCHET_GAME_DIR'], str(self.base))
                    self.assertEqual(os.environ['RATCHET_PATCH_DIR'], str(self.update))
                    return 7
                stack.enter_context(mock.patch.dict(os.environ, {
                    'RATCHET_GAME_DIR': str(self.base), 'RATCHET_PATCH_DIR': str(self.update),
                    'RATCHET_DATA_DIR': str(self.root), 'RATCHET_PROBE': str(probe),
                    'RATCHET_GLYPH_STYLE': 'keyboard', 'RATCHET_ISA_REWRITE': '0',
                    'RATCHET_DISCORD': '0'}, clear=True))
                stack.callback(os.chdir, os.getcwd())
                stack.enter_context(mock.patch.object(run, 'PORT', ROOT))
                stack.enter_context(mock.patch.object(sys, 'argv', ['run.py']))
                stack.enter_context(mock.patch.object(run, 'run_script', side_effect=script))
                stack.enter_context(mock.patch.object(run.subprocess, 'run',
                    return_value=mock.Mock(returncode=0, stdout='CPU: complete\n')))
                start = stack.enter_context(mock.patch.object(run.subprocess, 'Popen',
                    return_value=mock.Mock(pid=123, wait=mock.Mock(side_effect=wait))))
                stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
                if fail_preparation:
                    with self.assertRaisesRegex(RuntimeError, 'link failed'):
                        run.main()
                    start.assert_not_called()
                else:
                    self.assertEqual(run.main(), 7)
                self.assertTrue(views)
                self.assertTrue(all(not p.exists() for p in views))
                self.assertEqual(before, self.snapshot())
