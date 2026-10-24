# SPDX-License-Identifier: GPL-2.0-or-later
"""Restart-only shadow-map cap for the fingerprinted CUSA01047 01.00 build.

Clamp the manager's configured maximum before tile allocation. Keep the atlas,
packing rules, tile metadata and smaller per-light requests unchanged.
"""
CAPS = ('1024', '512', '256')
GROUPS = {cap: f'Ratchet Shadow Maps {cap}px maximum (experimental)' for cap in CAPS}
_ORIGINAL = '41 89 D6 89 75 D4 49 89 FC 49 C7 44 24 18 00 00 00 00 49 C7 44 24 10 00 00 00 00 49 C7 44 24 08 00 00 00 00'


def writes(cap):
    # min(ESI, cap), followed by the original register copies and three zero
    # stores. RAX and flags are dead here: e7fbb0 immediately replaces them.
    # Preserve the 36-byte span, including all instruction boundaries.
    replacement = (b'\xb8' + int(cap).to_bytes(4, 'little') + bytes.fromhex(
        '39 C6 0F 4F F0 41 89 D6 89 75 D4 49 89 FC 31 C0 '
        '49 89 44 24 18 49 89 44 24 10 49 89 44 24 08'))
    return [{'signature': _ORIGINAL, 'offset': 0, 'elf_vaddr': 0x186a771,
             'original_hex': _ORIGINAL, 'replacement_hex': replacement.hex(' ')}]


PATCH_GROUPS = {name: {'writes': writes(cap)} for cap, name in GROUPS.items()}


def normalize(value):
    return value if value in CAPS else 'original'


def requested_groups(value, other=()):
    names = [name for name in other if name not in GROUPS.values()]
    selected = GROUPS.get(normalize(value))
    return names + ([selected] if selected else [])


def launch_environment(report):
    selected = [cap for cap, name in GROUPS.items() if name in report.get('prepared', [])]
    return {'RATCHET_SHADOW_RESOLUTION': selected[0] if len(selected) == 1 else 'original'}
