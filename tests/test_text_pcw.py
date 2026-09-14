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
"""The PCW interpreter printing, assembled and run for real.

The same check as the Spectrum's and the Amstrad's: the screen is read out of
the emulator and decoded back into text with the adventure's own font, so
nothing is taken on trust.

Two things are this machine's own.  A glyph is eight bytes in a row, because
the eight lines of a byte column sit together, which makes printing cheaper
here than anywhere else; and it goes down inside out, because the text is
black on white paper, as everything on a PCW was.  More is printed than fits,
so the window has to scroll, which is the one part of this screen that drawing
a picture never touches.
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

PCW = os.path.join(ROOT, "z80", "pcw")
SOURCE = os.path.join(PCW, "main.asm")
DATABASE = os.path.join(PCW, "text.rgac")
BINARY = os.path.join(PCW, "text.bin")
LISTING = os.path.join(PCW, "text.lst")
ADVENTURE = os.path.join(ROOT, "snapshots", "megacorp2.json")

LOADS_AT = 0x0100
SCREEN = 0x8000
ROW_BYTES = 720
MARGIN = 13  # columns to the left of the text, as of the picture
COLUMNS = 64
WINDOW_ROWS = 16
MESSAGES_PRINTED = 20

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
        [sys.executable, "-m", "regac", "build", ADVENTURE, DATABASE, "-m", "pcw"],
        cwd=ROOT,
        check=True,
        capture_output=True,
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


def decode_screen(memory, glyphs):
    """Turn the pixels of the text window back into lines of text.

    A character cell is the eight bytes at row * 720 + (margin + column) * 8,
    and what is on the screen is the glyph turned inside out.
    """
    lines = []
    for row in range(WINDOW_ROWS):
        line = ""
        for column in range(COLUMNS):
            at = row * ROW_BYTES + (MARGIN + column) * 8
            cell = bytes(memory[at + n] ^ 0xFF for n in range(8))
            line += glyphs.get(cell, "?")
        lines.append(line.rstrip())
    return lines


def wrapped(texts, width=COLUMNS):
    """What the printing should come to, breaking between words."""
    out = []
    for text in texts:
        line = ""
        for word in text.split(" "):
            if line and len(line) + len(word) > width:
                out.append(line.rstrip())
                line = ""
            line += word + " "
        out.append(line.rstrip())
    return out


@needs_tools
def test_the_pcw_prints_what_the_database_holds():
    with open(ADVENTURE, encoding="utf-8") as f:
        ddb = json.load(f)
    listing = build()
    done = emulator.label_address(listing, "done_flag")
    with open(BINARY, "rb") as f:
        blob = f.read()

    session = emulator.Session(machine="PCW8256")
    try:
        time.sleep(4.0)  # let the machine ask for a disk
        finished = session.start_code(blob, LOADS_AT, done)
        memory = session.read(SCREEN, WINDOW_ROWS * ROW_BYTES)
    finally:
        session.close()
    assert finished, "the interpreter never reached the end of its run"

    database = Database(ddb, machine="pcw")
    lines = decode_screen(memory, glyph_table(database))
    expected = wrapped(database.texts[:MESSAGES_PRINTED])
    visible = [line for line in lines if line]
    assert len(expected) > WINDOW_ROWS, "this did not print enough to scroll"
    assert visible == expected[-len(visible):]
    assert len(visible) >= 10, "hardly anything was printed"


if __name__ == "__main__":
    test_the_pcw_prints_what_the_database_holds()
    print("the PCW build prints what it should")
