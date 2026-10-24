# SPDX-License-Identifier: GPL-2.0-or-later
"""Restart-only native motion-blur gate for the fingerprinted CUSA01047 01.00 build.

Original restores the game's own policy. Off follows its existing disabled path;
it does not remove velocity producers, temporal passes or camera/object data.
"""
BLUR_OFF_GROUP = 'Ratchet Motion Blur Off (experimental)'
BLUR_OFF_WRITES = [
    {
        # cmp esi,esi sets the same flags as comparing a disabled (zero) byte
        # with zero, without changing a register. The original sete/or/branch
        # and strength-clear store remain intact, after settings parsing.
        'signature': '80 7E 01 00 0F 94 C3 44 08 EB 0F B6 F3 83 FE 01 75 0C 41 C7 84 24 A4 00 02 00 00 00 00 00 81 FA FF FF FF 00',
        'offset': 0, 'elf_vaddr': 0x17cb0b6,
        'original_hex': '80 7E 01 00',
        'replacement_hex': '39 F6 90 90',
    },
]


def normalize(value):
    return 'off' if value == 'off' else 'original'


def requested_groups(value, other=()):
    # Only the explicit startup option owns this group; ignore a stale saved name.
    names = [name for name in other if name != BLUR_OFF_GROUP]
    return names + ([BLUR_OFF_GROUP] if normalize(value) == 'off' else [])


def launch_environment(report):
    # Native transaction rejection aborts before guest entry. Preparation alone
    # is not a receipt or visual validation of motion blur, TAA or other effects.
    return {'RATCHET_MOTION_BLUR': 'off' if BLUR_OFF_GROUP in report.get('prepared', []) else 'original'}
