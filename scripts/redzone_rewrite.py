"""Move the red zone of guest functions above RSP (Windows).

The PS4 code follows the SysV ABI: leaf functions keep data in the 128 bytes below RSP (the red
zone), which signal delivery never touches. Windows has no red zone. When a guest thread takes an
exception (the GPU page tracking write-protects guest memory and resolves the access violation),
KiUserExceptionDispatcher writes the exception frame right below RSP and destroys that data.
In Ratchet & Clank this corrupts the CPU skinning (spiky, flickering animated meshes) and crashes
the job workers (write to 0x54 at guest offset 0x1830a81).

Every function that addresses memory below RSP is relocated into a blob loaded after the image.
The copy runs 256 bytes lower: `lea rsp,[rsp-256]` on entry, every RSP-relative operand +256,
push/pop become lea+mov at the original slots and `lea rsp,[rsp+256]` precedes every exit. All stack
data keeps its original address (pointers into the frame stay valid) but now lies above RSP; 256
keeps the low byte of RSP, so even the flags of `add/sub rsp` stay identical. The loader writes a
`jmp rel32` at each original entry whose bytes still match (CRC32). Functions this rewrite cannot
move (jump tables, calls, indirect branches) are left alone; IN_PLACE_FIXES covers the ones that
fault in practice (RATCHET_FAULT_SITES=1 lists the faulting guest addresses).

Usage: redzone_rewrite.py out/boot-linked.bin --out out
Writes <out>/redzone.bin: 'RZP1', u32 version, u64 blob offset, u32 blob size, u32 count,
count x {u64 function offset, u32 size, u32 crc32, u32 blob entry}, blob,
then 'RZB1', u32 count, count x {u64 offset, u32 length, old bytes, new bytes}.
"""
import argparse
import binascii
from pathlib import Path
import struct
import sys
from prepare import span, unpack
from isa_rewrite import read_boot_linked
try:
    import iced_x86
    from iced_x86 import BlockEncoder, Code, Decoder, FlowControl, Instruction, MemoryOperand, Mnemonic, OpKind, Register
except ImportError:
    iced_x86 = None

SHIFT = 256
RSP_FAMILY = ('RSP', 'ESP', 'SP', 'SPL')
FAKE_IP = 0x7F00_0000_0000
# CUSA01047 v1.00: the vertex skinning loop (function 0x1836f20) keeps its position scale in
# [rsp-0x18] and writes the GPU-visible vertex buffer, so nearly every frame takes a write fault
# inside the loop. It has a jump table (not relocatable); its two stack arguments ([rsp+8],
# [rsp+0x10]) are read on entry, and that callee-owned, 16-byte aligned area holds the scale instead.
IN_PLACE_FIXES = [
    (0x1836f7e, bytes.fromhex('c5f8294424e8'), bytes.fromhex('c5f829442408')),  # vmovaps [rsp-0x18] -> [rsp+8], xmm0
    (0x1836ff9, bytes.fromhex('c5f8284424e8'), bytes.fromhex('c5f828442408')),  # vmovaps xmm0, [rsp-0x18] -> [rsp+8]
]


class Skip(Exception):
    pass


def eh_frame_tables(image, segments):
    """Function (start, size) pairs from every .eh_frame_hdr binary search table in the image."""
    executable = [(a, a + s) for a, s, f in segments if f & 1]
    in_code = lambda x: any(lo <= x < hi for lo, hi in executable)
    functions = {}
    pos = image.find(b'\x01\x1b\x03\x3b')
    while pos >= 0:
        count, = unpack('<I', image, pos + 8)
        if 0 < count < 1_000_000 and pos + 12 + 8 * count <= len(image):
            table = [struct.unpack_from('<ii', image, pos + 12 + 8 * i) for i in range(count)]
            starts = [pos + a for a, _ in table]
            if starts == sorted(starts) and all(in_code(s) for s in starts):
                for (a, b) in table:
                    fde = pos + b
                    if 0 <= fde + 16 <= len(image):
                        size, = unpack('<I', image, fde + 12)
                        if 0 < size < 0x100000:
                            functions[pos + a] = size
        pos = image.find(b'\x01\x1b\x03\x3b', pos + 1)
    return sorted(functions.items())


def is_rsp(reg):
    return reg in (Register.RSP, Register.ESP, Register.SP, Register.SPL)


def signed(x):
    return x - (1 << 64) if x >= (1 << 63) else x


