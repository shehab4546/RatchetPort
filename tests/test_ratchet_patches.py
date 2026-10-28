# SPDX-License-Identifier: GPL-2.0-or-later
"""Synthetic patch mechanics, never a substitute for real-game feature tests."""
from paths import ROOT
from copy import deepcopy
import json
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import ratchet_patches as rp
from ratchet_binary_audit import Binary
from test_prepare import fixture
from test_ratchet_binary_audit import sfo_bytes


def profile(binary):
    return dict(rp.PROFILE, source_sha256=rp.digest(binary.source).hex(),
                elf_sha256=rp.digest(binary.elf).hex(), groups={'synthetic': {'writes': [
                    {'signature': '02 03 ?? 05 06 07', 'offset': 2, 'elf_vaddr': 4,
                     'original_hex': '04 05', 'replacement_hex': '90 91'}]}})


def linked(image, relocs=()):
    return (struct.pack('<8s6Q', b'G3PROBE5', len(image), 0, 1, len(relocs), 0, 1) +
            bytes(40) + struct.pack('<QQ3Q', 0, 0, 0, len(image), 5) +
            b''.join(struct.pack('<4Q', a, 0, 0, 0) for a in relocs) + image)


class CompileTests(unittest.TestCase):
    def setUp(self):
        self.binary = Binary(bytes(fixture()))
        self.image = bytes(range(16)) + bytes(16)
        self.profile = profile(self.binary)
        self.site = self.profile['groups']['synthetic']['writes'][0]
        self.segments = [(0, 32, 5)]
        self.forbidden = []

    def result(self, names=('synthetic',)):
        return rp.compile_groups(self.binary, self.image, self.segments, self.forbidden, names, self.profile)

    def reject(self, reason):
        writes, prepared, skipped = self.result()
        self.assertEqual((writes, prepared), ([], []))
        self.assertIn(reason, skipped['synthetic'])

    def test_valid_group_and_duplicate_selection(self):
        writes, prepared, skipped = self.result(['synthetic', 'synthetic'])
        self.assertEqual(writes, [(4, b'\x04\x05', b'\x90\x91')])
        self.assertEqual(prepared, ['synthetic'])
        self.assertEqual(skipped, {})

    def test_source_and_elf_hash_required(self):
        for key in ('source_sha256', 'elf_sha256'):
            with self.subTest(key=key):
                self.profile = profile(self.binary)
                self.profile[key] = '0' * 64
                self.reject('fingerprint mismatch')

    def test_other_title_or_version_profile_rejected(self):
        for key, value in (('title_id', 'CUSA00000'), ('app_version', '01.01')):
            with self.subTest(key=key):
                self.profile = profile(self.binary)
                self.profile[key] = value
                self.reject('CUSA01047')

    def test_missing_signature(self):
        self.site['signature'] = 'ab cd ef'
        self.reject('signature absent')

    def test_duplicate_signature(self):
        source = bytearray(fixture())
        source[0x20a:0x20c] = b'\x02\x03'
        self.binary = Binary(bytes(source))
        self.profile.update(source_sha256=rp.digest(self.binary.source).hex(),
                            elf_sha256=rp.digest(self.binary.elf).hex())
        self.site['signature'] = '02 03'
        self.reject('not unique')

    def test_original_mismatch(self):
        self.site['original_hex'] = '44 55'
        self.reject('original bytes differ')

    def test_linker_changed_original(self):
        self.image = self.image[:4] + b'\x44' + self.image[5:]
        self.reject('linking changed')

    def test_segment_boundary(self):
        self.segments = [(0, 5, 5), (5, 27, 5)]
        self.reject('outside linked segments')

    def test_signature_must_cover_write_and_exact_address(self):
        for changes in ({'elf_vaddr': 8}, {'original_hex': '04 05 06 07 08', 'replacement_hex': '90 90 90 90 90'}):
            with self.subTest(changes=changes):
                self.profile = profile(self.binary)
                self.profile['groups']['synthetic']['writes'][0].update(changes)
                self.reject('guard range mismatch')

    def test_negative_offset(self):
        self.site['offset'] = -1
        self.reject('nonnegative integer')

    def test_relocation_isa_or_tcb_overlap_reserves_full_signature(self):
        self.forbidden = [(6, 1)]  # outside edited bytes, inside signature
        self.reject('overlaps relocation or ISA')

    def test_whole_group_rejected_when_second_write_invalid(self):
        second = dict(self.site, signature='ab cd ef')
        self.profile['groups']['synthetic']['writes'].append(second)
        self.reject('signature absent')

    def test_internal_overlap(self):
        self.profile['groups']['synthetic']['writes'].append(dict(self.site))
        self.reject('overlapping writes within group')

    def test_two_conflicting_groups_both_rejected_independent_survives(self):
        self.profile['groups']['conflict'] = deepcopy(self.profile['groups']['synthetic'])
        self.profile['groups']['independent'] = {'writes': [dict(self.site, signature='0a 0b 0c 0d', offset=0,
                                                               elf_vaddr=10, original_hex='0a 0b')]}
        writes, prepared, skipped = self.result(['synthetic', 'conflict', 'independent'])
        self.assertEqual(prepared, ['independent'])
        self.assertEqual(writes[0][0], 10)
        self.assertEqual(set(skipped), {'synthetic', 'conflict'})

    def test_no_external_or_unreviewed_names(self):
        writes, prepared, skipped = self.result(['other-game/60FPS'])
        self.assertFalse(writes or prepared)
        self.assertIn('no reviewed', skipped['other-game/60FPS'])
        self.assertEqual(set(rp.PROFILE['groups']), {rp.FPS60_GROUP, rp.BLUR_OFF_GROUP, *rp.SHADOW_GROUPS, *rp.RESOLUTION_GROUPS, *rp.LANGUAGE_GROUPS})

    def test_length_change_and_noop_rejected(self):
        for replacement in ('90', '04 05'):
            self.site['replacement_hex'] = replacement
            self.reject('without changing length')

    def test_bss_is_not_a_source_write(self):
        # A signature matches file bytes, but a write cannot escape into zero-filled BSS.
        with self.assertRaises(ValueError):
            self.binary.check_bytes(16, b'\0')

    def test_linked_parser_reserves_relocations(self):
        self.assertEqual(rp.read_linked(linked(self.image, [4])), (self.image, self.segments, [(4, 8)]))
        for data in (linked(self.image)[:-1], linked(self.image) + b'x', linked(self.image, [31])):
            with self.assertRaises(ValueError):
                rp.read_linked(data)

    def test_isa_relocated_instruction_reserved(self):
        # Actual G3ISA1 offsets: relocated_length is byte 47, not 48.
        header = struct.pack('<8sQ32sII8x', b'G3ISA1\0\0', 32, rp.digest(self.image), 1, 0)
        record = bytearray(64)
        struct.pack_into('<Q', record, 0, 4)
        record[8], record[11], record[47] = 4, 1, 3
        self.assertEqual(rp.isa_ranges(header + record, self.image), [(4, 7)])
        record[47] = 255
        with self.assertRaises(ValueError):
            rp.isa_ranges(header + record, self.image)


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = self.enterContext(tempfile.TemporaryDirectory())
        self.root = Path(self.tmp)
        self.out, self.game = self.root / 'out', self.root / 'game'
        (self.game / 'sce_sys').mkdir(parents=True)
        (self.game / 'eboot.bin').write_bytes(fixture())
        (self.game / 'sce_sys/param.sfo').write_bytes(sfo_bytes())
        self.binary = Binary(bytes(fixture()))
        self.image = bytes(range(16)) + bytes(16)
        self.out.mkdir()
        (self.out / 'boot-linked.bin').write_bytes(linked(self.image))
        self.enterContext(patch.dict(rp.PROFILE, profile(self.binary)))

    def receipt(self, report):
        (self.out / 'patch_receipt.bin').write_bytes(struct.pack('<8s16sQ', b'RCPACK3\0',
            bytes.fromhex(report['transaction']), report['write_count']))

    def test_prepare_is_not_applied_until_matching_loader_receipt(self):
        report = rp.prepare(self.game, self.out, ['synthetic'])
        self.assertEqual(rp.status(self.out)['applied'], [])
        self.assertEqual(report['phase'], 'prepared')
        self.receipt(dict(report, transaction='00' * 16))
        self.assertEqual(rp.status(self.out)['applied'], [])
        self.receipt(dict(report, write_count=2))
        self.assertEqual(rp.status(self.out)['applied'], [])
        self.receipt(report)
        self.assertEqual(rp.status(self.out)['applied'], ['synthetic'])
        rp.finish(self.out, 17)
        self.assertEqual(rp.status(self.out)['process_returncode'], 17)
        (self.out / 'patch_receipt.bin').unlink()
        self.assertNotEqual(rp.status(self.out)['phase'], 'loader_confirmed')
        self.assertEqual(rp.status(self.out)['applied'], [])

    def test_disable_clears_packet_and_receipt_preserves_source_and_linked(self):
        paths = [self.game / 'eboot.bin', self.game / 'sce_sys/param.sfo', self.out / 'boot-linked.bin']
        before = [p.read_bytes() for p in paths]
        self.receipt(rp.prepare(self.game, self.out, ['synthetic']))
        report = rp.prepare(self.game, self.out, [])
        self.assertEqual(report['phase'], 'disabled')
        self.assertFalse((self.out / 'patch_receipt.bin').exists())
        data = (self.out / 'patches.bin').read_bytes()
        self.assertEqual(len(data), 72)
        self.assertEqual(rp.HEADER.unpack(data)[-1], 0)
        self.assertEqual(before, [p.read_bytes() for p in paths])

    def test_failure_invalidates_old_packet(self):
        self.receipt(rp.prepare(self.game, self.out, ['synthetic']))
        (self.game / 'sce_sys/param.sfo').write_bytes(sfo_bytes('01.01'))
        report = rp.prepare(self.game, self.out, ['synthetic'])
        self.assertEqual(report['phase'], 'rejected')
        self.assertEqual((self.out / 'patches.bin').stat().st_size, 72)
        self.assertEqual(rp.status(self.out)['applied'], [])

    def test_loader_failure_reports_unconfirmed(self):
        rp.prepare(self.game, self.out, ['synthetic'])
        rp.finish(self.out, 1)
        report = rp.status(self.out)
        self.assertEqual(report['applied'], [])
        self.assertEqual(report['phase'], 'loader_unconfirmed')
        self.assertIn('loader did not confirm', report['skipped']['synthetic'])

    def test_output_cannot_modify_dump(self):
        with self.assertRaisesRegex(ValueError, 'outside the original'):
            rp.prepare(self.game, self.game / 'out', ['synthetic'])
        self.assertFalse((self.game / 'out').exists())

    def test_invalid_status_or_legacy_cannot_claim_applied(self):
        for report in ('broken JSON', '[]', 'null', '{"applied":["fps"]}'):
            (self.out / 'patch_status.json').write_text(report)
            self.assertEqual(rp.status(self.out)['applied'], [])

    @unittest.skipUnless(os.environ.get('RATCHET_PATCH_TEST'), 'native transport harness not configured')
    def test_native_loader_confirms_python_transaction_and_disabled_restart(self):
        exe = os.environ['RATCHET_PATCH_TEST']
        report = rp.prepare(self.game, self.out, ['synthetic'])
        imagefile, resultfile = self.root / 'image.bin', self.root / 'result.bin'
        imagefile.write_bytes(self.image)
        command = [exe, str(imagefile), str(self.out / 'patches.bin'), str(self.out / 'patch_receipt.bin'), str(resultfile)]
        subprocess.run(command, check=True)
        self.assertEqual(resultfile.read_bytes(), self.image[:4] + b'\x90\x91' + self.image[6:])
        self.assertEqual(rp.status(self.out)['applied'], ['synthetic'])
        rp.prepare(self.game, self.out, [])
        subprocess.run(command, check=True)
        self.assertEqual(resultfile.read_bytes(), self.image)
        self.assertEqual(rp.status(self.out)['applied'], [])
        self.assertEqual(imagefile.read_bytes(), self.image)


if __name__ == '__main__':
    unittest.main()
