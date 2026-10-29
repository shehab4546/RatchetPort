# SPDX-License-Identifier: GPL-2.0-or-later
"""Exercise only the fingerprinted 1.09 resource lookup with synthetic tables.

Linux x86-64 System V ABI; never starts the game or writes its installation.
Checks all language overrides, unsigned hashes, empty buckets and resource classes.
"""
import argparse
import ctypes
import json
import mmap
from pathlib import Path
import platform
import random
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from ratchet_binary_audit import Binary
from ratchet_patches import UPDATE_PROFILE, compile_groups, digest, read_linked
from ratchet_update_patches import LOOKUP_ADDRESS, LOOKUP_ORIGINAL
from language_split import GROUPS, TEXT_IDS


def verify(game, linked):
    if sys.platform != 'linux' or platform.machine() != 'x86_64':
        raise ValueError('Requires Linux x86-64 System V ABI')
    binary = Binary((game / 'eboot.bin').read_bytes())
    image, segments, forbidden = read_linked(linked.read_bytes())
    assert digest(binary.source).hex() == UPDATE_PROFILE['source_sha256']
    assert digest(binary.elf).hex() == UPDATE_PROFILE['elf_sha256']
    # The update retains the base language conversion table and USA SKU mask.
    table = struct.pack('<23I', 9, 1, 6, 15, 7, 8, 4, 13, 14, 10, 23, 22,
                        5, 16, 3, 11, 12, 18, 2, 20, 21, 19, 6)
    assert image[0x29a2ab0:0x29a2ab0 + len(table)] == table
    assert image[0x31bf8d:0x31bf92] == bytes.fromhex('b8 42 20 24 00')
    memory = mmap.mmap(-1, len(image), prot=mmap.PROT_READ | mmap.PROT_WRITE | mmap.PROT_EXEC)
    memory[:] = image
    address = ctypes.addressof(ctypes.c_char.from_buffer(memory))
    lookup = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint64,
                             ctypes.c_int, ctypes.c_uint)(address + LOOKUP_ADDRESS)
    target = 0xbe55d94f171bf8de
    rng = random.Random(109)
    hashes, ranges, buckets = [], [], {}
    for language in range(24):
        for resource in range(6):
            count = (language * 7 + resource * 3) % 19
            bucket = sorted({rng.getrandbits(64) for _ in range(count)} |
                            ({0, target, (1 << 64) - 1} if count else set()))
            first = len(hashes)
            ranges.extend((first, len(bucket)))
            hashes.extend(bucket)
            buckets[language, resource] = {h: first + i for i, h in enumerate(bucket)}
    index = (ctypes.c_uint32 * len(ranges))(*ranges)
    keys = (ctypes.c_uint64 * len(hashes))(*hashes)
    records = ctypes.create_string_buffer(12 * len(hashes))
    records_address = ctypes.addressof(records)
    context = (ctypes.c_void_p * 4)(ctypes.addressof(index), ctypes.addressof(keys),
                                  None, records_address)
    checked = 0
    for selected in (None, *GROUPS):
        if selected is None:
            replacement = bytes.fromhex(LOOKUP_ORIGINAL)
        else:
            name = GROUPS[selected]
            writes, prepared, skipped = compile_groups(binary, image, segments, forbidden,
                                                       [name], UPDATE_PROFILE)
            assert prepared == [name] and not skipped and len(writes) == 1
            assert writes[0][0] == LOOKUP_ADDRESS
            replacement = writes[0][2]
        memory[LOOKUP_ADDRESS:LOOKUP_ADDRESS + len(replacement)] = replacement
        for (language, resource), bucket in buckets.items():
            for key in {*bucket, target, 1, (1 << 63), (1 << 64) - 2}:
                effective = TEXT_IDS[selected] if selected and key == target else language
                record = buckets[effective, resource].get(key)
                expected = None if record is None else records_address + 12 * record
                actual = lookup(ctypes.addressof(context), key, language, resource)
                assert actual == expected, (selected, language, resource, hex(key), actual, expected)
                checked += 1
    memory.close()
    return {'source_sha256': UPDATE_PROFILE['source_sha256'], 'app_version': '01.09',
            'lookup_cases': checked, 'language_overrides': len(GROUPS),
            'original_and_replacements_passed': True, 'linked_relocation_guards_passed': True,
            'os_table_address': '0x29a2ab0', 'usa_mask': '0x242042',
            'lookup_address': hex(LOOKUP_ADDRESS), 'gameplay_tested': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game-dir', type=Path, required=True)
    parser.add_argument('--linked', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.output.resolve().is_relative_to(args.game_dir.resolve()):
        parser.error('Use a new output file outside the game folder')
    result = verify(args.game_dir, args.linked)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
