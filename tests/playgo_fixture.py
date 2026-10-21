"""Synthetic PlayGo metadata only; contains no extracted game data."""
import struct


def playgo_bytes(chunks=3):
    data = bytearray(256 + chunks * 32)
    struct.pack_into('<IHHHHHHI', data, 0, 0x6F676C70, 1, 0, 1, chunks, 0, 0, len(data))
    struct.pack_into('<II', data, 192, 256, chunks * 32)
    return bytes(data)
