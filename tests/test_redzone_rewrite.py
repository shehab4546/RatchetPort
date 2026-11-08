"""Relocation of red-zone functions (Windows has no SysV red zone)."""
from paths import ROOT
import struct
import unittest
import redzone_rewrite as rz

try:
    from iced_x86 import BlockEncoder, Decoder, Formatter, FormatterSyntax
except ImportError:
    BlockEncoder = None

# push rbx; mov [rsp-0x10], rdi; lea rax, [rsp-0x10]; mov rax, [rax]; mov ecx, [rsp+0x10]; pop rbx; ret
LEAF = bytes.fromhex('53' '48897c24f0' '488d4424f0' '488b00' '8b4c2410' '5b' 'c3')
# mov [rsp-8], rdi; test edi, edi; je 0x1000 (outside); ret
COND_EXIT = bytes.fromhex('48897c24f8' '85ff' '0f84' + struct.pack('<i', 0x1000 - 0x400d).hex() + 'c3')
CALLS = bytes.fromhex('48897c24f8' 'e800000000' 'c3')       # mov [rsp-8], rdi; call; ret
JUMP_TABLE = bytes.fromhex('48897c24f8' 'ffe0' 'c3')         # mov [rsp-8], rdi; jmp rax; ret


def text(instructions, start=0x5a00000):
    encoder = BlockEncoder(64)
    encoder.add_many(instructions)
    code = encoder.encode(start)
    fmt = Formatter(FormatterSyntax.INTEL)
    return [fmt.format(i) for i in Decoder(64, code, ip=start)]


@unittest.skipUnless(BlockEncoder, 'pip install iced-x86')
class RewriteTests(unittest.TestCase):
    def test_leaf_runs_256_bytes_lower_with_slots_at_their_original_addresses(self):
        self.assertTrue(rz.uses_red_zone(LEAF, 0x4000))
        lines = text(rz.rewrite(LEAF, 0x4000))
        self.assertEqual(lines[0], 'lea rsp,[rsp-100h]')
        self.assertEqual(lines[1:3], ['lea rsp,[rsp-8]', 'mov [rsp+100h],rbx'])     # push rbx
        self.assertEqual(lines[3], 'mov [rsp+0F0h],rdi')                            # was [rsp-10h]
        self.assertEqual(lines[4], 'lea rax,[rsp+0F0h]')                            # pointer into the frame
        self.assertEqual(lines[6], 'mov ecx,[rsp+110h]')                            # caller frame, was [rsp+10h]
        self.assertEqual(lines[7:9], ['mov rbx,[rsp+100h]', 'lea rsp,[rsp+8]'])     # pop rbx
        self.assertEqual(lines[9:11], ['lea rsp,[rsp+100h]', 'ret'])

    def test_conditional_exit_goes_through_a_restore_stub(self):
        lines = text(rz.rewrite(COND_EXIT, 0x4000))
        self.assertEqual(lines[-2], 'lea rsp,[rsp+100h]')
        self.assertTrue(lines[-1].startswith('jmp 0000000000001000h'))
        self.assertIn('lea rsp,[rsp+100h]', lines[:-2])  # before the ret

    def test_calls_and_indirect_branches_are_left_alone(self):
        for code in (CALLS, JUMP_TABLE):
            with self.assertRaises(rz.Skip):
                rz.rewrite(code, 0x4000)

    def test_functions_without_red_zone_are_not_selected(self):
        self.assertFalse(rz.uses_red_zone(bytes.fromhex('488b442408c3'), 0x4000))  # mov rax, [rsp+8]; ret

    def test_file_layout(self):
        data = rz.encode([(0x4000, len(LEAF), 0x1234, 0)], b'\xcc' * 16, 0x5a00000,
                         [(0x4001, b'\xe8', b'\x08')])
        self.assertEqual(data[:4], b'RZP1')
        self.assertEqual(struct.unpack_from('<IQII', data, 4), (1, 0x5a00000, 16, 1))
        self.assertEqual(struct.unpack_from('<QIII', data, 24), (0x4000, len(LEAF), 0x1234, 0))
        trailer = data[24 + 20 + 16:]
        self.assertEqual(trailer[:8], b'RZB1' + struct.pack('<I', 1))
        self.assertEqual(trailer[8:], struct.pack('<QI', 0x4001, 1) + b'\xe8\x08')


if __name__ == '__main__':
    unittest.main()
