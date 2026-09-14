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
"""The Spectrum interpreter, assembled and run for real.

sjasmplus builds it and ZEsarUX runs it headless; the test then reads the
screen out of the emulator's memory and decodes it back into text using the
adventure's own font.  Nothing here trusts the assembly: if a glyph lands on
the wrong address, the comparison fails.
"""

import json
import os
import subprocess
import sys

try:
    import pytest
except ImportError:
    pytest = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import emulator  # noqa: E402
from regac.binary import S_FONT, Database, Reader  # noqa: E402

SPECTRUM = os.path.join(ROOT, "z80", "spectrum")
SOURCE = os.path.join(SPECTRUM, "main.asm")
DATABASE = os.path.join(SPECTRUM, "game.rgac")
SNAPSHOT = os.path.join(SPECTRUM, "out.sna")
ADVENTURE = os.path.join(ROOT, "snapshots", "megacorp2.json")

TEXT_THIRD = 0x5000  # the screen third the text window lives in
WINDOW_ROWS = 8
COLUMNS = 32
MESSAGES_PRINTED = 6

if pytest is not None:
    needs_tools = pytest.mark.skipif(
        not emulator.available() or not os.path.exists(ADVENTURE),
        reason="sjasmplus and ZEsarUX must be in tools/, with a decompiled adventure",
    )
else:

    def needs_tools(func):
        return func


def load_adventure():
    with open(ADVENTURE, encoding="utf-8") as f:
        return json.load(f)


def build():
    """Make the database and the snapshot the emulator will run."""
    subprocess.run(
        [sys.executable, "-m", "regac", "build", ADVENTURE, DATABASE, "-m", "spectrum48"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return emulator.assemble(SOURCE)


def glyph_table(database):
    """Every glyph of the font, against the character it draws, so the screen
    can be read back as text."""
    font = Reader(database.build()).section(S_FONT)
    first, count = font[0], font[1]
    table = {}
    for index in range(count):
        glyph = bytes(font[2 + index * 8 : 10 + index * 8])
        table.setdefault(glyph, database.store.charset.chars[first + index])
    return table


def decode_screen(memory, glyphs):
    """Turn the pixels of the text window back into lines of text."""
    lines = []
    for row in range(WINDOW_ROWS):
        line = ""
        for column in range(COLUMNS):
            cell = bytes(memory[line_ * 256 + row * 32 + column] for line_ in range(8))
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
def test_the_spectrum_prints_what_the_database_holds():
    ddb = load_adventure()
    listing = build()
    finished, (memory,) = emulator.run(
        SNAPSHOT, listing, reads=[(TEXT_THIRD, 2048)]
    )
    assert finished, "the interpreter never reached the end of its run"

    database = Database(ddb)
    lines = decode_screen(memory, glyph_table(database))
    expected = wrapped(database.texts[:MESSAGES_PRINTED])
    # The window holds the last few lines; the final one is blank because the
    # cursor moved on after the last message.
    visible = [line for line in lines if line]
    assert visible == expected[-len(visible) :]
    assert len(visible) >= 5, "hardly anything was printed"


if __name__ == "__main__":
    test_the_spectrum_prints_what_the_database_holds()
    print("the Spectrum build prints what it should")
