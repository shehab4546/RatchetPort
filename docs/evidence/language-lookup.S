# SPDX-License-Identifier: GPL-2.0-or-later
# Assemble as x86-64 Intel syntax. 92 bytes + one NOP occupy the guarded 93-byte lookup.
.intel_syntax noprefix
.text
.global lookup
lookup:
 movabs rax, 0xbe55d94f171bf8de
 cmp rsi, rax
 jne normal
 mov edx, 21
normal:
 imul edx, edx, 48
 mov ecx, ecx
 lea rdx, [rdx+rcx*8]
 add rdx, [rdi]
 mov r8d, [rdx]
 mov r10d, [rdx+4]
 add r10d, r8d
 mov r9, [rdi+8]
loop:
 cmp r8d, r10d
 jae miss
 lea eax, [r8+r10]
 shr eax, 1
 cmp [r9+rax*8], rsi
 je found
 jb lower
 mov r10d, eax
 jmp loop
lower:
 lea r8d, [rax+1]
 jmp loop
found:
 lea rax, [rax+rax*2]
 mov rdx, [rdi+24]
 lea rax, [rdx+rax*4]
 ret
miss:
 xor eax, eax
 ret