def uses_red_zone(code, start):
    for i in Decoder(64, code, ip=start):
        for k in range(i.op_count):
            if i.op_kind(k) == OpKind.MEMORY and i.memory_base == Register.RSP and signed(i.memory_displacement) < 0:
                return True
    return False


def stack_effect(i):
    m = i.mnemonic
    if m in (Mnemonic.PUSH, Mnemonic.POP):
        if i.op_kind(0) == OpKind.MEMORY or (i.op_kind(0) == OpKind.REGISTER and is_rsp(i.op0_register)):
            raise Skip('push/pop with memory or rsp operand')
        return i.stack_pointer_increment
    if m in (Mnemonic.PUSHFQ, Mnemonic.POPFQ, Mnemonic.PUSHF, Mnemonic.POPF, Mnemonic.ENTER, Mnemonic.LEAVE):
        raise Skip('pushf/popf/enter/leave')
    for k in range(i.op_count):
        if i.op_kind(k) == OpKind.REGISTER and is_rsp(i.op_register(k)):
            if k == 0 and i.op0_register == Register.RSP and m in (Mnemonic.SUB, Mnemonic.ADD) and \
                    i.op_kind(1) in (OpKind.IMMEDIATE8TO64, OpKind.IMMEDIATE32TO64):
                return -i.immediate(1) if m == Mnemonic.SUB else i.immediate(1)
            if k == 0 and i.op0_register == Register.RSP and m == Mnemonic.LEA and \
                    i.memory_base == Register.RSP and i.memory_index == Register.NONE:
                return signed(i.memory_displacement)
            raise Skip('rsp used as a register operand')
        if i.op_kind(k) == OpKind.MEMORY and is_rsp(i.memory_index):
            raise Skip('rsp as an index')
    return 0


def rewrite(code, start):
    """The relocated instructions of one function (iced Instructions for BlockEncoder)."""
    end = start + len(code)
    ins = []
    for i in Decoder(64, code, ip=start):
        if i.code == Code.INVALID:
            raise Skip('data in code (jump table)')
        ins.append(i)
    if not ins or ins[-1].next_ip != end:
        raise Skip('decoding does not end at the function end')
    index = {i.ip: k for k, i in enumerate(ins)}
    inside = lambda t: start <= t < end
    for i in ins:
        fc = i.flow_control
        if fc in (FlowControl.CALL, FlowControl.INDIRECT_CALL, FlowControl.INDIRECT_BRANCH, FlowControl.INTERRUPT):
            raise Skip('call, indirect branch or interrupt')
        if fc in (FlowControl.UNCONDITIONAL_BRANCH, FlowControl.CONDITIONAL_BRANCH) and \
                inside(i.near_branch_target) and i.near_branch_target not in index:
            raise Skip('branch into an instruction')
    if ins[-1].flow_control not in (FlowControl.RETURN, FlowControl.UNCONDITIONAL_BRANCH):
        raise Skip('does not end with ret or jmp')
    # Stack depth at every reachable instruction; exits must leave at depth 0.
    depth = [None] * len(ins)
    depth[0] = 0
    work = [0]
    while work:
        k = work.pop()
        i, d = ins[k], depth[k]
        nd = d + stack_effect(i)
        fc = i.flow_control
        succ = []
        if fc == FlowControl.RETURN:
            if d:
                raise Skip('ret with a nonzero stack depth')
        elif fc in (FlowControl.UNCONDITIONAL_BRANCH, FlowControl.CONDITIONAL_BRANCH):
            t = i.near_branch_target
            if inside(t):
                succ.append(index[t])
            elif d:
                raise Skip('exit jump with a nonzero stack depth')
            if fc == FlowControl.CONDITIONAL_BRANCH:
                succ.append(k + 1)
        else:
            if k + 1 >= len(ins):
                raise Skip('falls off the end')
            succ.append(k + 1)
        for s in succ:
            if depth[s] is None:
                depth[s] = nd
                work.append(s)
            elif depth[s] != nd:
                raise Skip('inconsistent stack depth')

    fake = [FAKE_IP + start * 16]
    def fresh():
        fake[0] += 1
        return fake[0]
    def lea_rsp(delta, ip):
        x = Instruction.create_reg_mem(Code.LEA_R64_M, Register.RSP,
                                       MemoryOperand(Register.RSP, displ=delta, displ_size=1 if -128 <= delta < 128 else 8))
        x.ip = ip
        return x
    def slot():
        return MemoryOperand(Register.RSP, displ=SHIFT, displ_size=8)

    out = [lea_rsp(-SHIFT, fresh())]   # internal branches to the start skip it
    stubs = []
    for k, i in enumerate(ins):
        if depth[k] is None:           # unreachable padding
            out.append(i.copy())
            continue
        m, fc = i.mnemonic, i.flow_control
        if m == Mnemonic.PUSH:
            out.append(lea_rsp(-8, i.ip))
            if i.code == Code.PUSH_R64:
                x = Instruction.create_mem_reg(Code.MOV_RM64_R64, slot(), i.op0_register)
            elif i.code in (Code.PUSHQ_IMM32, Code.PUSHQ_IMM8):
                x = Instruction.create_mem_i32(Code.MOV_RM64_IMM32, slot(), signed(i.immediate(0)))
            else:
                raise Skip('unsupported push')
            x.ip = fresh()
            out.append(x)
            continue
        if m == Mnemonic.POP:
            if i.code != Code.POP_R64:
                raise Skip('unsupported pop')
            x = Instruction.create_reg_mem(Code.MOV_R64_RM64, i.op0_register, slot())
            x.ip = i.ip
            out += [x, lea_rsp(8, fresh())]
            continue
        x = i.copy()
        if not (x.op_count and x.op_kind(0) == OpKind.REGISTER and x.op0_register == Register.RSP):
            for o in range(x.op_count):
                if x.op_kind(o) == OpKind.MEMORY and x.memory_base == Register.RSP:
                    disp = signed(x.memory_displacement)
                    if disp < -128:
                        raise Skip('access below the red zone')
                    disp += SHIFT
                    x.memory_displacement = disp & ((1 << 64) - 1)
                    x.memory_displ_size = 1 if -128 <= disp < 128 else 8
                    break
        if fc == FlowControl.RETURN or (fc == FlowControl.UNCONDITIONAL_BRANCH and not inside(i.near_branch_target)):
            out.append(lea_rsp(SHIFT, i.ip))   # branches to the exit run the restore first
            x.ip = fresh()
        elif fc == FlowControl.CONDITIONAL_BRANCH and not inside(i.near_branch_target):
            stub = fresh()
            stubs.append((stub, i.near_branch_target))
            x.near_branch64 = stub
        out.append(x)
    for stub, target in stubs:
        j = Instruction.create_branch(Code.JMP_REL32_64, target)
        j.ip = fresh()
        out += [lea_rsp(SHIFT, stub), j]
    return out


