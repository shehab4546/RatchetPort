# SPDX-License-Identifier: GPL-2.0-or-later
"""Supported editions: USA stays the reviewed baseline; Europe adds its own data and fixes."""
import struct
import sys
import tempfile
import unittest
from pathlib import Path

from paths import ROOT
import editions
import edition_compat
import frame_timing
import language_split as split
import motion_blur
import ratchet_patches
import voice_archive
from ratchet_binary_audit import original, pattern
from ratchet_game import validate_identity

try:
    import iced_x86  # noqa: F401
except ImportError:
    iced_x86 = None


class Identity(unittest.TestCase):
    def test_both_editions_version_100_only(self):
        for title in (editions.USA, editions.EUROPE):
            validate_identity({'TITLE_ID': title, 'APP_VER': '01.00'})
        for values in ({'TITLE_ID': 'CUSA01073', 'APP_VER': '01.07'}, {'TITLE_ID': 'CUSA00001', 'APP_VER': '01.00'}):
            with self.assertRaises(ValueError):
                validate_identity(values)

    def test_profiles_follow_editions(self):
        for title, profile in ratchet_patches.PROFILES.items():
            record = editions.EDITIONS[title]
            self.assertEqual(profile['source_sha256'], record['source_sha256'])
            self.assertEqual(profile['elf_sha256'], record['elf_sha256'])
        self.assertIs(ratchet_patches.PROFILES[editions.USA], ratchet_patches.PROFILE)
        self.assertEqual(sorted(ratchet_patches.PROFILE_EUROPE['groups']),
                         sorted([frame_timing.FPS60_GROUP, motion_blur.BLUR_OFF_GROUP]))


class Languages(unittest.TestCase):
    def test_usa_behaviour_is_unchanged(self):
        self.assertIs(voice_archive.LANGUAGES, editions.USA_LANGUAGES)
        self.assertEqual(split.normalize('19'), '1')
        self.assertEqual(split.normalize('22'), '2')
        self.assertEqual(editions.normalize_language('22'), '2')
        self.assertEqual(editions.normalize_language('3'), '1')

    def test_europe_languages_and_no_text_split(self):
        self.assertEqual(split.normalize('3', editions.EUROPE), '3')
        self.assertEqual(split.normalize('20', editions.EUROPE), '1')   # Latin American is USA-only
        self.assertEqual(split.requested_groups('3', '4', ['Other'], editions.EUROPE), ['Other'])
        env = split.launch_environment('3', '4', {'prepared': list(split.GROUPS.values())}, editions.EUROPE)
        self.assertEqual(env, {'RATCHET_LANGUAGE': '3', 'RATCHET_LANGUAGE_SPLIT': '0'})

    def test_voice_archive_uses_the_edition_table(self):
        with tempfile.TemporaryDirectory() as folder:
            report = voice_archive.inspect(folder, '3', editions.EUROPE)
            self.assertEqual((report['language'], report['archive']), ('Spanish Spain', 'asset_archive/a00s015.es'))
            report = voice_archive.inspect(folder, '3', editions.USA)
            self.assertEqual(report['archive'], 'asset_archive/a00s003.us')

    def test_launcher_lists_match_editions(self):
        sys.path.insert(0, str(ROOT / 'launcher'))
        import ratchetport_launcher_win as launcher
        for title, labels in launcher.EDITION_LANGUAGES.items():
            self.assertEqual(sorted(v for v, _ in labels), sorted(editions.languages(title)))
        self.assertEqual(launcher.game_language_id('3', launcher.LANGUAGES_EUROPE), '3')
        self.assertEqual(launcher.game_language_id('3'), '1')
        self.assertEqual(launcher.game_language_id('22'), '22')


class EuropeFrameTiming(unittest.TestCase):
    def test_writes_are_well_formed(self):
        for site in frame_timing.FPS60_WRITES_EUROPE + motion_blur.BLUR_OFF_WRITES_EUROPE:
            sig = pattern(site['signature'])
            before, after = original(site['original_hex']), original(site['replacement_hex'])
            self.assertEqual(len(before), len(after))
            self.assertNotEqual(before, after)
            self.assertLessEqual(site['offset'] + len(before), len(sig))
            self.assertEqual(bytes(sig[site['offset']:site['offset'] + len(before)]), before)

    def test_interval_replacement_stores_one(self):
        after = original(frame_timing.FPS60_WRITES_EUROPE[0]['replacement_hex'])
        self.assertIn(bytes.fromhex('41c7461c') + struct.pack('<f', 1.0), after)
        self.assertIn(bytes.fromhex('41c6462401'), after)          # throttle flag unchanged


SYNTHETIC_LEAF = bytes.fromhex(
    '55 4157 4156 4155 4154 53'            # push rbp, r15, r14, r13, r12, rbx
    '48894424f8'                           # mov [rsp-8], rax
    '488b4c24f8'                           # mov rcx, [rsp-8]
    '5b 415c 415d 415e 415f 5d c3')        # pops, ret


