# SPDX-License-Identifier: GPL-2.0-or-later
"""Restart-only native scene dimensions for the fingerprinted BASE 01.00 build.

Override the selector's width/height outputs, preserving its boolean contract.
Its caller uses ResizeSharedBuffers; host output/window sizes remain independent.
Original removes the override and restores the game's resolution policy.
"""
SIZES = {'720p': (1280, 720), '900p': (1600, 900), '1080p': (1920, 1080),
         '1440p': (2560, 1440), '4K': (3840, 2160)}
GROUPS = {mode: f'Ratchet Internal Resolution {mode} (experimental)' for mode in SIZES}
_ORIGINAL = 'FF CF 83 FF 05 76 03 31 C0 C3 48 8D 05 5F 00 00 00 48 63 0C B8 48 01 C1 FF E1'


def writes(mode):
    width, height = SIZES[mode]
    # mov [rsi],width; mov [rdx],height; mov al,1; ret. Whole instruction span.
    replacement = (b'\xc7\x06' + width.to_bytes(4, 'little') + b'\xc7\x02' +
                   height.to_bytes(4, 'little') + b'\xb0\x01\xc3' + b'\x90' * 11)
    return [{'signature': _ORIGINAL, 'offset': 0, 'elf_vaddr': 0x178b4a0,
             'original_hex': _ORIGINAL, 'replacement_hex': replacement.hex(' ')}]


PATCH_GROUPS = {name: {'writes': writes(mode)} for mode, name in GROUPS.items()}


def normalize(value):
    return value if value in SIZES else 'original'


def requested_groups(value, other=()):
    names = [name for name in other if name not in GROUPS.values()]
    selected = GROUPS.get(normalize(value))
    return names + ([selected] if selected else [])


def launch_environment(report):
    selected = [mode for mode, name in GROUPS.items() if name in report.get('prepared', [])]
    return {'RATCHET_INTERNAL_RESOLUTION': selected[0] if len(selected) == 1 else 'original'}
