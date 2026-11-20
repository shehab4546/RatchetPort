# SPDX-License-Identifier: GPL-2.0-or-later
"""CUSA01047 01.00 opt-in frame timing; gameplay acceptance remains pending.

The patch transaction verifies the exact SELF/ELF before using these sites.
See docs/RP04_FRAME_TIMING.md for disassembly evidence and test limits.
"""
FPS60_GROUP = 'Ratchet 60 FPS (experimental)'
FPS60_WRITES = [
    {
        # Replace the settings-to-frame-state copy, after settings parsing.
        # The next instruction reloads xmm0 for the untouched alternate interval.
        'signature': 'C5 FA 10 46 24 C5 FA 11 47 1C C5 FA 10 46 28 C5 FA 11 47 20 C6 47 24 01 C7 47 2C 00 00 00 00 4D',
        'offset': 0, 'elf_vaddr': 0x17b7664,
        'original_hex': 'C5 FA 10 46 24 C5 FA 11 47 1C',
        'replacement_hex': 'C7 47 1C 00 00 80 3F 90 90 90',
    },
    {
        # Keep period * interval as the floor instead of raising it to a
        # caller's legacy minimum. Retain the 1/60 safety floor, upper bound,
        # elapsed TSC, smoothing, pause and time-scale instructions.
        'signature': 'C5 FB 10 4D E0 C5 FB 5F C1 C5 FB 5F 0D 03 3D 7C 01 C5 FB 10 55 E8 C5 FB 5F C2 C5 FB 11 4B 40 C5',
        'offset': 5, 'elf_vaddr': 0x171e7a1,
        'original_hex': 'C5 FB 5F C1',
        'replacement_hex': '90 90 90 90',
    },
]
# The same two writes in the European edition (CUSA01073 01.00), located by behaviour; see
# docs/EUROPE_EDITION.md. Its newer compiler copies the interval with integer moves, so the
# 1.0 store fits only by reordering the 34-byte block (same instructions and effects; `mov esi,8`
# becomes `push 8; pop rsi` in this non-leaf function, which keeps nothing below rsp).
FPS60_WRITES_EUROPE = [
    {
        # mov eax,[rsi+24h]; imul r15,r12,148h; mov [r14+1Ch],eax; mov eax,[rsi+28h]; mov esi,8;
        # mov rdi,r15; mov [r14+20h],eax; mov byte [r14+24h],1  ->  interval 1.0, rest unchanged.
        'signature': '8B 46 24 4D 69 FC 48 01 00 00 41 89 46 1C 8B 46 28 BE 08 00 00 00 4C 89 FF '
                     '41 89 46 20 41 C6 46 24 01 41 C7 46 2C 00 00',
        'offset': 0, 'elf_vaddr': 0x1722f64,
        'original_hex': '8B 46 24 4D 69 FC 48 01 00 00 41 89 46 1C 8B 46 28 BE 08 00 00 00 4C 89 FF '
                        '41 89 46 20 41 C6 46 24 01',
        'replacement_hex': '4D 69 FC 48 01 00 00 41 C7 46 1C 00 00 80 3F 8B 46 28 41 89 46 20 '
                           '41 C6 46 24 01 4C 89 FF 6A 08 5E 90',
    },
    {
        # vmaxsd xmm0,xmm0,xmm1 (caller minimum) before the retained 1/60 floor.
        'signature': '80 78 24 00 75 05 C5 FA 5F 40 20 C5 FA 59 40 18 C5 FB 10 4D E0 C5 FB 10 55 E8 '
                     'C5 FA 5A C0 C5 FB 5F C1 C5 FB 5F 0D D0 5B',
        'offset': 30, 'elf_vaddr': 0x16991f4,
        'original_hex': 'C5 FB 5F C1',
        'replacement_hex': '90 90 90 90',
    },
]


def normalize(value):
    return '60' if str(value) == '60' else '30'


def requested_groups(value, other=()):
    # The explicit game_fps setting owns this group. A stale saved patch name
    # must never re-enable it after selecting Original and restarting.
    names = [name for name in other if name != FPS60_GROUP]
    return names + ([FPS60_GROUP] if normalize(value) == '60' else [])


def launch_environment(report, explicit_limit=None):
    # Prepared is only enough to choose a host ceiling: the native loader
    # rejects the launch if it cannot apply the whole verified transaction.
    fps = 60 if FPS60_GROUP in report.get('prepared', []) else 30
    try:
        limit = int(explicit_limit)
    except (TypeError, ValueError):
        limit = fps
    limit = min(limit, fps) if limit > 0 else fps
    return {'RATCHET_ENGINE_FPS': str(fps), 'RATCHET_FPS_LIMIT': str(limit),
            'RATCHET_VBLANK_HZ': '60'}