@unittest.skipIf(iced_x86 is None, 'iced_x86 not installed')
class EuropeCompat(unittest.TestCase):
    def test_usa_and_unknown_dumps_get_no_compat(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertIsNone(edition_compat.compat_for(folder))

    def test_red_zone_locals_move_into_a_frame(self):
        image = bytearray(SYNTHETIC_LEAF)
        plan = edition_compat.redzone_plan(image, 0, len(image))
        (p_at, p_len), frame, fixes, (e_at, e_len) = plan
        self.assertEqual((p_at, p_len, frame, e_len), (0, 10, 16, 11))
        self.assertEqual([disp for _, disp in fixes], [8, 8])

    def test_apply_redirects_and_binds_stubs(self):
        image, segments = bytearray(SYNTHETIC_LEAF), [(0, len(SYNTHETIC_LEAF), 5)]
        compat = edition_compat.Compat('test', {'libkernel': ('WslcK1FQcGI',)}, {}, [(0, len(SYNTHETIC_LEAF))], sse4a=False)
        with tempfile.TemporaryDirectory() as out:
            stubs, slots = compat.apply(image, segments, 0x10000, [(0, len(SYNTHETIC_LEAF))], out)
        self.assertEqual(slots, [])                                 # no Mount2 bridge requested
        self.assertEqual(image[0], 0xE9)                            # prologue jumps to the trampoline
        self.assertEqual(image[14], 0x08)                           # [rsp-8] -> [rsp+8]
        address = stubs[('libkernel', 'WslcK1FQcGI')]
        self.assertEqual(bytes(image[address:address + 3]), bytes.fromhex('31c0c3'))
        self.assertEqual(segments[-2:], [(0x10000, 0x1000, 6), (0x11000, 0x1000, 5)])

    def test_default_game_dir_finds_either_edition(self):
        with tempfile.TemporaryDirectory() as base:
            self.assertEqual(editions.default_game_dir(base), Path(base) / editions.USA)
            (Path(base) / editions.EUROPE).mkdir()
            (Path(base) / editions.EUROPE / 'eboot.bin').write_bytes(b'x')
            self.assertEqual(editions.default_game_dir(base), Path(base) / editions.EUROPE)

    def test_sse4a_trampoline_preserves_state(self):
        from iced_x86 import Decoder, Formatter, FormatterSyntax
        code = edition_compat.sse4a_trampoline(0x2000, (0x1000, 6, 'INSERTQ', 9, 12, 8, 16))
        text = [Formatter(FormatterSyntax.INTEL).format(i) for i in Decoder(64, code, ip=0x2000)]
        self.assertEqual(text[:5], ['lea rsp,[rsp-80h]', 'pushfq', 'push rax', 'push rcx', 'push rdx'])
        self.assertIn('pinsrq xmm9,rax,0', text)
        self.assertEqual(text[-1], 'jmp 0000000000001006h')

    def test_mount2_bridge_builds_mount1_and_calls_the_slot(self):
        from iced_x86 import Decoder, Formatter, FormatterSyntax
        code, names = edition_compat.guest_code(0x11000, 0x10000)
        start = names['savedata_mount2'] - 0x11000
        text = [Formatter(FormatterSyntax.INTEL).format(i)
                for i in Decoder(64, bytes(code[start:names['zero'] - 0x11000]), ip=names['savedata_mount2'])]
        self.assertEqual([text[0], text[2], text[3]], ['test rdi,rdi', 'sub rsp,58h', 'mov rax,rdi'])
        self.assertTrue(text[1].startswith('je '))
        self.assertIn('mov qword ptr [rsp+8],0', text)            # Mount1.title = NULL
        self.assertIn('mov rcx,[rax+8]', text)                     # Mount2.dir
        self.assertIn('mov [rsp+10h],rcx', text)                   # -> Mount1.dir
        self.assertIn('mov ecx,[rax+18h]', text)                   # Mount2.mode
        self.assertIn('call qword ptr [10300h]', text)             # data page slot
        self.assertEqual(text[-2:], ['mov eax,809F0000h', 'ret'])
        je_target = int(text[1].split()[-1].rstrip('h'), 16)        # 'je short 0000...h'
        self.assertEqual(je_target, names['zero'] - 6)              # jz lands on the parameter error

    def test_europe_aliases_and_slots(self):
        compat = edition_compat.EUROPE
        self.assertEqual(compat.aliases[('libSceSaveData', 'TywrFKCoLGY')], 'ZkZhskCPXFw#libSceSaveData')
        self.assertNotIn(('libSceSaveData', 'TywrFKCoLGY'), compat.stub_names())

    def test_europe_lists_are_explicit(self):
        names = edition_compat.EUROPE.stub_names()
        self.assertEqual(names[('libSceLibcInternalExt', 'NWtTN10cJzE')], 'heap_trace')
        self.assertNotIn(('libSceLibcInternal', '5bBacGLyLOs'), names)   # served by the game's own libc


if __name__ == '__main__':
    unittest.main()
