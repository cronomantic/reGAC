# MIT License
#
# Copyright (c) 2025 Cronomantic
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
"""Save a rendered picture as a PNG, so pictures can be checked without
starting the interpreter.  Written by hand to keep the tools free of
dependencies."""

import struct
import zlib

from .gfx import CHAR_WIDTH, PICTURE_ROWS, SCREEN_WIDTH

SPECTRUM_PALETTE = [
    0x000000, 0x0100CE, 0xCF0100, 0xCF01CE,
    0x00CF15, 0x01CFCF, 0xCFCF15, 0xCFCFCF,
    0x000000, 0x0200FD, 0xFF0201, 0xFF02FD,
    0x00FF1C, 0x02FFFF, 0xFFFF1D, 0xFFFFFF,
]


def to_rgb(picture, palette=None):
    """Turn a picture into rows of (r, g, b) tuples."""
    palette = palette or SPECTRUM_PALETTE
    rows = []
    for y in range(PICTURE_ROWS):
        row = []
        for x in range(SCREEN_WIDTH):
            attr = picture.attrs[(y >> 3) * CHAR_WIDTH + (x >> 3)]
            bright = 8 if (attr >> 6) & 1 else 0
            lit = (picture.pixels[y * CHAR_WIDTH + (x >> 3)] >> (7 - (x & 7))) & 1
            colour = palette[((attr & 7) if lit else ((attr >> 3) & 7)) + bright]
            row.append(((colour >> 16) & 0xFF, (colour >> 8) & 0xFF, colour & 0xFF))
        rows.append(row)
    return rows


def write(path, rows, scale=2):
    """Write rows of (r, g, b) tuples to a PNG file."""
    height = len(rows)
    width = len(rows[0]) if height else 0
    raw = bytearray()
    for row in rows:
        line = bytearray([0])  # no per line filter
        for red, green, blue in row:
            line += bytes((red, green, blue)) * scale
        raw += line * scale

    def chunk(tag, data):
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    header = struct.pack(">IIBBBBB", width * scale, height * scale, 8, 2, 0, 0, 0)
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
        f.write(chunk(b"IHDR", header))
        f.write(chunk(b"IDAT", zlib.compress(bytes(raw), 9)))
        f.write(chunk(b"IEND", b""))


def save_picture(path, picture, scale=2, palette=None):
    write(path, to_rgb(picture, palette), scale)
