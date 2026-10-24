#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Verified Ratchet patch transactions. Never modify the dump or linked boot file.

RP-03 supplies the transport and guards. RP-04 adds opt-in experimental 60 FPS;
gameplay acceptance is separate. RP-02 evidence is not an enable list.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import struct

from ratchet_binary_audit import Binary, LIMIT, integer, original, pattern
from ratchet_game import validate_identity
from frame_timing import FPS60_GROUP, FPS60_WRITES
from prepare import load_sfo, span, unpack

PROFILE = {
    'title_id': 'CUSA01047', 'app_version': '01.00',
    'source_sha256': 'fdf72d683f305ab1a70adfe246e9ac1dbbd4ceb988b1327157b6bda55476697d',
    'elf_sha256': 'dc1a8862016cb80060928e911ab933d6e380014c1128e537642f9f569f3a05cf',
    'groups': {FPS60_GROUP: {'writes': FPS60_WRITES}},  # Opt-in; no external activation.
}
HEADER = struct.Struct('<8sQ32s16sQ')
MAX_WRITES = 1024
MAX_BYTES = 4096
MAX_PACKET = HEADER.size + MAX_WRITES * (16 + MAX_BYTES * 2)


def digest(data):
    return hashlib.sha256(data).digest()


def overlap(a, n, b, m):
    return a < b + m and b < a + n


def atomic_write(path, data):
    path = Path(path)
    tmp = path.with_name(path.name + '.tmp')
    try:
        with tmp.open('wb') as stream:
            stream.write(data)
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def save_status(out, report):
    atomic_write(Path(out) / 'patch_status.json', (json.dumps(report, indent=2) + '\n').encode())


def encode(image, writes, token):
    if len(writes) > MAX_WRITES:
        raise ValueError('too many patch writes')
    chunks = [HEADER.pack(b'RCPATCH3', len(image) if writes else 0,
                         digest(image) if writes else bytes(32), token, len(writes))]
    for address, before, after in writes:
        if not 0 < len(before) == len(after) <= MAX_BYTES:
            raise ValueError('replacement must preserve length, at most 4096 bytes')
        chunks.extend((struct.pack('<QQ', address, len(before)), before, after))
    return b''.join(chunks)


