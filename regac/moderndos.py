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
"""The letters an adventure gets when it brings none of its own.

An adventure off an Amstrad keeps no letters: the Amstrad's GAC printed with
the firmware's, which are in the machine's ROM and not ours to carry.  So it
gets these instead: **Modern DOS 8x8**, by Jayvee Enaguas (HarvettFox96),
version 20190101.02, which is the CGA's letters and is dedicated to the
public domain under CC0 1.0 -- "Released under a libre/free public domain
licence as Creative Commons Zero (CC0) 1.0", as its own source says.  It is
taken from the author's FontForge source, ModernDOS8x8.sfd, in the mirror of
his repository at https://github.com/notpeter/ttf-moderndos.

What is kept here is only the ninety six letters from the space on, eight
bytes a letter, the top row first and the leftmost point in the top bit: the
same dump regac reads for a font of an adventure's own, in
moderndos8x8.bin.  This is where it came from, so that it can be made again:

    python -m regac.moderndos tools/moderndos/ModernDOS8x8.sfd

In the source every point is a square of a hundred units, the top row from
600 to 700 and the bottom one from -100 to 0, and a letter is drawn as
straight outlines; a point is lit when its middle is inside them, counting
by crossings, so that the hole of an A stays a hole.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LETTERS = os.path.join(HERE, "moderndos8x8.bin")
FIRST, LAST = 32, 127           # the space to the last of ASCII
UNIT = 100                      # a point, in the source's units
TOP = 700                       # the top of the top row


def letters():
    """The ninety six letters, as a list of 768 bytes."""
    with open(LETTERS, "rb") as f:
        return list(f.read())


def outlines(sfd):
    """Every character of the source that has a code: code -> its outlines,
    each a list of (x, y) corners."""
    out = {}
    code = None
    shapes = []
    for line in sfd.splitlines():
        words = line.split()
        if line.startswith("Encoding:"):
            code = int(words[2])
            shapes = []
        elif len(words) == 4 and words[2] == "m":
            shapes.append([(int(words[0]), int(words[1]))])
        elif len(words) == 4 and words[2] == "l":
            shapes[-1].append((int(words[0]), int(words[1])))
        elif line.startswith("EndChar") and code is not None:
            out[code] = shapes
            code = None
    return out


def inside(x, y, shapes):
    """Whether (x, y) is inside the outlines, counting crossings."""
    crossings = 0
    for shape in shapes:
        for (x0, y0), (x1, y1) in zip(shape, shape[1:] + shape[:1]):
            if (y0 > y) != (y1 > y):
                at = x0 + (y - y0) * (x1 - x0) / (y1 - y0)
                if at > x:
                    crossings += 1
    return crossings % 2 == 1


def glyph(shapes):
    rows = []
    for row in range(8):
        y = TOP - row * UNIT - UNIT // 2
        byte = 0
        for column in range(8):
            x = column * UNIT + UNIT // 2
            if inside(x, y, shapes):
                byte |= 0x80 >> column
        rows.append(byte)
    return rows


def extract(sfd_path):
    with open(sfd_path, encoding="utf-8") as f:
        drawn = outlines(f.read())
    out = []
    for code in range(FIRST, LAST + 1):
        out += glyph(drawn.get(code, []))
    return bytes(out)


if __name__ == "__main__":
    source = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        HERE, "..", "tools", "moderndos", "ModernDOS8x8.sfd")
    data = extract(source)
    with open(LETTERS, "wb") as f:
        f.write(data)
    print(f"{LETTERS}: {len(data)} bytes")
