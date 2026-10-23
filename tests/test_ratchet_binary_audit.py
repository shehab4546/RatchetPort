# SPDX-License-Identifier: GPL-2.0-or-later
"""Synthetic bytes only: validate evidence mechanics, not Ratchet feature support."""
from paths import ROOT
from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import struct
import tempfile
import unittest

from prepare import parse_self
from ratchet_binary_audit import Binary, audit, digest, main, pattern, verify_candidates
from test_prepare import fixture


def evidence(binary):
    return {
        'schema_version': 1, 'title_id': 'CUSA01047', 'app_version': '01.00',
        'source_sha256': digest(binary.source), 'elf_sha256': digest(binary.elf),
        'sites': [{
            'id': 'synthetic-only', 'feature': 'fps',
            'signature': '02 03 ?? 05 06 07', 'offset_in_signature': 2,
            'elf_vaddr': '0x4', 'original_hex': '04 05',
            'consumer': {'elf_vaddr': '0x0', 'original_hex': '00 01'},
            'purpose': 'Synthetic fixture; not a real instruction or a game feature.',
            'initialization': 'Synthetic test only; no initialization proof.',
            'evidence_reference': 'tests/test_ratchet_binary_audit.py',
        }],
    }


def sfo_bytes(version='01.00'):
    fields = [('TITLE_ID', 'CUSA01047'), ('APP_VER', version)]
    keys, values, entries = b'', b'', []
    for key, value in fields:
        data = value.encode() + b'\0'
        entries.append(struct.pack('<HHIII', len(keys), 0x204, len(data), len(data), len(values)))
        keys += key.encode() + b'\0'
        values += data
    keys_offset = 20 + len(entries) * 16
    return (struct.pack('<4sIIII', b'\0PSF', 0x101, keys_offset, keys_offset + len(keys), len(entries)) +
            b''.join(entries) + keys + values)


