# SPDX-License-Identifier: GPL-2.0-or-later
"""Link-time compatibility for editions other than the reviewed USA build.

The USA edition needs none of this and its linked image is unchanged. For the European
edition (CUSA01073 v01.00, see docs/EUROPE_EDITION.md) link_modules.py calls apply(), which:

1. Serves imports the host runtime has no implementation for with small guest-code stubs
   (explicit per-edition list; a stub is used only when no native export exists).
2. Emulates the AMD-only SSE4a INSERTQ/EXTRQ instructions (Intel CPUs raise #UD) through
   jump-out trampolines.
3. Moves the System V red-zone locals of listed leaf functions into a real frame: on Windows
   the page-watcher exceptions are dispatched on the guest stack and overwrite the red zone.

Everything lives in one appended code/data page inside the last linked module (the runtime only
accepts bindings inside a module). Original game files and the dump are never modified.
"""
import hashlib
import json
import struct
from pathlib import Path

PAGE = 0x1000

# Imports of the European eboot/libc/libSceFios2 that ratchet-probe does not implement, by library.
# Each returns 0 (SCE_OK / false) unless a special stub is listed in SPECIAL_STUBS. Almost all are
# online (NpToolkit), streaming/recording, error dialogs or PS4 Pro queries, which this offline port
# answers with "not available"; see docs/EUROPE_EDITION.md for the reviewed meanings.
EUROPE_ZERO_STUBS = {
    'libSceDiscMap': ('fJgP+wqifno',),
    'libSceErrorDialog': ('9XAxK2PMwk8', 'I88KChlynSs', 'M2ZF-ClLhgY', 'WWiGuh9XfgQ', 'ekXHb1kDBl0'),
    'libSceGameLiveStreaming': ('9yK6Fk8mKOQ', 'dWM80AX39o4', 'kvYEw2lBndk'),
    'libSceNpToolkit': (
        '+vlPLHD00To', '-yX6wn3uxtY', '0S1VPE7USx4', '3Ek9odpk9YA', '6Elq8JRcABo', '6q0KZ62Ok1s',
        '7wRBEcZoyPI', '8goZrMdh1-U', 'AnVgmQj3yRg', 'BIqPNz1T+t4', 'CNfDCtPLzso', 'CczSTwBcdxE',
        'CdobpaGS6WU', 'DTe15BBYXDs', 'DsQPfdyTiv8', 'EaNyI3eRq7k', 'FObJjOlF5qo', 'Fa9J7ngbX6c',
        'GAiEhgDtJWQ', 'GHQulEstteY', 'Hx8cvWyMdqI', 'KX7EOXJ2sU0', 'Kh8dZZS0u0k', 'LBPuue9NRXo',
        'MBYc6kmK11g', 'NhDcICYJo24', 'OD56nOZAtdU', 'P4z5uq2vHzk', 'PC5Gpw2wImU', 'QCzOmgxL95I',
        'RGA+5Ya-Qv8', 'ROOoy-+hydE', 'S0xHRXabnnA', 'S3Et4iyZ0K0', 'S3trkSjQj1I', 'SDCKr+PlzXs',
        'SLxNhwWCSJE', 'SNQKcoMZwaU', 'UOU5c7dyzPM', 'UVHQ5QOlN1s', 'XY21x3P2TtM', 'YL7i9hQ-9Hw',
        'YqDiZtP2g-U', 'ZmbMDphkqqM', 'arB3rFJIChI', 'c59ADTvHxOg', 'cIYAby4aWvw', 'cbpbhWr1RmU',
        'ceQ-P-FXwXY', 'ch1gPt3APgk', 'cmT0DEnAAHE', 'fEx7+E0w-cA', 'fc+ZCcOOA9U', 'gQ3aL+5g6t8',
        'gXrGIfpK+Rw', 'jpA+IcvGLJQ', 'jqCAI6-i5F4', 'kUzZ7TNCxMw', 'kn0-k32rPJE', 'lqeZJNlw8C4',
        'm+3cpksNpBg', 'mG2BEWS7I6U', 'olxGqGZ5egA', 'pWFx2bo5OuQ', 'qfPu91qDeRM', 's+uku3je12E',
        'sZdEKjVwJfQ', 'tDpnyx0AidQ', 'tO+MzKT6aLU', 'trPXDKRnszQ', 'uPbKbN7X5B4', 'uc-MH98BJo8',
        'uiOi3D5osbI', 'utSFHQbm8+I', 'v2dS6RrHRZg', 'vHGVN2bUMfM', 'vOA3a52SjWo', 'vuEwc1lpJ-U',
        'xKF1H20+f3c', 'xMdAAKfBCAQ', 'xWDZ0jzZbgg', 'yrRz1HggR4s', 'zkg+kaBk8Dw', 'zqsgWAHMGy0'),
    'libScePosix': ('FN4gaPmuFV8', 'VAzswvTOCzI', 'ih4CD9-gghM'),
    'libSceVideoRecording': ('Fc8qxlKINYQ',),
    'libkernel': ('-YTW+qXc3CQ', 'WslcK1FQcGI', 'yDBwVAolDgg'),  # WslcK1FQcGI: sceKernelIsNeoMode -> base PS4
}
# (library, NID) -> stub name in guest_code().
EUROPE_SPECIAL_STUBS = {
    ('libSceLibcInternalExt', 'NWtTN10cJzE'): 'heap_trace',     # sceLibcHeapGetTraceInfo (as shadPS4)
    ('libSceSaveData', '0z45PIH+SNI'): 'savedata_mount2',       # sceSaveDataMount2 -> sceSaveDataMount
}
# (library, NID) -> a NID#library the runtime knows for the same function (same arguments).
# ratchet-probe implements these by name but its NID table only lists the older SDK's NIDs.
EUROPE_IMPORT_ALIASES = {
    ('libSceSaveData', 'TywrFKCoLGY'): 'ZkZhskCPXFw#libSceSaveData',   # Initialize3 -> Initialize
}
# Runtime functions the guest stubs call through a pointer slot in the data page.
SAVEDATA_MOUNT = '32HQAQdwM2o#libSceSaveData'   # sceSaveDataMount(const Mount1 *, MountResult *)
MOUNT_SLOT = 0x300                              # data page offset (after the heap-trace statics)
# Leaf functions that keep locals in the red zone and run while page watchers fault.
EUROPE_REDZONE_FUNCTIONS = (
    (0x178d500, 0x178d6a0),   # animation/skinning job: crashed at 0x178d667 / 0x178d681
)


