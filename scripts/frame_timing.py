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
