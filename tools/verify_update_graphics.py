# SPDX-License-Identifier: GPL-2.0-or-later
"""Opt-in native 1.09 graphics probe, Linux x86-64; never starts the game.

Requires privately supplied, fingerprinted USA 1.09 files. Executes the native
selector, resize coordinator, shadow manager/allocator and GPU heap routines
with synthetic state and OS/GPU dependencies stubbed. No rendering is tested.
"""
import argparse
import ctypes as c
import itertools
import json
import mmap
from pathlib import Path
import platform
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from ratchet_binary_audit import Binary
from ratchet_patches import UPDATE_PROFILE, compile_groups, digest, read_linked
import ratchet_update_patches as update
import internal_resolution as resolution
import shadow_resolution as shadow
from language_split import GROUPS as LANGUAGES


def verify(game, linked):
    if sys.platform != 'linux' or platform.machine() != 'x86_64':
        raise ValueError('Requires Linux x86-64 System V ABI')
    binary = Binary((game / 'eboot.bin').read_bytes())
    image, segments, forbidden = read_linked(linked.read_bytes())
    assert digest(binary.source).hex() == UPDATE_PROFILE['source_sha256']
    assert digest(binary.elf).hex() == UPDATE_PROFILE['elf_sha256']
    compiled = {}
    for name in UPDATE_PROFILE['groups']:
        writes, prepared, skipped = compile_groups(binary, image, segments, forbidden,
                                                   [name], UPDATE_PROFILE)
        assert prepared == [name] and not skipped, (name, skipped)
        compiled[name] = writes
    # Validate every setting combination against actual source and linked bytes.
    combinations = 0
    for names in itertools.product((None, *resolution.GROUPS.values()),
                                   (None, *shadow.GROUPS.values()),
                                   (None, *LANGUAGES.values())):
        requested = [name for name in names if name]
        writes, prepared, skipped = compile_groups(binary, image, segments, forbidden,
                                                   requested, UPDATE_PROFILE)
        assert prepared == requested and not skipped, (requested, skipped)
        assert writes == sorted(w for name in requested for w in compiled[name])
        combinations += 1
    for groups in (resolution.GROUPS, shadow.GROUPS):
        writes, prepared, skipped = compile_groups(binary, image, segments, forbidden,
                                                   list(groups.values()), UPDATE_PROFILE)
        assert not writes and not prepared and len(skipped) == len(groups)
    print(f'Validated {combinations} guarded combinations', flush=True)

    mem = mmap.mmap(-1, len(image), prot=7)
    mem[:] = image
    base = c.addressof(c.c_char.from_buffer(mem))
    keep = []

    def function(address, nargs):
        return c.CFUNCTYPE(c.c_uint64, *([c.c_uint64] * nargs))(base + address)

    def stub(address, fn, nargs=0):
        callback = c.CFUNCTYPE(c.c_uint64, *([c.c_uint64] * nargs))(fn)
        keep.append(callback)
        mem[address:address + 12] = (b'\x48\xb8' + struct.pack('<Q', c.cast(callback, c.c_void_p).value)
                                    + b'\xff\xe0')

    def buffer(size, fill=0):
        obj = c.create_string_buffer(size)
        keep.append(obj)
        c.memset(c.addressof(obj), fill, size)
        return c.addressof(obj)

    def apply(name):
        for address, before, after in compiled[name]:
            mem[address:address + len(after)] = after

    def restore(address, size):
        mem[address:address + size] = image[address:address + size]

    stub(0x1f83410, lambda: 0)
    selector = function(update.RESOLUTION_ADDRESS, 3)
    selector_cases = 0
    for selected in (None, *resolution.SIZES, None):
        if selected:
            apply(resolution.GROUPS[selected])
        else:
            restore(update.RESOLUTION_ADDRESS, len(bytes.fromhex(update.RESOLUTION_ORIGINAL)))
        for mode in (0, 1, 2, 3, 4, 5, 6, 7, 0xffffffff):
            width, height = c.c_uint32(123), c.c_uint32(456)
            ok = selector(mode, c.addressof(width), c.addressof(height)) & 255
            original = {1: (320, 240), 2: (640, 480), 3: (1280, 720),
                        4: (1600, 900), 5: (1920, 1080), 6: (1920, 800)}
            expected = resolution.SIZES[selected] if selected else original.get(mode, (123, 456))
            assert (width.value, height.value) == expected
            assert bool(ok) == bool(selected or mode in original)
            selector_cases += 1
    print(f'Validated {selector_cases} selector cases', flush=True)

    # Real resize coordinator reaches teardown/recreate once, then early-outs
    # on identical dimensions. GPU resource creation is deliberately stubbed.
    resized, released = [], []
    stub(0x16eff70, lambda ctx: (released.append(ctx) or 0), 1)
    stub(0x16ee3f0, lambda ctx: (resized.append(struct.unpack('<2I', c.string_at(ctx + 0x6224, 8))) or 0), 1)
    resize = function(0x16f02d0, 3)
    context = buffer(0x6300)
    for width, height in resolution.SIZES.values():
        resize(context, width, height)
        resize(context, width, height)
    assert resized == list(resolution.SIZES.values()) and len(released) == len(resized)

    # Execute the complete shadow constructor with allocation and texture
    # creation intercepted; retain its actual sizing function and zero stores.
    packers, atlases, allocated = [], [], []
    fail = False
    def allocate(size, alignment, label):
        allocated.append((size, alignment))
        return 0 if fail else buffer(size, 0xa5)
    stub(0x179caf0, allocate, 3)
    stub(0x2828028, lambda p, value, n: (c.memset(p, value, n) or p), 3)
    stub(0xe4de30, lambda *args: (packers.append(args) or 1), 5)
    stub(0x16fce60, lambda *args: (atlases.append(args) or 1), 10)
    constructor = function(0x17c0e40, 4)
    shadow_cases = 0
    for cap in (None, *shadow.CAPS, None):
        if cap:
            apply(shadow.GROUPS[cap])
        else:
            restore(update.SHADOW_ADDRESS, len(bytes.fromhex(update.SHADOW_ORIGINAL)))
        for configured in (128, 256, 512, 1024, 1792, 4096):
            for count in (1, 128):
                for fail in (False, True):
                    manager = buffer(48, 0xa5)
                    packers.clear(); atlases.clear(); allocated.clear()
                    result = constructor(manager, configured, count, 1) & 255
                    assert bool(result) == (not fail)
                    assert c.string_at(manager + 8, 24) == bytes(24)
                    assert allocated == [(count * 80 + 0x698, 128)]
                    if not fail:
                        expected = min(configured, int(cap)) if cap else configured
                        assert struct.unpack('<2I', c.string_at(manager, 8)) == (expected, count)
                        assert len(packers) == len(atlases) == 1
                        assert packers[0][1:4] == (8192, 4096, count)
                        assert atlases[0][1:3] == (8192, 4096)
                    else:
                        assert not packers and not atlases
                    shadow_cases += 1
    print(f'Validated {shadow_cases} shadow constructor cases', flush=True)

    # The allocator returns a packed two-register result. This tiny test stub
    # records ESI/EDX, supplies coordinates and succeeds without a real atlas.
    observed = buffer(8)
    pack_stub = (b'\x48\xb8' + struct.pack('<Q', observed) + b'\x89\x30\x89\x50\x04' +
                 b'\x48\xb8' + struct.pack('<Q', (64 << 32) | 32) +
                 b'\x48\xba' + struct.pack('<Q', 1 << 32) + b'\xc3')
    mem[0xe4df60:0xe4df60 + len(pack_stub)] = pack_stub
    stub(0x16edfe0, lambda pool, size: buffer(size), 2)
    allocate_shadow = function(0x17c0ff0, 3)
    tile_cases = 0
    for maximum in (128, 256, 512, 1024, 1792):
        manager = buffer(48)
        c.c_int32.from_address(manager).value = maximum
        for request in (-1, 0, 1, 31, 32, 33, 128, 255, 512, 1792, 4096):
            tile = allocate_shadow(manager, 1234, request)
            expected = (min(request if request > 0 else maximum, maximum) + 31) & ~31
            assert struct.unpack('<2I', c.string_at(observed, 8)) == (expected, expected)
            assert struct.unpack('<3H', c.string_at(tile, 6)) == (32, 64, expected)
            assert c.c_uint8.from_address(tile + 6).value == 0
            assert c.c_uint32.from_address(tile + 8).value == 1234
            tile_cases += 1

    # Exercise the real native +128 MiB path, with the runtime's base PS4 model.
    reservations, heaps, lookups = [], [], []
    stub(0xe46870, lambda *args: 4096, 2)
    stub(0x179caf0, lambda *args: buffer(4096), 3)
    configured_heap = 1165
    def lookup(name):
        lookups.append(c.string_at(name))
        return configured_heap << 20
    stub(0xe63b40, lookup, 1)
    stub(0x28281b8, lambda: 0)  # sceKernelIsProspero
    stub(0x2828468, lambda: 0)  # sceKernelIsNeoMode
    def reserve(page, count, flags, name):
        reservations.append((page * count, flags, c.string_at(name)))
        return 0x1080000000
    stub(0xe9b170, reserve, 4)
    stub(0xe469b0, lambda *args: (heaps.append(args) or 1), 9)
    stub(0x179cf80, lambda *args: 1, 5)
    initialize = function(0x184b2f0, 0)
    heap_cases = 0
    for page, configured_heap, mode in itertools.product((16384, 65536), (1000, 1165),
                                                         (None, '1440p', '4K', None)):
        struct.pack_into('<Q', mem, 0x29a3128, page)
        mem[0x4beb650] = 0
        struct.pack_into('<I', mem, 0x4bfcd48 + 0x74, 0)
        if mode:
            apply(resolution.GROUPS[mode])
        else:
            restore(update.HEAP_ADDRESS, 5)
        reservations.clear(); heaps.clear(); lookups.clear()
        assert initialize() & 255 == 1
        expected = (resolution.GPU_HEAP_MB[mode] if mode else configured_heap + 128) << 20
        assert reservations == [(expected, 8, b'XMemGpu')], reservations
        assert len(heaps) == 1 and heaps[0][1:3] == (0x1080000000, expected)
        assert bool(lookups) == (mode is None)
        assert expected < 2 << 30
        heap_cases += 1
    print(f'Validated {heap_cases} heap initialization cases', flush=True)

    # Check the real failure branch's NULL return and printf-compatible arguments.
    label, heap_name = buffer(64), buffer(16)
    c.memmove(label, b'GBuffer Target MRT\0', 19)
    c.memmove(heap_name, b'XMemGpu\0', 8)
    struct.pack_into('<Q', mem, 0x4bebae8 + 0x18, heap_name)
    stub(0x179d550, lambda: label)
    stub(0xe46c10, lambda *args: 0, 5)
    logged = []
    def printf(fmt, heap, resource, size):
        logged.append((c.string_at(fmt), c.string_at(heap), c.string_at(resource), size))
        return 99
    stub(update.PRINTF_ADDRESS, printf, 4)
    allocate = function(0x184b4b0, 2)
    restore(update.FAILURE_ADDRESS, 5)
    assert allocate(33423360, 0x40000000) == 0 and not logged
    apply(resolution.GROUPS['4K'])
    assert allocate(33423360, 0x40000000) == 0
    assert logged == [(b'%s alloc "%s" failed: %u bytes\n', b'XMemGpu', b'GBuffer Target MRT', 33423360)], logged
    mem.close()
    return {'source_sha256': UPDATE_PROFILE['source_sha256'], 'app_version': '01.09',
            'guarded_combinations': combinations, 'selector_cases': selector_cases,
            'resize_coordinator_modes': len(resized), 'shadow_constructor_cases': shadow_cases,
            'shadow_tile_cases': tile_cases, 'heap_initialization_cases': heap_cases,
            'final_gpu_heap_mib': resolution.GPU_HEAP_MB,
            'allocation_failure_log_and_null_return': True,
            'original_restoration_passed': True, 'rendering_tested': False, 'gameplay_tested': False}


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
