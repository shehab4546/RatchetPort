# SPDX-License-Identifier: GPL-2.0-or-later
"""Opt-in Linux x86-64 native probe; requires the exact privately owned BASE dump.

Run: python tests/probe_resolution_heap.py /path/to/eboot.bin
Executes native heap-init, allocation-failure, texture/view and packet code with
OS/GPU dependencies stubbed. Does not render pixels, emulate a level or measure
its peak memory. No game binary is included or modified on disk.
"""
from pathlib import Path
import ctypes as c
import mmap
import platform
import struct
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from ratchet_binary_audit import Binary
from ratchet_patches import PROFILE, digest
import internal_resolution as resolution


def main(path):
    assert sys.platform == 'linux' and platform.machine() == 'x86_64'
    binary = Binary(Path(path).read_bytes())
    assert digest(binary.source).hex() == PROFILE['source_sha256']
    assert digest(binary.elf).hex() == PROFILE['elf_sha256']
    mem = mmap.mmap(-1, max(p['vaddr'] + p['memsz'] for p in binary.segments), prot=7)
    for p in binary.segments:
        mem[p['vaddr']:p['vaddr'] + p['filesz']] = binary.elf[p['offset']:p['offset'] + p['filesz']]
    base = c.addressof(c.c_char.from_buffer(mem))
    keep = []

    def stub(address, fn, nargs=0):
        callback = c.CFUNCTYPE(c.c_uint64, *([c.c_uint64] * nargs))(fn)
        keep.append(callback)
        mem[address:address+12] = b'\x48\xb8' + struct.pack('<Q', c.cast(callback, c.c_void_p).value) + b'\xff\xe0'

    def function(address, nargs):
        return c.CFUNCTYPE(c.c_uint64, *([c.c_uint64] * nargs))(base + address)

    def buffer(size):
        obj = c.create_string_buffer(size)
        keep.append(obj)
        return c.addressof(obj)

    guard = buffer(8)
    struct.pack_into('<Q', mem, 0x3a6b748, guard)
    reservations, heaps, lookups = [], [], []
    stub(0xe78030, lambda *args: 4096, 2)
    stub(0x18403c0, lambda *args: buffer(4096), 3)
    def lookup(name):
        lookups.append(c.string_at(name))
        return 1165 << 20
    stub(0xe93530, lookup, 1)
    def reserve(page, count, flags, name):
        reservations.append((page * count, flags, c.string_at(name)))
        return 0x1080000000
    stub(0xebde40, reserve, 4)
    def heap_init(*args):
        heaps.append(args)
        return 1
    stub(0xe78180, heap_init, 9)
    stub(0x1840880, lambda *args: 1, 5)
    init = function(0x19086b0, 0)
    original = bytes(mem[0x1908724:0x1908729])
    cases = 0
    for page in (16384, 65536):
        struct.pack_into('<Q', mem, 0x2c8ecb0, page)
        for mode in ('original', '1440p', '4K'):
            mem[0x4edbe84] = 0
            struct.pack_into('<I', mem, 0x4ee6cf0 + 0x74, 0)
            mem[0x1908724:0x1908729] = original if mode == 'original' else bytes.fromhex(resolution.writes(mode)[1]['replacement_hex'])
            reservations.clear(); heaps.clear(); lookups.clear()
            assert init() & 255 == 1
            size = resolution.GPU_HEAP_MB.get(mode, 1165) << 20
            assert reservations == [(size, 8, b'XMemGpu')], reservations
            assert len(heaps) == 1 and heaps[0][1:3] == (0x1080000000, size)
            assert bool(lookups) == (mode == 'original')
            cases += 1

    # The real allocator's failure branch preserves NULL and its varargs ABI.
    label = buffer(64); c.memmove(label, b'GBuffer Target MRT\0', 19)
    heap_name = buffer(16); c.memmove(heap_name, b'XMemGpu\0', 8)
    struct.pack_into('<Q', mem, 0x4edb9a8 + 0x18, heap_name)
    stub(0x18416a0, lambda: label)
    stub(0xe783f0, lambda *args: 0, 5)
    logged = []
    def printf(fmt, heap, resource, size):
        logged.append((c.string_at(fmt), c.string_at(heap), c.string_at(resource), size))
        return 99
    stub(0x2c88338, printf, 4)
    allocate = function(0x1908830, 2)
    assert allocate(33423360, 0x40000000) == 0 and not logged
    site = resolution.writes('4K')[2]
    mem[site['elf_vaddr']:site['elf_vaddr']+5] = bytes.fromhex(site['replacement_hex'])
    assert allocate(33423360, 0x40000000) == 0
    assert logged == [(b'%s alloc "%s" failed: %u bytes\n', b'XMemGpu', b'GBuffer Target MRT', 33423360)], logged

    # Execute real texture creation and render-target view creation. A NULL GPU
    # backing allocation is reported as success upstream, then disables CB_INFO.
    fail_gpu = False
    def alloc(size, flags):
        if flags & 0x3c0000000:
            return 0 if fail_gpu else 0x1088000000
        return buffer(size)
    stub(0x1841630, alloc, 2)
    stub(0x2c88068, lambda p, value, n: (c.memset(p, value, n) or p), 3)
    for address in (0x17961a0, 0x17961d0, 0x17b7cd0, 0x178ee40):
        stub(address, lambda *args: 1, 0)
    callback = c.CFUNCTYPE(c.c_uint64)(lambda: 1); keep.append(callback)
    struct.pack_into('<Q', mem, 0x39f2270, c.cast(callback, c.c_void_p).value)
    create, view, bind = function(0x17b0680, 4), function(0x17b2460, 4), function(0x21364a0, 3)
    pairs = 0
    for fail_gpu in (False, True):
        for width, height in resolution.SIZES.values():
            for fmt in (24, 29, 29):
                desc, view_desc, out, rt = buffer(44), buffer(20), buffer(8), buffer(8)
                c.memmove(desc, struct.pack('<11I', width, height, 1, 1, fmt, 1, 0, 0, 0x28, 0, 0), 44)
                c.memmove(view_desc, struct.pack('<5I', fmt, 4, 0, 0, 0), 20)
                assert create(1, desc, 0, out) & 0xffffffff == 0
                resource = c.c_uint64.from_address(out).value
                assert view(1, resource, view_desc, rt) & 0xffffffff == 0
                target = c.c_uint64.from_address(rt).value + 0x20
                assert bool(c.c_uint32.from_address(target).value) == (not fail_gpu)
                command, words = buffer(40), buffer(256)
                c.c_uint64.from_address(command+8).value = words+256
                c.c_uint64.from_address(command+16).value = words
                bind(command, 0, target)
                used = c.c_uint64.from_address(command+16).value - words
                packet = struct.unpack('<'+'I'*(used//4), c.string_at(words, used))
                if fail_gpu:
                    assert packet == (0xc0016900, 0x31c, 0), packet
                else:
                    assert len(packet) == 15 and packet[0] == 0xc00b6900
                    assert packet[2] != 0 and packet[6] != 0
                pairs += 1
    print(f'PASS: {cases} native heap initializations; failure-log ABI and NULL result; {pairs} texture/view/packet cases. GPU rendering not tested.')


if __name__ == '__main__':
    main(sys.argv[1])