def guest_code(code_at, data_at):
    """Shared stub code (bytes) and {stub name: image address} for a page at code_at."""
    code, names = bytearray(), {}
    names['heap_trace'] = code_at + len(code)
    # HeapInfoInfo{u64 size; u32 flag; u32 getSegmentInfo; u64 *mask; u64 *mstate_table}
    start = code_at + len(code)
    code += bytes.fromhex('c7470c00000000')                                    # mov dword [rdi+0xc], 0
    code += bytes.fromhex('488d05') + struct.pack('<i', data_at - (start + 14))       # lea rax, mask (u64)
    code += bytes.fromhex('48894710')                                          # mov [rdi+0x10], rax
    code += bytes.fromhex('488d05') + struct.pack('<i', data_at + 8 - (start + 25))   # lea rax, table (u64[64])
    code += bytes.fromhex('48894718')                                          # mov [rdi+0x18], rax
    code += bytes.fromhex('31c0c3')                                            # xor eax, eax; ret
    # sceSaveDataMount2(const Mount2 *m, MountResult *r): the runtime's Mount2 is Mount with no
    # title, so build Mount1{user, title=NULL, dir, fingerprint=NULL, blocks, mode} on the stack
    # and call sceSaveDataMount through the data-page slot. Mount2: user@0 dir@8 blocks@16 mode@24.
    names['savedata_mount2'] = code_at + len(code)
    code += bytes.fromhex('4885ff')                                            # test rdi, rdi
    jz_at = len(code)
    code += bytes.fromhex('7400')                                              # jz parameter_error (below)
    code += bytes.fromhex('4883ec58')                                          # sub rsp, 88 (Mount1 + align)
    code += bytes.fromhex('4889f8')                                            # mov rax, rdi
    code += bytes.fromhex('488b08' '48890c24')                                 # [rsp] = user, pad
    code += bytes.fromhex('48c744240800000000')                                # [rsp+8] = title NULL
    code += bytes.fromhex('488b4808' '48894c2410')                             # [rsp+16] = dir
    code += bytes.fromhex('48c744241800000000')                                # [rsp+24] = fingerprint NULL
    code += bytes.fromhex('488b4810' '48894c2420')                             # [rsp+32] = blocks
    code += bytes.fromhex('8b4818' '48894c2428')                               # [rsp+40] = mode (zero-extended)
    for offset in (0x30, 0x38, 0x40, 0x48):                                    # reserved and padding = 0
        code += bytes.fromhex('48c74424') + bytes([offset]) + bytes(4)
    code += bytes.fromhex('4889e7')                                            # mov rdi, rsp (rsi = result)
    call_at = code_at + len(code)
    code += bytes.fromhex('ff15') + struct.pack('<i', data_at + MOUNT_SLOT - (call_at + 6))  # call [slot]
    code += bytes.fromhex('4883c458' 'c3')                                     # add rsp, 88; ret
    code[jz_at + 1] = len(code) - (jz_at + 2)
    code += bytes.fromhex('b800009f80' 'c3')                                   # parameter_error: eax = 0x809F0000
    names['zero'] = code_at + len(code)
    code += bytes.fromhex('31c0c3')                                            # xor eax, eax; ret
    return code, names


