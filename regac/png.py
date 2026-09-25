# ReGAC, tools for Graphic Adventure Creator adventures.
#
# Copyright (C) 2025 Cronomantic
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see <https://www.gnu.org/licenses/>.
#
# The interpreters in z80/ are not part of this program and are given under
# the MIT licence instead: see z80/LICENSE.
#
import struct
import zlib

from .i18n import _

SIGNATURE = bytes((137, 80, 78, 71, 13, 10, 26, 10))


def write(path, rows, scale=2):
    """Write rows of (red, green, blue) tuples to a PNG file."""
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
        f.write(SIGNATURE)
        f.write(chunk(b"IHDR", header))
        f.write(chunk(b"IDAT", zlib.compress(bytes(raw), 9)))
        f.write(chunk(b"IEND", b""))


class ImageError(Exception):
    pass


CHANNELS = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}       # grey, rgb, palette, +alpha


def unfilter(raw, height, stride, step):
    """Undo the filter each row of a PNG is written with.

    The five of them are all "this byte, plus one already decoded": the one to
    its left, the one above, the mean of those two, or whichever of three the
    Paeth rule picks.  Nothing here is PNG specific beyond that.
    """
    out = bytearray()
    at = 0
    previous = bytearray(stride)
    for _row in range(height):
        kind, at = raw[at], at + 1
        line = bytearray(raw[at:at + stride])
        at += stride
        for index in range(stride):
            left = line[index - step] if index >= step else 0
            above = previous[index]
            corner = previous[index - step] if index >= step else 0
            if kind == 1:
                line[index] = (line[index] + left) & 0xFF
            elif kind == 2:
                line[index] = (line[index] + above) & 0xFF
            elif kind == 3:
                line[index] = (line[index] + (left + above) // 2) & 0xFF
            elif kind == 4:
                guess = left + above - corner
                da, db, dc = (abs(guess - left), abs(guess - above),
                              abs(guess - corner))
                nearest = left if da <= db and da <= dc else (
                    above if db <= dc else corner)
                line[index] = (line[index] + nearest) & 0xFF
            elif kind:
                raise ImageError(_("a row of this image is filtered with "
                                   "{kind}", kind=kind))
        out += line
        previous = line
    return out


def samples(line, depth, count):
    """The samples of one row, whatever they are packed at: one, two, four,
    eight or sixteen bits each."""
    if depth == 8:
        return list(line[:count])
    if depth == 16:
        return [line[n * 2] for n in range(count)]      # the top half is enough
    out = []
    per_byte = 8 // depth
    mask = (1 << depth) - 1
    for index in range(count):
        byte = line[index // per_byte]
        shift = 8 - depth * (index % per_byte + 1)
        out.append((byte >> shift) & mask)
    return out


def read_image(blob):
    """Read a PNG, and say for every pixel whether it is ink.

    Ink is anything darker than half, and anything see-through is not ink at
    all.  That is all a font needs out of an image, and it means a sheet drawn
    in any two colours works without being asked which is which.
    """
    if blob[:len(SIGNATURE)] != SIGNATURE:
        raise ImageError(_("this is not a PNG"))
    at = len(SIGNATURE)
    width = height = depth = colour = interlace = 0
    palette = alpha = b""
    data = bytearray()
    while at + 8 <= len(blob):
        length = struct.unpack_from(">I", blob, at)[0]
        tag = blob[at + 4:at + 8]
        body = blob[at + 8:at + 8 + length]
        at += 12 + length
        if tag == b"IHDR":
            width, height, depth, colour, _pack, _filter, interlace = struct.unpack(
                ">IIBBBBB", body[:13])
        elif tag == b"PLTE":
            palette = body
        elif tag == b"tRNS":
            alpha = body
        elif tag == b"IDAT":
            data += body
        elif tag == b"IEND":
            break
    if interlace:
        raise ImageError(_("this PNG is interlaced, and this reader is "
                           "not"))
    if colour not in CHANNELS:
        raise ImageError(_("this PNG is of a kind ({colour}) this cannot "
                           "read", colour=colour))
    count = CHANNELS[colour]
    stride = (width * count * depth + 7) // 8
    rows = unfilter(zlib.decompress(bytes(data)), height, stride,
                    max(1, count * depth // 8))
    top = (1 << depth) - 1
    ink = []
    for row in range(height):
        line = rows[row * stride:(row + 1) * stride]
        values = samples(line, depth, width * count)
        for column in range(width):
            piece = values[column * count:(column + 1) * count]
            if colour == 3:
                index = piece[0]
                red, green, blue = palette[index * 3:index * 3 + 3]
                clear = index < len(alpha) and alpha[index] < 128
            elif colour in (0, 4):
                grey = piece[0] * 255 // top
                red = green = blue = grey
                clear = colour == 4 and piece[1] * 255 // top < 128
            else:
                red, green, blue = (v * 255 // top for v in piece[:3])
                clear = colour == 6 and piece[3] * 255 // top < 128
            light = (red * 299 + green * 587 + blue * 114) // 1000
            ink.append(light < 128 and not clear)
    return width, height, ink


def save_picture(path, device, scale=2):
    """Save what a device has been drawn on, whichever machine it models."""
    write(path, device.to_rgb(), scale)
