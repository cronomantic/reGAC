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
"""Playing the original, and reading what it puts on the screen.

Not a test: this is what a measurement uses when the question is what the
original does, which is the only thing that settles an argument here.  It is
kept because both halves of it took an afternoon to work out.

  - **MegaCorp opens asking for its code**, and the code is not in any manual
    we have but in the adventure itself: its room 5000 takes verb 29, and verb
    29 of its own vocabulary is REBECA.
  - **Its letters are its own**, so the screen is read with the font out of
    its database, whose first character is the code nought.  What made that
    look impossible for a while is the machine and not the adventure: the
    eight pixel lines of a character row are 256 bytes apart and not 32, so
    reading them one after another gives letters sliced into ribbons.

The way to ask it something is the one in doc/pendiente.md: conditions of our
own written over the start of one of its tables, which is found by searching
its memory for the bytes regac compiles from the same adventure.
"""
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import emulator  # noqa: E402

ENTER = chr(13)
PASSWORD = "REBECA"


ENTER = chr(13)
PASSWORD = "REBECA"


def adventure(name="megacorp2"):
    with open(os.path.join(ROOT, "snapshots", name + ".json"),
              encoding="utf-8") as f:
        return json.load(f)


def cells(session):
    """Every character cell of the screen, as eight bytes."""
    screen = bytes(session.read(0x4000, 0x1800))
    out = []
    for row in range(24):
        third, r = divmod(row, 8)
        # the eight pixel lines of a row are 256 bytes apart, not 32: this
        # machine interleaves them, and reading them as if they followed one
        # another gives letters sliced into ribbons
        out.append([bytes(screen[third * 0x800 + line * 0x100 + r * 0x20 + col]
                          for line in range(8))
                    for col in range(32)])
    return out


def reading(ddb, wanted="Ciudad"):
    """A way of turning cells into letters, worked out by trying every first
    character until the text on screen is text we know."""
    font = bytes(ddb.get("font") or [])
    glyphs = [font[i * 8:i * 8 + 8] for i in range(len(font) // 8)]

    def table(first):
        out = {}
        for index, glyph in enumerate(glyphs):
            code = first + index
            if 32 <= code < 127:
                out.setdefault(glyph, chr(code))
        return out

    return table


def text_of(rows, table):
    lines = []
    for row in rows:
        line = "".join(table.get(cell, "?") for cell in row)
        lines.append(line.rstrip())
    return lines


def started(session, name="megacorp2", past_the_code=True, seconds=6.0):
    session.load(os.path.join(ROOT, "snapshots", name + ".sna"))
    time.sleep(seconds)
    if past_the_code:
        session.type(PASSWORD + ENTER)
        time.sleep(4.0)
    return session


if __name__ == "__main__":
    ddb = adventure()
    session = emulator.Session()
    try:
        started(session)
        rows = cells(session)
        table = reading(ddb)
        for first in range(0, 128):
            got = text_of(rows, table(first))
            if any("Ciudad" in line or "CIUDAD" in line for line in got):
                print("the font's first character is", first)
                for line in got:
                    if line.strip("? "):
                        print("  |" + line + "|")
                break
        else:
            print("no first character reads the screen as words")
            print("  cells not blank:",
                  sum(1 for row in rows for c in row if any(c)))
    finally:
        session.close()
