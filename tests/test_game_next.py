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
"""The whole interpreter playing a real adventure on a Spectrum Next.

It is started the way a person starts one: the .nex file the assembler writes,
handed to the machine, which loads its banks and jumps in.  Nothing is poked
in from outside.

What is checked is the whole of it: the database in banks that are paged into
the window at $0000, the text in layer 2 where there is no character set and
every letter is sixty four bytes of colour, the Spectrum's own keyboard, the
parser, and the picture the first room draws.
"""

import json
import os
import subprocess
import sys
import time

try:
    import pytest
except ImportError:
    pytest = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import emulator  # noqa: E402
from regac.binary import S_FONT, Database, Reader  # noqa: E402
from regac.devices import next_device  # noqa: E402
from regac.gfx import Renderer  # noqa: E402

NEXT = os.path.join(ROOT, "z80", "next")
SOURCE = os.path.join(NEXT, "game.asm")
DATABASE = os.path.join(NEXT, "game.rgac")
DEFS = os.path.join(NEXT, "banks.inc")
IMAGE = os.path.join(NEXT, "game.nex")
LISTING = os.path.join(NEXT, "game.lst")
ADVENTURE = os.path.join(ROOT, "snapshots", "megacorp2.json")

# Layer 2, in the emulator's own memory: the picture is the first thirty two
# kilobytes of it and the text window the sixteen behind them.
L2_AT = emulator.Session.NEXT_PAGE_0 + 16 * 8192
PICTURE_BYTES = 256 * 128
TEXT_AT = L2_AT + PICTURE_BYTES
TEXT_BYTES = 64 * 256

TEXT_INK = 7                    # what a letter is drawn in, a byte a pixel
TEXT_ROWS = 8
COLUMNS = 32
ENTER = chr(13)
NOT_UNDERSTOOD = "242"          # the message GAC prints when a word means nothing

if pytest is not None:
    needs_tools = pytest.mark.skipif(
        not emulator.available() or not os.path.exists(ADVENTURE),
        reason="sjasmplus and ZEsarUX must be in tools/, with a decompiled adventure",
    )
else:

    def needs_tools(func):
        return func


def build():
    subprocess.run(
        [sys.executable, "-m", "regac", "build", ADVENTURE, DATABASE,
         "-m", "next", "-b", "16k", "--defs", DEFS],
        cwd=ROOT, check=True, capture_output=True,
    )
    return emulator.assemble(SOURCE, listing=LISTING)


def glyph_table(database):
    """Every glyph of the font against the character it draws."""
    font = Reader(database.build()).section(S_FONT)
    first, count = font[0], font[1]
    table = {}
    for index in range(count):
        glyph = bytes(font[2 + index * 8 : 10 + index * 8])
        table.setdefault(glyph, database.store.charset.chars[first + index])
    return table


def decode_screen(text, glyphs):
    """The text window, out of layer 2.  A letter there is not eight bytes of
    bits but sixty four of colour, so the bits are put back together: a pixel
    is lit when it is the ink."""
    lines = []
    for row in range(TEXT_ROWS):
        line = ""
        for column in range(COLUMNS):
            at = row * 8 * 256 + column * 8
            glyph = bytearray()
            for down in range(8):
                bits = 0
                for across in range(8):
                    if text[at + down * 256 + across] == TEXT_INK:
                        bits |= 0x80 >> across
                glyph.append(bits)
            line += glyphs.get(bytes(glyph), "?")
        lines.append(line.rstrip())
    return lines


def screen(session, glyphs):
    return decode_screen(bytes(session.read(TEXT_AT, TEXT_BYTES,
                                            zone=session.RAM)), glyphs)


def wait_screen(session, glyphs, wanted, timeout=90.0):
    """Let it play until those letters show up, and give back the screen."""
    deadline = time.time() + timeout
    lines = screen(session, glyphs)
    while time.time() < deadline:
        lines = screen(session, glyphs)
        if any(wanted in line for line in lines if line):
            return lines
        time.sleep(0.5)
    return lines


@needs_tools
def test_it_asks_and_answers_on_a_next():
    with open(ADVENTURE, encoding="utf-8") as f:
        ddb = json.load(f)
    build()
    built = Database(ddb, machine="next", page_bits=14)
    glyphs = glyph_table(built)
    prompt = ddb["messages"]["240"].strip()[:3]
    puzzled = ddb["messages"][NOT_UNDERSTOOD]

    session = emulator.Session(machine="TBBlue")
    try:
        session.load(IMAGE)
        opening = wait_screen(session, glyphs, prompt)
        assert any(prompt in line for line in opening if line), (
            f"the interpreter never asked: {opening}"
        )

        # A word the adventure does not know, so it has to say so.
        session.type("XYZZY" + ENTER)
        answered = wait_screen(session, glyphs, puzzled[:6], timeout=30.0)

        room = ddb["locations"][str(ddb["init_loc"])]["graphic_id"]
        drawn = bytes(session.read(L2_AT, PICTURE_BYTES, zone=session.RAM))
    finally:
        session.close()

    assert answered != opening, "typing changed nothing on screen"
    assert any("XYZZY" in line for line in answered), (
        f"what was typed never showed up: {answered}"
    )
    assert any(puzzled[:6] in line for line in answered), (
        f"expected {puzzled!r} somewhere in {answered}"
    )
    assert drawn == Renderer(ddb["gfx"], next_device()).run(int(room)).vram(), (
        f"the picture of room {ddb['init_loc']} is not the one the reference draws"
    )


if __name__ == "__main__":
    test_it_asks_and_answers_on_a_next()
    print("the Next build plays")