def sse4a_sites(image, code_segments, cache):
    """Immediate-form INSERTQ/EXTRQ in the given code: [(address, length, kind, dst, src, bits, index)].

    Register forms and sites with a branch into their middle are left alone (reported).
    The scan is cached by the digest of the scanned code.
    """
    digest = hashlib.sha256(b''.join(bytes(image[a:a + s]) for a, s in code_segments)).hexdigest()
    try:
        cached = json.loads(Path(cache).read_text())
        if cached.get('sha256') == digest:
            return [tuple(site) for site in cached['sites']]
    except (OSError, ValueError):
        pass
    try:
        from iced_x86 import Decoder, FlowControl, Mnemonic, OpKind, RegisterExt
    except ImportError:
        print('SSE4a: iced_x86 unavailable; INSERTQ/EXTRQ left unpatched', flush=True)
        return []
    sites, targets = [], set()
    for address, size in code_segments:
        for ins in Decoder(64, bytes(image[address:address + size]), ip=address):
            if ins.flow_control in (FlowControl.UNCONDITIONAL_BRANCH, FlowControl.CONDITIONAL_BRANCH,
                                    FlowControl.CALL) and ins.op0_kind == OpKind.NEAR_BRANCH64:
                targets.add(ins.near_branch_target)
            if ins.mnemonic == Mnemonic.INSERTQ and ins.op_count == 4:
                sites.append((ins.ip, ins.len, 'INSERTQ', RegisterExt.number(ins.op_register(0)),
                              RegisterExt.number(ins.op_register(1)), ins.immediate8, ins.immediate8_2nd))
            elif ins.mnemonic == Mnemonic.EXTRQ and ins.op_count == 3:
                sites.append((ins.ip, ins.len, 'EXTRQ', RegisterExt.number(ins.op_register(0)), 0,
                              ins.immediate8, ins.immediate8_2nd))
            elif ins.mnemonic in (Mnemonic.INSERTQ, Mnemonic.EXTRQ):
                print(f'SSE4a: register form at {ins.ip:#x} not emulated', flush=True)
    usable = [s for s in sites if s[1] >= 5 and not any(s[0] < t < s[0] + s[1] for t in targets)]
    try:
        Path(cache).write_text(json.dumps(dict(sha256=digest, sites=usable)))
    except OSError:
        pass
    return usable


