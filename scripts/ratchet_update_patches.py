# SPDX-License-Identifier: GPL-2.0-or-later
"""Independently reviewed CUSA01047 1.09 patch sites; never reuse 1.00 offsets.

The 1.09 resource lookup has the same argument and table layout, with a different
98-byte implementation. Its unsigned sorted search returns 12-byte records.
Only localization_all changes language; audio and other resources keep EDX.
Resolution, shadow caps and high-resolution heap sites are specific to 1.09.
See docs/UPDATE_COMPATIBILITY.md for evidence and validation limits.
"""
from language_split import GROUPS, TEXT_IDS, TEMPLATE
from internal_resolution import SIZES, GPU_HEAP_MB, GROUPS as RESOLUTION_GROUPS
from shadow_resolution import GROUPS as SHADOW_GROUPS

LOOKUP_ADDRESS = 0x17dd2b0
LOOKUP_ORIGINAL = (
    '55 48 89 e5 41 56 53 48 63 d2 48 89 f0 48 89 fb 89 c9 '
    '48 8d 34 52 48 c1 e6 04 48 03 33 44 8b 34 ce 8b 54 ce 04 '
    'be 08 00 00 00 48 89 c1 4a 8d 3c f5 00 00 00 00 48 03 7b 08 '
    'e8 e2 83 6a ff 31 c9 48 83 f8 ff 74 14 4b 8d 0c 76 '
    '48 8d 04 40 48 c1 e1 02 48 03 4b 18 48 8d 0c 81 '
    '48 89 c8 5b 41 5e 5d c3'
)


def language_writes(value):
    replacement = bytearray(TEMPLATE)
    replacement[16:20] = TEXT_IDS[value].to_bytes(4, 'little')
    replacement.extend(b'\x90' * (len(bytes.fromhex(LOOKUP_ORIGINAL)) - len(replacement)))
    return [{'signature': LOOKUP_ORIGINAL, 'offset': 0, 'elf_vaddr': LOOKUP_ADDRESS,
             'original_hex': LOOKUP_ORIGINAL, 'replacement_hex': replacement.hex(' ')}]


RESOLUTION_ADDRESS = 0x16fa460
RESOLUTION_ORIGINAL = (
    '55 48 89 e5 41 56 53 ff cf 49 89 d6 48 89 f3 83 ff 05 77 74 '
    '48 8d 05 e1 0f 3a 01 48 63 0c b8 48 01 c1 ff e1'
)
SHADOW_ADDRESS = 0x17c0e51
SHADOW_ORIGINAL = (
    '41 89 d6 49 89 fc c5 f8 57 c0 89 75 d4 44 89 f7 '
    'c4 c1 78 11 44 24 08 49 c7 44 24 18 00 00 00 00'
)
HEAP_ADDRESS = 0x184b364
FAILURE_ADDRESS = 0x184b549
PRINTF_ADDRESS = 0x2828408


def resolution_writes(mode):
    width, height = SIZES[mode]
    # Override at the entry, before saving registers. RSI/RDX are output pointers.
    replacement = (b'\xc7\x06' + width.to_bytes(4, 'little') + b'\xc7\x02' +
                   height.to_bytes(4, 'little') + b'\xb0\x01\xc3' + b'\x90' * 21)
    writes = [{'signature': RESOLUTION_ORIGINAL, 'offset': 0,
               'elf_vaddr': RESOLUTION_ADDRESS, 'original_hex': RESOLUTION_ORIGINAL,
               'replacement_hex': replacement.hex(' ')}]
    if mode in GPU_HEAP_MB:
        # 1.09 adds 128 MiB after the configuration lookup. Account for that
        # addition: final capacities remain 1549/1933 MiB, below the 2 GiB slot.
        # The runtime exposes the base PS4 model (Neo/Prospero queries return 0).
        heap = b'\xb8' + ((GPU_HEAP_MB[mode] - 128) << 20).to_bytes(4, 'little')
        diagnostic = b'\xe8' + (PRINTF_ADDRESS - (FAILURE_ADDRESS + 5)).to_bytes(
            4, 'little', signed=True)
        writes.extend([
            {'signature': '4c 8b 29 e8 d7 87 61 ff 48 89 c3', 'offset': 3,
             'elf_vaddr': HEAP_ADDRESS, 'original_hex': 'e8 d7 87 61 ff',
             'replacement_hex': heap.hex(' ')},
            {'signature': '48 0f 45 f0 31 c0 e8 b2 6c 64 ff 4c 89 e0', 'offset': 6,
             'elf_vaddr': FAILURE_ADDRESS, 'original_hex': 'e8 b2 6c 64 ff',
             'replacement_hex': diagnostic.hex(' ')},
        ])
    return writes


def shadow_writes(cap):
    # min(ESI, cap), then the original manager/count/maximum and zero stores.
    # EAX/flags are replaced by the next call. e4de20 uses GPRs only; XMM0 is
    # caller-saved. MOV AH encodes these multiples of 256 within the 32-byte span.
    replacement = bytes.fromhex(
        f'31 c0 b4 {int(cap) >> 8:02x} 39 c6 0f 4f f0 41 89 d6 49 89 fc '
        '89 75 d4 0f 57 c0 0f 11 47 08 66 0f d6 47 18 89 d7')
    return [{'signature': SHADOW_ORIGINAL, 'offset': 0, 'elf_vaddr': SHADOW_ADDRESS,
             'original_hex': SHADOW_ORIGINAL, 'replacement_hex': replacement.hex(' ')}]


# Motion blur, frame timing and prompt artwork still require independent review.
PATCH_GROUPS = {
    **{name: {'writes': language_writes(value)} for value, name in GROUPS.items()},
    **{name: {'writes': resolution_writes(value)} for value, name in RESOLUTION_GROUPS.items()},
    **{name: {'writes': shadow_writes(value)} for value, name in SHADOW_GROUPS.items()},
}