def reset(out):
    """Invalidate receipts first, and replace old writes before any launch can fail."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    (out / 'patch_receipt.bin').unlink(missing_ok=True)
    (out / 'patch_receipt.bin.tmp').unlink(missing_ok=True)
    token = secrets.token_bytes(16)
    atomic_write(out / 'patches.bin', encode(b'', [], token))
    report = {'schema_version': 3, 'transaction': token.hex(), 'phase': 'disabled',
              'prepared': [], 'applied': [], 'skipped': {}, 'write_count': 0}
    save_status(out, report)
    return report


def read_linked(data):
    """Bounded G3PROBE5 metadata parser; retains relocation slots as forbidden ranges."""
    magic, size, entry, ns, nr, ni, flags = unpack('<8s6Q', data, 0)
    if magic != b'G3PROBE5' or size > LIMIT or ns > 4096 or nr > LIMIT // 32 or ni > LIMIT // 128:
        raise ValueError('invalid linked image header')
    pos = 96  # header + procparam + main TLS
    nm, = unpack('<Q', data, pos)
    if nm > 16:
        raise ValueError('too many linked modules')
    pos += 8 + nm * 56
    nb, = unpack('<Q', data, pos)
    if nb > ni:
        raise ValueError('invalid linked binding count')
    pos += 8 + nb * 24
    segments = [unpack('<3Q', data, pos + i * 24) for i in range(ns)]
    for a, n, f in segments:
        if a > size or n > size - a or f > 7:
            raise ValueError('invalid linked segment')
    pos += ns * 24 + ni * 128
    relocs = [unpack('<4Q', data, pos + i * 32)[0] for i in range(nr)]
    if any(a > size or 8 > size - a for a in relocs):
        raise ValueError('invalid linked relocation')
    pos += nr * 32
    image = bytes(span(data, pos, size))
    if pos + size != len(data):
        raise ValueError('trailing linked-image bytes')
    return image, segments, [(a, 8) for a in relocs]


def isa_ranges(data, image):
    """Reserve all ISA sites, including the extra instruction in relocated sites."""
    if len(data) < 64 or data[:8] != b'G3ISA1\0\0':
        raise ValueError('invalid ISA table')
    size, = unpack('<Q', data, 8)
    count, = unpack('<I', data, 48)
    if size != len(image) or data[16:48] != digest(image) or count > 1 << 20 or len(data) != 64 + count * 64:
        raise ValueError('ISA table does not match linked image')
    ranges = []
    for i in range(count):
        pos = 64 + i * 64
        address, = unpack('<Q', data, pos)
        length, mode, relocated = data[pos + 8], data[pos + 11], data[pos + 47]
        length = length + relocated if mode == 1 else length
        if not length or address > len(image) or length > len(image) - address:
            raise ValueError('invalid ISA range')
        ranges.append((address, length))
    return ranges


def compile_groups(binary, image, segments, forbidden, requested, profile=PROFILE):
    """Reject each invalid group whole; overlapping groups are both rejected.

    A group is {'writes': [{'signature', 'offset', 'elf_vaddr',
    'original_hex', 'replacement_hex'}]}. Profile injection is for synthetic
    unit tests; production accepts only the module's reviewed PROFILE.
    """
    requested = list(dict.fromkeys(requested))
    skipped, candidates = {}, {}
    try:
        validate_identity({'TITLE_ID': profile['title_id'], 'APP_VER': profile['app_version']})
    except (KeyError, ValueError) as error:
        return [], [], {name: str(error) for name in requested}
    if (digest(binary.source).hex() != profile['source_sha256'] or
            digest(binary.elf).hex() != profile['elf_sha256']):
        return [], [], {name: 'source/ELF fingerprint mismatch' for name in requested}
    for name in requested:
        try:
            if name not in profile['groups']:
                raise ValueError('feature has no reviewed RP-03 replacement group')
            group = profile['groups'][name]
            if not isinstance(group.get('writes'), list) or not group['writes']:
                raise ValueError('empty replacement group')
            writes = []
            for site in group['writes']:
                sig = pattern(site['signature'])
                found = binary.matches(sig)
                if len(found) != 1:
                    raise ValueError('signature absent' if not found else 'signature is not unique')
                address, offset = integer(site['elf_vaddr']), integer(site['offset'])
                before, after = original(site['original_hex']), original(site['replacement_hex'])
                if offset < 0 or address != found[0] + offset or offset + len(before) > len(sig):
                    raise ValueError('signature/address or guard range mismatch')
                if not 0 < len(before) == len(after) <= MAX_BYTES or before == after:
                    raise ValueError('replacement must change bytes without changing length')
                binary.check_bytes(address, before)
                if not any(a <= address and address + len(before) <= a + n for a, n, _ in segments):
                    raise ValueError('write outside linked segments')
                if image[address:address + len(before)] != before:
                    raise ValueError('linking changed original bytes')
                # Reserve the full signature window, not just edited immediate bytes.
                if any(overlap(found[0], len(sig), a, n) for a, n in forbidden):
                    raise ValueError('signature overlaps relocation or ISA rewrite')
                if any(overlap(address, len(before), a, len(old)) for a, old, new in writes):
                    raise ValueError('overlapping writes within group')
                writes.append((address, before, after))
            candidates[name] = writes
        except (KeyError, TypeError, ValueError, struct.error) as error:
            skipped[name] = str(error)
    names = list(candidates)
    for i, left in enumerate(names):
        for right in names[i + 1:]:
            if any(overlap(a, len(old), b, len(orig))
                   for a, old, _ in candidates[left] for b, orig, _ in candidates[right]):
                skipped[left] = f'write conflict with {right}'
                skipped[right] = f'write conflict with {left}'
    prepared = [name for name in names if name not in skipped]
    writes = sorted(w for name in prepared for w in candidates[name])
    if len(writes) > MAX_WRITES:
        return [], [], {name: 'transaction exceeds write limit' for name in requested}
    return writes, prepared, skipped


def prepare(game, out, requested=(), isa_path=None):
    """Start a fresh transaction; invalid requests never inherit an old packet."""
    out, game = Path(out), Path(game)
    if out.resolve().is_relative_to(game.resolve()):
        raise ValueError('patch output must be outside the original game directory')
    report = reset(out)
    requested = list(dict.fromkeys(requested))
    report['requested'] = requested
    if not requested:
        save_status(out, report)
        print('Patches: disabled (no reviewed feature selected)', flush=True)
        return report  # No game patch requested: unchanged baseline, even on an unknown dump.
    try:
        validate_identity(load_sfo(game / 'sce_sys/param.sfo'))
        with (game / 'eboot.bin').open('rb') as stream:
            binary = Binary(stream.read(LIMIT + 1))
        report['source_sha256'] = digest(binary.source).hex()
        image, segments, forbidden = read_linked((out / 'boot-linked.bin').read_bytes())
        if isa_path:
            forbidden += isa_ranges(Path(isa_path).read_bytes(), image)
        # Linker's FS->GS edits fail byte checks above. Windows' later GS->TEB
        # transformation also reserves each entire instruction, even on Linux.
        tcb = bytes.fromhex('65488b042500000000')
        at = image.find(tcb)
        while at >= 0:
            forbidden.append((at, len(tcb)))
            at = image.find(tcb, at + 1)
        writes, prepared, skipped = compile_groups(binary, image, segments, forbidden, requested)
        atomic_write(out / 'patches.bin', encode(image, writes, bytes.fromhex(report['transaction'])))
        report.update(prepared=prepared, skipped=skipped, write_count=len(writes),
                      phase='prepared' if writes else 'disabled')
    except (OSError, ValueError, struct.error) as error:
        # reset() already replaced old writes and invalidated old acknowledgements.
        report.update(phase='rejected', skipped={name: str(error) for name in requested})
    save_status(out, report)
    for name, reason in report['skipped'].items():
        print(f'Patches: {name} skipped ({reason})', flush=True)
    if report['prepared']:
        print(f'Patches: prepared {report["prepared"]}; awaiting loader confirmation', flush=True)
    return report


def status(out):
    """Only the current loader receipt can promote prepared groups to applied."""
    out = Path(out)
    try:
        report = json.loads((out / 'patch_status.json').read_text())
        if not isinstance(report, dict):
            raise ValueError('patch status must be an object')
        if report.get('schema_version') != 3:
            return {'applied': [], 'skipped': {}, 'phase': 'unconfirmed_legacy_status'}
        report['applied'] = []
        if report.get('phase') == 'loader_confirmed':
            report['phase'] = 'prepared' if report.get('prepared') else 'disabled'
        receipt = (out / 'patch_receipt.bin').read_bytes()
        expected = struct.pack('<8s16sQ', b'RCPACK3\0', bytes.fromhex(report['transaction']), report['write_count'])
        if receipt == expected:
            report['applied'] = report['prepared']
            report['phase'] = 'loader_confirmed'
        return report
    except FileNotFoundError:
        return report if 'report' in locals() else None
    except (OSError, ValueError, KeyError, TypeError, struct.error):
        return {'applied': [], 'skipped': {}, 'phase': 'invalid_status'}


def finish(out, returncode):
    report = status(out)
    if report is None:
        return
    report['process_returncode'] = returncode
    if report.get('prepared') and report.get('phase') != 'loader_confirmed':
        report['phase'] = 'loader_unconfirmed'
        report['skipped'].update({name: 'loader did not confirm this transaction' for name in report['prepared']})
    save_status(out, report)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game-dir', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--select', default='', help='Reviewed names separated by semicolons; empty disables all')
    args = parser.parse_args()
    if args.out.resolve().is_relative_to(args.game_dir.resolve()):
        parser.error('--out must be outside the original game directory')
    report = prepare(args.game_dir, args.out, [n.strip() for n in args.select.split(';') if n.strip()])
    print(json.dumps(report, indent=2))
    return 2 if report['skipped'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