def sse4a_trampoline(at, site):
    """Guest code emulating one immediate INSERTQ/EXTRQ, placed at image address `at`.

    Uses rax/rcx/rdx and flags, all restored below the 128-byte red zone; keeps the destination's
    upper 64 bits (pinsrq). Ends with a jump back after the original instruction.
    """
    address, length, kind, dst, src, bits, index = site
    mask = ((1 << (bits or 64)) - 1) << index & 0xFFFFFFFFFFFFFFFF

    def movq_from_xmm(xmm, gpr):   # movq gpr, xmm
        return bytes([0x66, 0x48 | (4 if xmm >= 8 else 0), 0x0F, 0x7E, 0xC0 | (xmm & 7) << 3 | gpr])
    code = bytearray(bytes.fromhex('488d642480' '9c' '50' '51' '52'))  # lea rsp,[rsp-128]; pushfq; push rax/rcx/rdx
    code += movq_from_xmm(dst, 0)                                       # rax = dst[63:0]
    code += bytes.fromhex('48ba') + struct.pack('<Q', mask)             # rdx = field mask
    if kind == 'INSERTQ':
        code += movq_from_xmm(src, 1)                                   # rcx = src[63:0]
        code += bytes.fromhex('48c1e1') + bytes([index])                # shl rcx, index
        code += bytes.fromhex('4821d1' '48f7d2' '4821d0' '4809c8')      # and rcx,rdx; not rdx; and rax,rdx; or rax,rcx
    else:
        code += bytes.fromhex('4821d0')                                 # and rax, rdx
        code += bytes.fromhex('48c1e8') + bytes([index])                # shr rax, index
    code += bytes([0x66, 0x48 | (4 if dst >= 8 else 0), 0x0F, 0x3A, 0x22, 0xC0 | (dst & 7) << 3, 0])  # pinsrq dst, rax, 0
    code += bytes.fromhex('5a' '59' '58' '9d' '488da42480000000')       # pop rdx/rcx/rax; popfq; lea rsp,[rsp+128]
    code += b'\xe9' + struct.pack('<i', address + length - (at + len(code) + 5))
    return bytes(code)


def redzone_plan(image, start, end):
    """Plan moving a leaf function's red-zone locals above rsp, or None when its shape is unexpected.

    Returns ((prologue address, length), frame size, [(disp8 byte address, new disp8)],
    (epilogue address, length)): prologue = leading register pushes, epilogue = trailing pops + ret.
    """
    from iced_x86 import Decoder, FlowControl, Mnemonic, OpKind, Register
    code = list(Decoder(64, bytes(image[start:end]), ip=start))
    ret_index = next((i for i, ins in enumerate(code) if ins.mnemonic == Mnemonic.RET), None)
    if ret_index is None:
        return None
    body = code[:ret_index + 1]
    pushes = 0
    while body[pushes].mnemonic == Mnemonic.PUSH and body[pushes].op0_kind == OpKind.REGISTER:
        pushes += 1
    pops = ret_index
    while pops > 0 and body[pops - 1].mnemonic == Mnemonic.POP and body[pops - 1].op0_kind == OpKind.REGISTER:
        pops -= 1
    if not pushes or ret_index - pops != pushes:
        return None
    lowest, refs = 0, []
    for ins in body[pushes:pops]:
        if ins.flow_control in (FlowControl.CALL, FlowControl.RETURN, FlowControl.INDIRECT_BRANCH):
            return None                                      # not a leaf with a single exit
        if any(ins.op_kind(i) == OpKind.REGISTER and ins.op_register(i) in (Register.RSP, Register.ESP)
               for i in range(ins.op_count)):
            return None                                      # rsp changed inside the body
        if any(ins.op_kind(i) == OpKind.MEMORY for i in range(ins.op_count)) and ins.memory_base == Register.RSP:
            disp = ins.memory_displacement
            disp -= (1 << 64) if disp >= 1 << 63 else 0
            if ins.memory_index != Register.NONE or ins.memory_displ_size != 1 or disp >= 0:
                return None
            lowest = min(lowest, disp)
            refs.append((ins, disp))
    if not refs:
        return None
    frame = (-lowest + 15) & ~15
    fixes = []
    for ins, disp in refs:
        raw = bytes(image[ins.ip:ins.next_ip])
        if raw[-1] != disp & 0xFF or not -128 <= disp + frame <= 127:
            return None                                      # displacement is not the last byte
        fixes.append((ins.next_ip - 1, (disp + frame) & 0xFF))
    prologue = (start, body[pushes].ip - start)
    epilogue = (body[pops].ip, body[ret_index].next_ip - body[pops].ip)
    if prologue[1] < 5 or epilogue[1] < 5:
        return None
    for ins in body:                                         # no jump into the replaced bytes
        if ins.flow_control in (FlowControl.UNCONDITIONAL_BRANCH, FlowControl.CONDITIONAL_BRANCH) \
                and ins.op0_kind == OpKind.NEAR_BRANCH64:
            t = ins.near_branch_target
            if start < t < start + prologue[1] or epilogue[0] < t < epilogue[0] + epilogue[1]:
                return None
    return prologue, frame, fixes, epilogue