def build(image, segments, blob_off):
    blob = bytearray()
    entries, skipped = [], {}
    for start, size in eh_frame_tables(image, segments):
        code = span(image, start, size)
        if not uses_red_zone(code, start):
            continue
        try:
            instructions = rewrite(code, start)
        except Skip as e:
            skipped[start] = str(e)
            continue
        encoder = BlockEncoder(64)
        encoder.add_many(instructions)
        piece = encoder.encode(blob_off + len(blob))
        entries.append((start, size, binascii.crc32(code), len(blob)))
        blob += piece
        blob += b'\xcc' * (-len(blob) % 16)
    return entries, bytes(blob), skipped


def encode(entries, blob, blob_off, fixes):
    parts = [b'RZP1', struct.pack('<IQII', 1, blob_off, len(blob), len(entries))]
    parts += [struct.pack('<QIII', *e) for e in entries]
    parts += [blob, b'RZB1', struct.pack('<I', len(fixes))]
    parts += [struct.pack('<QI', off, len(old)) + old + new for off, old, new in fixes]
    return b''.join(parts)


def main(argv):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('boot', type=Path)
    p.add_argument('--out', type=Path, default=Path(__file__).resolve().parent.parent / 'out')
    a = p.parse_args(argv)
    try:
        if iced_x86 is None:
            raise RuntimeError('iced_x86 is not installed')
        segments, image = read_boot_linked(a.boot.read_bytes())
        # After the image and room for the ISA rewrite stubs; rel32 reaches it from any function.
        blob_off = ((len(image) + 0xfffff) & ~0xfffff) + 0x800000
        entries, blob, skipped = build(image, segments, blob_off)
        fixes = [f for f in IN_PLACE_FIXES if span(image, f[0], len(f[1])) == f[1]]
        (a.out / 'redzone.bin').write_bytes(encode(entries, blob, blob_off, fixes))
    except (OSError, ValueError, RuntimeError) as e:
        print(f'Red zone: rewrite unavailable ({e})')
        return 1
    print(f'Red zone: {len(entries)} functions relocated, {len(skipped)} left in place, '
          f'{len(fixes)} in-place fixes, {len(blob)} bytes')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