class BinaryAuditTests(unittest.TestCase):
    def setUp(self):
        self.source = bytes(fixture())
        self.binary = Binary(self.source)
        self.manifest = evidence(self.binary)

    def result(self, **changes):
        self.manifest['sites'][0].update(changes)
        return verify_candidates(self.binary, self.manifest)[0]

    def test_self_elf_and_prelink_offsets_are_distinct(self):
        matched = self.result()
        self.assertEqual(matched['mechanical_status'], 'matched')
        self.assertEqual(matched['location'], {
            'segment_index': 0, 'elf_vaddr': 4, 'prelink_image_offset': 4,
            'elf_file_offset': 0x1004, 'source_file_offset': 0x204,
        })
        unpacked = Binary(bytes(self.binary.elf))
        self.assertEqual(unpacked.check_bytes(4, b'\x04\x05')['source_file_offset'], 0x1004)
        self.assertEqual(digest(unpacked.elf), digest(self.binary.elf))
        self.assertNotEqual(digest(unpacked.source), digest(self.source))

    def test_nonzero_vaddr_uses_segment_mapping(self):
        elf = bytearray(self.binary.elf)
        struct.pack_into('<Q', elf, 24, 0x2000)  # Entry.
        struct.pack_into('<Q', elf, 64 + 16, 0x2000)
        location = Binary(bytes(elf)).check_bytes(0x2004, b'\x04\x05')
        self.assertEqual(location['elf_file_offset'], 0x1004)
        self.assertEqual(location['prelink_image_offset'], 0x2004)

    def test_matching_is_never_semantic_approval(self):
        result = self.result()
        self.assertEqual(result['semantic_status'], 'review_required')
        self.assertEqual(result['runtime_status'], 'not_tested')

    def test_source_and_elf_hashes_must_both_match(self):
        for field in ('source_sha256', 'elf_sha256'):
            with self.subTest(field=field):
                bad = deepcopy(self.manifest)
                bad[field] = '0' * 64
                with self.assertRaisesRegex(ValueError, field):
                    verify_candidates(self.binary, bad)

    def test_other_game_or_version_rejected(self):
        for key, value in (('title_id', 'CUSA01073'), ('app_version', '01.09')):
            bad = deepcopy(self.manifest)
            bad[key] = value
            with self.assertRaisesRegex(ValueError, 'different title or version'):
                verify_candidates(self.binary, bad)

    def test_manifest_cannot_invent_a_missing_site(self):
        result = self.result(signature='fe ed fa ce')
        self.assertEqual(result['reason'], 'signature absent')

    def test_repeated_signature_rejected(self):
        source = bytearray(self.source)
        source[0x208:0x20e] = source[0x202:0x208]
        binary = Binary(bytes(source))
        result = verify_candidates(binary, evidence(binary))[0]
        self.assertEqual(result['reason'], 'signature is not unique')

    def test_wildcard_does_not_hide_wrong_original_bytes(self):
        result = self.result(original_hex='ff 05')
        self.assertEqual(result['reason'], 'original bytes differ')

    def test_address_from_other_coordinate_system_rejected(self):
        for address in (0x204, 0x1004, 0x400004):
            with self.subTest(address=address):
                self.assertEqual(self.result(elf_vaddr=address)['reason'], 'signature/address mismatch')

    def test_byte_range_must_stay_within_signature(self):
        self.assertIn('extends beyond', self.result(offset_in_signature=5)['reason'])

    def test_bss_and_cross_boundary_reads_rejected(self):
        for address, size in ((16, 1), (15, 2), (0, 0)):
            with self.assertRaises(ValueError):
                self.binary.locate(address, size)

    def test_scan_ignores_self_headers_and_bss(self):
        self.assertEqual(self.binary.matches(pattern('7f 45 4c 46')), [])
        self.assertEqual(self.binary.matches(pattern('00 00 00 00')), [])

    def test_consumer_must_be_in_executable_segment(self):
        elf = bytearray(self.binary.elf)
        # Add a second, non-executable segment and put consumer evidence there.
        struct.pack_into('<H', elf, 56, 2)
        struct.pack_into('<IIQQQQQQ', elf, 120, 1, 6, 0x1020, 0x100, 0, 4, 4, 16)
        elf.extend(b'\0' * (0x1024 - len(elf)))
        elf[0x1020:0x1024] = b'\xaa\xbb\xcc\xdd'
        binary = Binary(bytes(elf))
        manifest = evidence(binary)
        manifest['sites'][0]['consumer'] = {'elf_vaddr': 0x100, 'original_hex': 'aa bb'}
        self.assertEqual(verify_candidates(binary, manifest)[0]['mechanical_status'], 'rejected')
        # The same signature in a non-executable load still defeats global uniqueness.
        self.assertEqual(binary.matches(pattern('aa bb')), [0x100])

    def test_overlap_in_virtual_mapping_rejected(self):
        elf = bytearray(self.binary.elf)
        struct.pack_into('<H', elf, 56, 2)
        struct.pack_into('<IIQQQQQQ', elf, 120, 1, 6, 0x1000, 8, 0, 4, 4, 16)
        with self.assertRaisesRegex(ValueError, 'overlapping'):
            Binary(bytes(elf))

    def test_filesz_cannot_exceed_memsz(self):
        elf = bytearray(self.binary.elf)
        struct.pack_into('<Q', elf, 64 + 40, 4)
        with self.assertRaisesRegex(ValueError, 'invalid loaded segment'):
            Binary(bytes(elf))

    def test_missing_semantic_notes_or_consumer_are_rejected(self):
        for field in ('purpose', 'initialization', 'evidence_reference', 'consumer'):
            manifest = deepcopy(self.manifest)
            del manifest['sites'][0][field]
            self.assertEqual(verify_candidates(self.binary, manifest)[0]['mechanical_status'], 'rejected')

    def test_consumer_original_bytes_checked(self):
        self.assertEqual(self.result(consumer={'elf_vaddr': 0, 'original_hex': 'ff ff'})['reason'],
                         'original bytes differ')

    def test_invalid_patterns(self):
        for value in ('', '?? ??', '0001', '0x12', '-1', 'gg', None, 5, 'ff ' * 4097):
            with self.subTest(value=str(value)[:20]), self.assertRaises(ValueError):
                pattern(value)

    def test_empty_or_duplicate_sites_rejected(self):
        for sites in ([], [self.manifest['sites'][0]] * 2):
            manifest = dict(self.manifest, sites=sites)
            with self.assertRaises(ValueError):
                verify_candidates(self.binary, manifest)

    def test_malformed_schema_rejected(self):
        for value in ([], None, {}, {'schema_version': 2}):
            with self.assertRaises(ValueError):
                verify_candidates(self.binary, value)


class AuditCliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.game = self.root / 'game'
        (self.game / 'sce_sys').mkdir(parents=True)
        (self.game / 'eboot.bin').write_bytes(fixture())
        (self.game / 'sce_sys/param.sfo').write_bytes(sfo_bytes())
        (self.game / 'patches.bin').write_bytes(b'untouched sentinel')

    def cli(self, *args):
        with redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
            return main(['--game-dir', str(self.game), *map(str, args)])

    def test_report_does_not_modify_game_or_export_game_bytes(self):
        before = {p: p.read_bytes() for p in self.game.rglob('*') if p.is_file()}
        output = self.root / 'inventory.json'
        self.assertEqual(self.cli('--output', output), 0)
        data = json.loads(output.read_text())
        self.assertEqual(data['mode'], 'inventory_only')
        self.assertFalse(data['rp02_complete'])
        self.assertTrue(all(not x['runtime_enabled'] for x in data['capabilities'].values()))
        self.assertNotIn(str(self.game), output.read_text())
        self.assertEqual(before, {p: p.read_bytes() for p in self.game.rglob('*') if p.is_file()})

    def test_existing_report_is_not_overwritten(self):
        output = self.root / 'inventory.json'
        output.write_text('previous report')
        self.assertEqual(self.cli('--output', output), 2)
        self.assertEqual(output.read_text(), 'previous report')

    def test_output_inside_game_is_rejected(self):
        self.assertEqual(self.cli('--output', self.game / 'new.json'), 2)
        self.assertFalse((self.game / 'new.json').exists())

    def test_version_109_rejected_even_without_manifest(self):
        (self.game / 'sce_sys/param.sfo').write_bytes(sfo_bytes('01.09'))
        with self.assertRaisesRegex(ValueError, 'version 1.00'):
            audit(self.game)

    def test_bad_manifest_causes_nonzero_exit(self):
        manifest = self.root / 'evidence.json'
        for value in (None, {'schema_version': 1}, []):
            manifest.write_text(json.dumps(value))
            self.assertEqual(self.cli('--manifest', manifest), 2)

    def test_rejected_candidate_reports_failure_without_applying_anything(self):
        manifest = evidence(Binary(bytes(fixture())))
        manifest['sites'][0]['original_hex'] = 'ff ff'
        path = self.root / 'evidence.json'
        path.write_text(json.dumps(manifest))
        output = self.root / 'report.json'
        self.assertEqual(self.cli('--manifest', path, '--output', output), 2)
        self.assertEqual(json.loads(output.read_text())['candidate_results'][0]['mechanical_status'], 'rejected')
        self.assertEqual((self.game / 'patches.bin').read_bytes(), b'untouched sentinel')

    def test_matched_candidate_still_does_not_complete_rp02(self):
        manifest = evidence(Binary(bytes(fixture())))
        report = audit(self.game, manifest)
        self.assertFalse(report['rp02_complete'])
        self.assertEqual(report['candidate_results'][0]['mechanical_status'], 'matched')
        self.assertTrue(all(x['status'] == 'unverified' for x in report['capabilities'].values()))


if __name__ == '__main__':
    unittest.main()
