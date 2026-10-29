#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Read-only RP-02 inventory and candidate-byte checks, never a patch installer.

Matching bytes do not establish what an instruction does. Semantic review and
runtime validation remain separate, mandatory steps. No game bytes are exported.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import sys

from patches import find_pattern
from prepare import load_sfo, parse_self, unpack
from ratchet_game import APP_VERSION, TITLE_ID, validate_identity

LOAD_TYPES = (1, 0x61000010)  # Same mapping as prepare.py, including SCE_RELRO.
LIMIT = 512 * 1024 * 1024
FEATURES = ('fps', 'motion_blur', 'internal_resolution')
HINTS = ('MotionBlurEnable', 'RenderSettingsUser', 'FrameRate', 'Resolution')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def integer(value):
    if isinstance(value, str) and re.fullmatch(r'0x[0-9a-fA-F]+|[0-9]+', value):
        return int(value, 16 if value.startswith('0x') else 10)
    if type(value) is int and value >= 0:
        return value
    raise ValueError('expected a nonnegative integer or hexadecimal address')


def pattern(text):
    if not isinstance(text, str):
        raise ValueError('signature must be a string')
    tokens = text.split()
    if not tokens or len(tokens) > 4096 or any(
            not re.fullmatch(r'[0-9a-fA-F]{2}|\?\?', t) for t in tokens):
        raise ValueError('signature requires byte pairs or ??, at most 4096 bytes')
    result = [None if t == '??' else int(t, 16) for t in tokens]
    if all(v is None for v in result):
        raise ValueError('signature has no fixed bytes')
    return result


def original(text):
    values = pattern(text)
    if None in values:
        raise ValueError('original bytes cannot contain wildcards')
    return bytes(values)


class Binary:
    def __init__(self, source):
        if len(source) > LIMIT:
            raise ValueError('source exceeds 512 MiB audit limit')
        self.source = source
        self.elf, header, ph, _, missing = parse_self(source)
        self.entry = header[4]
        self.format = 'ELF' if source.startswith(b'\x7fELF') else 'SELF'
        self.segments = []
        for index, p in enumerate(ph):
            if p['type'] not in LOAD_TYPES:
                continue
            if p['filesz'] > p['memsz'] or p['vaddr'] + p['memsz'] > LIMIT:
                raise ValueError('invalid loaded segment size or virtual address')
            if index in missing:
                raise ValueError('loaded segment is unavailable')
            for other in self.segments:
                if (p['memsz'] and other['memsz'] and
                        p['vaddr'] < other['vaddr'] + other['memsz'] and
                        other['vaddr'] < p['vaddr'] + p['memsz']):
                    raise ValueError('overlapping loaded virtual segments')
            physical = p['offset'] if self.format == 'ELF' else None
            if self.format == 'SELF' and p['filesz']:
                count, = unpack('<H', source, 24)
                entries = [unpack('<QQQQ', source, 32 + i * 32) for i in range(count)]
                matches = [e for e in entries if e[0] & 0x800 and (e[0] >> 20) & 4095 == index]
                if len(matches) != 1:
                    raise ValueError('loaded segment lacks a unique SELF payload mapping')
                physical = matches[0][1]
            self.segments.append(dict(p, index=index, source_offset=physical))
        if not self.segments:
            raise ValueError('no loaded segments')
        self.locate(self.entry, 1, executable=True)

    def locate(self, address, size, executable=False):
        address, size = integer(address), integer(size)
        if not size:
            raise ValueError('empty byte range')
        matches = [p for p in self.segments if p['vaddr'] <= address and
                   address + size <= p['vaddr'] + p['filesz'] and
                   (not executable or p['flags'] & 1)]
        if len(matches) != 1:
            raise ValueError('range is not within one file-backed loaded segment of the required type')
        p = matches[0]
        delta = address - p['vaddr']
        return {
            'segment_index': p['index'], 'elf_vaddr': address,
            # prepare.py maps p_vaddr directly into its pre-link image.
            'prelink_image_offset': address,
            'elf_file_offset': p['offset'] + delta,
            'source_file_offset': p['source_offset'] + delta,
        }

    def check_bytes(self, address, expected, executable=False):
        location = self.locate(address, len(expected), executable)
        start = location['elf_file_offset']
        if self.elf[start:start + len(expected)] != expected:
            raise ValueError('original bytes differ')
        source_start = location['source_file_offset']
        if self.source[source_start:source_start + len(expected)] != expected:
            raise ValueError('source/ELF coordinate mapping differs')
        return location

    def matches(self, signature):
        # Search every file-backed load, never BSS, holes or raw SELF headers.
        # Two matches are enough to reject uniqueness; no full-image allocation.
        found = []
        for p in self.segments:
            chunk = self.elf[p['offset']:p['offset'] + p['filesz']]
            found.extend(p['vaddr'] + i for i in find_pattern(chunk, signature, 2 - len(found)))
            if len(found) >= 2:
                break
        return found

    def inventory(self):
        return {
            'source_format': self.format, 'source_size': len(self.source),
            'source_sha256': digest(self.source), 'elf_sha256': digest(self.elf),
            'entry_elf_vaddr': self.entry,
            'address_convention': 'ELF p_vaddr equals prepare.py pre-link image offset; not a host pointer',
            'segments': [dict(p, file_bytes_sha256=digest(
                self.elf[p['offset']:p['offset'] + p['filesz']])) for p in self.segments],
            'string_hints_not_proof': {name: {'matches_capped_at_two': self.matches(list(name.encode() + b'\0'))}
                                      for name in HINTS},
        }


