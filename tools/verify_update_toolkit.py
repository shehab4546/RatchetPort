#!/usr/bin/env python3
"""Isolated USA 1.09 NP Toolkit link/constructor checks; no gameplay or network.

Run on Linux x86-64 with AVX support. Uses locally supplied game files; none are
included here. Only __cxa_atexit is intercepted during the native module init;
any other external call terminates the check instead of returning fake success.
"""
import argparse
import ctypes as C
import hashlib
import json
import mmap
import os
from pathlib import Path
import platform
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from link_modules import canonical, module
from ratchet_game import BUILD_FINGERPRINTS, UPDATE_TOOLKIT_SHA256


def verify(game, linked):
    if sys.platform != 'linux' or platform.machine() not in ('x86_64', 'AMD64'):
        raise RuntimeError('Native verification requires Linux x86-64')
    if ' avx ' not in Path('/proc/cpuinfo').read_text().replace('\n', ' '):
        raise RuntimeError('Native verification requires AVX')
    main = module(game / 'eboot.bin')
    native = module(game / 'sce_module/libSceNpToolkit.prx')
    assert main['sha256'] == BUILD_FINGERPRINTS[('CUSA01047', '01.09')][0]
    assert native['sha256'] == UPDATE_TOOLKIT_SHA256
    raw = linked.read_bytes()
    magic, size, _, ns, nr, ni, _ = struct.unpack_from('<8s6Q', raw)
    assert magic == b'G3PROBE5'
    nm = struct.unpack_from('<Q', raw, 96)[0]
    mods = [struct.unpack_from('<7Q', raw, 104 + i * 56) for i in range(nm)]
    assert nm == 3 and [m[6] for m in mods] == [2, 3, 4]
    nb = struct.unpack_from('<Q', raw, 104 + nm * 56)[0]
    pos = 112 + nm * 56
    bindings = dict((i, (addr, kind)) for i, addr, kind in
                    (struct.unpack_from('<3Q', raw, pos + n * 24) for n in range(nb)))
    pos += nb * 24 + ns * 24
    names = [raw[pos + i * 128:pos + (i + 1) * 128].split(b'\0')[0].decode() for i in range(ni)]
    pos += ni * 128
    relocs = [struct.unpack_from('<QQqq', raw, pos + i * 32) for i in range(nr)]
    image_at = pos + nr * 32
    assert len(raw) == image_at + size
    base, _, init, tls, memsz, filesz, tls_id = mods[2]
    assert init == base and (memsz, filesz, tls_id) == (8, 0, 4)
    tls_target = next(t for t, k, _, _ in native['relocs'] if k == 16)
    assert struct.unpack_from('<Q', raw, image_at + base + tls_target)[0] == 4
    exports = {s['identity']: s for s in native['symbols'] if s['identity'] and s['section']}
    imports = [s for s in main['symbols'] if s['identity'] and not s['section']
               and s['identity'][1][0] == 'libSceNpToolkit']
    assert len(imports) == 84
    for s in imports:
        index = names.index(canonical(s['identity']))
        assert bindings[index] == (base + exports[s['identity']]['value'], 1)
        assert any(k == 1 and v == index for _, k, v, _ in relocs)

    # Relocate the actual module independently, exercising its initializer and
    # the constructor that stopped the Windows run. External services are traps.
    loads = [p for p in native['ph'] if p['type'] in (1, 0x61000010)]
    length = max(p['vaddr'] + p['memsz'] for p in loads)
    mem = mmap.mmap(-1, length, prot=mmap.PROT_READ | mmap.PROT_WRITE | mmap.PROT_EXEC)
    address = C.addressof(C.c_char.from_buffer(mem))
    for p in loads:
        mem[p['vaddr']:p['vaddr'] + p['filesz']] = native['elf'][p['offset']:p['offset'] + p['filesz']]
    registrations = []
    callbacks = []
    @C.CFUNCTYPE(C.c_int, C.c_void_p, C.c_void_p, C.c_void_p)
    def register(destructor, obj, dso):
        registrations.append((destructor, obj, dso))
        return 0
    def trap(name):
        @C.CFUNCTYPE(C.c_uint64)
        def called():
            os.write(2, f'Unexpected external call: {name}\n'.encode())
            os._exit(70)
        callbacks.append(called)
        return C.cast(called, C.c_void_p).value
    for target, kind, symid, addend in native['relocs']:
        s = native['symbols'][symid]
        if kind == 8:
            value = address + addend
        elif kind == 16:
            value = 4
        elif kind in (1, 7):
            if s['section']:
                value = (0 if s['section'] == 0xfff1 else address) + s['value'] + addend
            elif s['binding'] == 2 and not s['identity']:
                value = 0
            else:
                name = canonical(s['identity'])
                value = (C.cast(register, C.c_void_p).value
                         if name == 'tsvEmnenz48#libSceLibcInternal' else trap(name)) + addend
        else:
            raise AssertionError(f'Unexpected relocation kind {kind}')
        struct.pack_into('<Q', mem, target, value)
    result = C.CFUNCTYPE(C.c_int, C.c_uint64, C.c_void_p, C.c_void_p)(address)(0, None, None)
    assert result == 0 and len(registrations) == 3
    assert all(address <= v < address + length for row in registrations for v in row)
    key = ('7wRBEcZoyPI', ('libSceNpToolkit', 1), ('libSceNpToolkit', 0))
    ctor = C.CFUNCTYPE(None, C.c_void_p)(address + exports[key]['value'])
    # The real constructor clears a 144-byte object. Check both boundaries and
    # unaligned storage, as the native code uses unaligned vector writes.
    for offset in (16, 17, 31):
        buf = C.create_string_buffer(b'\xa5' * 192, 192)
        ctor(C.addressof(buf) + offset)
        assert buf.raw == b'\xa5' * offset + bytes(144) + b'\xa5' * (192 - offset - 144)
    mem.close()
    return {'toolkit_sha256': native['sha256'], 'linked_sha256': hashlib.sha256(raw).hexdigest(),
            'toolkit_imports_bound': len(imports), 'native_bindings': nb, 'tls_module': tls_id,
            'initializer_result': result, 'destructors_registered': len(registrations),
            'constructor_boundary_cases': 3,
            'scope': 'Native module initialization and constructor only; no gameplay, rendering or PSN'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game-dir', type=Path, required=True)
    parser.add_argument('--linked', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.output and (args.output.exists() or
                       args.output.resolve().is_relative_to(args.game_dir.resolve())):
        parser.error('Use a new output file outside the game folder')
    result = verify(args.game_dir, args.linked)
    text = json.dumps(result, indent=2) + '\n'
    if args.output:
        args.output.write_text(text)
    print(text, end='')