class Compat:
    """One edition's link-time fixes."""

    def __init__(self, name, zero_stubs, special_stubs, redzone_functions, sse4a=True, aliases=None):
        self.name, self.zero_stubs, self.special_stubs = name, zero_stubs, special_stubs
        self.redzone_functions, self.sse4a = redzone_functions, sse4a
        self.aliases = aliases or {}

    def stub_names(self):
        """(library, NID) -> stub name, for every import this edition serves with guest code."""
        names = {(lib, nid): 'zero' for lib, nids in self.zero_stubs.items() for nid in nids}
        names.update(self.special_stubs)
        return names

    def apply(self, image, segments, base, main_code, out):
        """Append a data page and the stub/trampoline code at `base` (64 KiB aligned), patch the main
        image in memory and add both segments.

        Returns ({(library, NID): image address} of the stubs, [(slot address, NID#library)] of the
        runtime functions the stubs call; the caller relocates each slot to that import).
        """
        data_at, code_at = base, base + PAGE
        code, names = guest_code(code_at, data_at)
        jumps, redzone = [], []
        for site in (sse4a_sites(image, main_code, Path(out) / 'sse4a-sites.json') if self.sse4a else ()):
            at = code_at + len(code)
            code += sse4a_trampoline(at, site)
            jumps.append((site, at))
        for start, end in self.redzone_functions:
            plan = redzone_plan(image, start, end)
            if plan is None:
                print(f'Red zone: function {start:#x} not patched (unexpected shape)', flush=True)
                continue
            (p_at, p_len), frame, fixes, (e_at, e_len) = plan
            entry = code_at + len(code)
            code += bytes(image[p_at:p_at + p_len])                         # original pushes
            code += bytes.fromhex('4881ec') + struct.pack('<I', frame)      # sub rsp, frame
            code += b'\xe9' + struct.pack('<i', p_at + p_len - (code_at + len(code) + 5))
            exit_at = code_at + len(code)
            code += bytes.fromhex('4881c4') + struct.pack('<I', frame)      # add rsp, frame
            code += bytes(image[e_at:e_at + e_len])                         # original pops + ret
            redzone.append((plan, entry, exit_at))
        code_size = (len(code) + PAGE - 1) & ~(PAGE - 1)
        if code_at + code_size > 512 * 1024 * 1024:
            raise ValueError('linked image exceeds probe limit')
        image.extend(bytes(code_at + code_size - len(image)))
        image[code_at:code_at + len(code)] = code
        for (address, length, *_), at in jumps:
            image[address:address + length] = b'\xe9' + struct.pack('<i', at - (address + 5)) + b'\x90' * (length - 5)
        for ((p_at, p_len), frame, fixes, (e_at, e_len)), entry, exit_at in redzone:
            for address, disp in fixes:
                image[address] = disp
            image[p_at:p_at + p_len] = b'\xe9' + struct.pack('<i', entry - (p_at + 5)) + b'\x90' * (p_len - 5)
            image[e_at:e_at + e_len] = b'\xe9' + struct.pack('<i', exit_at - (e_at + 5)) + b'\xcc' * (e_len - 5)
            print(f'Red zone: function {p_at:#x} locals moved into a {frame}-byte frame ({len(fixes)} accesses)',
                  flush=True)
        segments.append((data_at, PAGE, 6))        # R+W: heap-trace statics
        segments.append((code_at, code_size, 5))   # R+X: stubs and trampolines
        if jumps:
            print(f'SSE4a: {len(jumps)} INSERTQ/EXTRQ sites redirected to emulation', flush=True)
        stubs = {key: names[name] for key, name in self.stub_names().items()}
        slots = [(data_at + MOUNT_SLOT, SAVEDATA_MOUNT)] if 'savedata_mount2' in self.special_stubs.values() else []
        return stubs, slots


EUROPE = Compat('europe', EUROPE_ZERO_STUBS, EUROPE_SPECIAL_STUBS, EUROPE_REDZONE_FUNCTIONS,
                aliases=EUROPE_IMPORT_ALIASES)
COMPAT = {'europe': EUROPE}


def compat_for(game):
    """The Compat of a game folder's edition, or None (USA and unknown dumps: unchanged)."""
    from editions import edition, title_of
    record = edition(title_of(game))
    return COMPAT.get(record['compat']) if record and record.get('compat') else None