def verify_candidates(binary, manifest, title_id=TITLE_ID, app_version=APP_VERSION):
    """Mechanical validation only. Never promote a candidate to supported."""
    if not isinstance(manifest, dict) or manifest.get('schema_version') != 1:
        raise ValueError('unsupported evidence schema')
    if manifest.get('title_id') != title_id or manifest.get('app_version') != app_version:
        raise ValueError('evidence belongs to a different title or version')
    for field, actual in (('source_sha256', digest(binary.source)), ('elf_sha256', digest(binary.elf))):
        if not isinstance(manifest.get(field), str) or manifest[field] != actual:
            raise ValueError(f'{field} mismatch or missing; address-only evidence is not accepted')
    sites = manifest.get('sites')
    if not isinstance(sites, list) or not sites:
        raise ValueError('evidence has no candidate sites')
    results, names = [], set()
    for site in sites:
        if not isinstance(site, dict) or not isinstance(site.get('id'), str) or not site['id'].strip():
            raise ValueError('every candidate requires a nonempty id')
        if site['id'] in names:
            raise ValueError('duplicate candidate id')
        names.add(site['id'])
        result = {'id': site['id'], 'mechanical_status': 'rejected'}
        try:
            if site.get('feature') not in FEATURES:
                raise ValueError('unknown feature')
            result['feature'] = site['feature']
            for field in ('purpose', 'initialization', 'evidence_reference'):
                if not isinstance(site.get(field), str) or not site[field].strip():
                    raise ValueError(f'missing {field} evidence note')
            sig = pattern(site.get('signature'))
            matches = binary.matches(sig)
            if len(matches) != 1:
                raise ValueError('signature absent' if not matches else 'signature is not unique')
            offset = integer(site.get('offset_in_signature'))
            expected = original(site.get('original_hex'))
            if offset + len(expected) > len(sig):
                raise ValueError('candidate byte range extends beyond signature')
            address = integer(site.get('elf_vaddr'))
            if address != matches[0] + offset:
                raise ValueError('signature/address mismatch')
            location = binary.check_bytes(address, expected)
            consumer = site.get('consumer')
            if not isinstance(consumer, dict):
                raise ValueError('missing consumer instruction evidence')
            consumer_location = binary.check_bytes(
                integer(consumer.get('elf_vaddr')), original(consumer.get('original_hex')), executable=True)
            result.update(mechanical_status='matched', location=location, consumer_location=consumer_location,
                          semantic_status='review_required', runtime_status='not_tested')
        except ValueError as error:
            result['reason'] = str(error)
        results.append(result)
    return results


def audit(game, manifest=None):
    game = Path(game)
    sfo_path = game / 'sce_sys/param.sfo'
    identity = validate_identity(load_sfo(sfo_path))
    path = game / 'eboot.bin'
    # A bounded read also handles growth between stat and read.
    with path.open('rb') as stream:
        source = stream.read(LIMIT + 1)
    binary = Binary(source)
    report = {
        'schema_version': 1, 'title_id': identity['TITLE_ID'], 'app_version': identity['APP_VER'],
        'binary': binary.inventory(), 'mode': 'inventory_only' if manifest is None else 'candidate_check',
        'capabilities': {f: {'status': 'unverified', 'runtime_enabled': False} for f in FEATURES},
        'rp02_complete': False,
    }
    if manifest is not None:
        report['candidate_results'] = verify_candidates(binary, manifest, identity['TITLE_ID'], identity['APP_VER'])
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game-dir', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, help='Optional researcher-supplied candidate evidence JSON')
    parser.add_argument('--output', type=Path, help='New JSON report outside the game directory; default stdout')
    args = parser.parse_args(argv)
    try:
        if args.output and args.output.resolve().is_relative_to(args.game_dir.resolve()):
            raise ValueError('report must be outside the game directory')
        manifest = json.loads(args.manifest.read_text(encoding='utf-8')) if args.manifest else None
        if args.manifest and manifest is None:
            raise ValueError('manifest cannot be null')
        report = audit(args.game_dir, manifest)
        payload = json.dumps(report, indent=2) + '\n'
        if args.output:
            with args.output.open('x', encoding='utf-8') as stream:
                stream.write(payload)
        else:
            print(payload, end='')
        print('Inventory/candidate checks only: no patches applied; RP-02 is not accepted.', file=sys.stderr)
        return 2 if any(r['mechanical_status'] == 'rejected' for r in report.get('candidate_results', [])) else 0
    except (OSError, ValueError, struct.error) as error:
        print(f'Binary audit failed: {error}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
