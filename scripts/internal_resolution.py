# SPDX-License-Identifier: GPL-2.0-or-later
"""Restart-only native scene dimensions for the fingerprinted BASE 01.00 build.

Override the selector's width/height outputs, preserving its boolean contract.
Its caller uses ResizeSharedBuffers; host output/window sizes remain independent.
Original removes the override and restores the game's resolution policy.
High-resolution groups also reserve native resource-heap and direct-pool headroom.
"""
from guest_memory import DMEM_RETAIL_MB

SIZES = {'720p': (1280, 720), '900p': (1600, 900), '1080p': (1920, 1080),
         '1440p': (2560, 1440), '4K': (3840, 2160)}
GROUPS = {mode: f'Ratchet Internal Resolution {mode} (experimental)' for mode in SIZES}
_ORIGINAL = 'FF CF 83 FF 05 76 03 31 C0 C3 48 8D 05 5F 00 00 00 48 63 0C B8 48 01 C1 FF E1'
# Fixed BASE 01.00 XMemGpu capacities for the experimental high-resolution modes.
# The observed retail heap is 1165 MiB. Extra space is bounded test headroom,
# not a measured minimum or a guarantee that a whole level fits.
RETAIL_GPU_HEAP_MB = 1165
GPU_HEAP_MB = {'1440p': 1549, '4K': 1933}
_HEAP_SIGNATURE = '4C 89 E7 E8 07 AE 58 FF 89 C0 48 8D 44 03 FF'
_FAILURE_SIGNATURE = '31 C0 4C 89 FA 4C 89 F1 E8 57 B5 5A FF 4C 89 E0'


def writes(mode):
    width, height = SIZES[mode]
    # mov [rsi],width; mov [rdx],height; mov al,1; ret. Whole instruction span.
    replacement = (b'\xc7\x06' + width.to_bytes(4, 'little') + b'\xc7\x02' +
                   height.to_bytes(4, 'little') + b'\xb0\x01\xc3' + b'\x90' * 11)
    result = [{'signature': _ORIGINAL, 'offset': 0, 'elf_vaddr': 0x178b4a0,
               'original_hex': _ORIGINAL, 'replacement_hex': replacement.hex(' ')}]
    if mode in GPU_HEAP_MB:
        # Replace only the XMemGpu configuration lookup with mov eax,bytes.
        # Native alignment, reservation and heap initialization remain intact.
        heap = b'\xb8' + (GPU_HEAP_MB[mode] << 20).to_bytes(4, 'little')
        # This allocator's failure-only logger is a no-op in the retail image.
        # Route its existing printf-compatible arguments to the native printf PLT.
        diagnostic = b'\xe8' + (0x2c88338 - (0x19088c4 + 5)).to_bytes(4, 'little', signed=True)
        result.extend([
            {'signature': _HEAP_SIGNATURE, 'offset': 3, 'elf_vaddr': 0x1908724,
             'original_hex': 'E8 07 AE 58 FF', 'replacement_hex': heap.hex(' ')},
            {'signature': _FAILURE_SIGNATURE, 'offset': 8, 'elf_vaddr': 0x19088c4,
             'original_hex': 'E8 57 B5 5A FF', 'replacement_hex': diagnostic.hex(' ')},
        ])
    return result


PATCH_GROUPS = {name: {'writes': writes(mode)} for mode, name in GROUPS.items()}


def normalize(value):
    return value if value in SIZES else 'original'


def requested_groups(value, other=()):
    names = [name for name in other if name not in GROUPS.values()]
    selected = GROUPS.get(normalize(value))
    return names + ([selected] if selected else [])


def launch_environment(report, explicit_dmem=None):
    selected = [mode for mode, name in GROUPS.items() if name in report.get('prepared', [])]
    mode = selected[0] if len(selected) == 1 else 'original'
    env = {'RATCHET_INTERNAL_RESOLUTION': mode}
    if mode in GPU_HEAP_MB:
        required = DMEM_RETAIL_MB + GPU_HEAP_MB[mode] - RETAIL_GPU_HEAP_MB
        try:
            explicit = int(explicit_dmem)
        except (ValueError, TypeError):
            explicit = 0
        # Match runtime_memory.c's accepted range; never lower a valid larger pool.
        if not DMEM_RETAIL_MB <= explicit <= 16384:
            explicit = DMEM_RETAIL_MB
        env['RATCHET_RESOLUTION_DMEM_MB'] = str(max(required, explicit))
    return env
