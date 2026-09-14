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
"""The whole interpreter playing a real adventure on an MSX1.

The machine is taken whole -- RAM in all four pages, the BIOS out of the way
-- so that the database has somewhere to live, and that is what makes loading
it here a two step affair: nothing outside the machine can write under the
BIOS until the interpreter itself has switched, so the build waits for a word
that the database is in place.  Off a cassette it never waits, because the
loader put it there first.

What is checked is the whole of it: the switch, the database where the BIOS
was, the screen in the video chip, the keyboard without a BIOS to scan it, the
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
from regac.devices import MSX_COLOURS, MSX_PATTERNS, MSX_PICTURE_BYTES  # noqa: E402
from regac.devices import MsxDevice  # noqa: E402
from regac.gfx import Renderer  # noqa: E402
from test_keyboard_msx import EVENTS, type_them  # noqa: E402

MSX = os.path.join(ROOT, "z80", "msx")
SOURCE = os.path.join(MSX, "game.asm")
DATABASE = os.path.join(MSX, "game.rgac")
BINARY = os.path.join(MSX, "game.bin")
LISTING = os.path.join(MSX, "game.lst")
ADVENTURE = os.path.join(ROOT, "snapshots", "megacorp2.json")

CODE_AT = 0x8000
VRAM = 24  # the emulator's name for the video chip's own memory
TEXT_TOP = 16  # the picture takes the sixteen rows above
TEXT_ROWS = 8
COLUMNS = 32
ROW_BYTES = 256
ENTER = chr(13)
NOT_UNDERSTOOD = "242"  # the message GAC prints when a word means nothing

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
        [sys.executable, "-m", "regac", "build", ADVENTURE, DATABASE, "-m", "msx"],
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


def decode_screen(patterns, glyphs):
    """The text window, out of the video chip's pattern table.  A cell is its
    eight bytes one after another, which is what makes printing cheap here."""
    lines = []
    for row in range(TEXT_ROWS):
        line = ""
        for column in range(COLUMNS):
            at = row * ROW_BYTES + column * 8
            line += glyphs.get(bytes(patterns[at:at + 8]), "?")
        lines.append(line.rstrip())
    return lines


def screen(session, glyphs):
    # The text is the third block of the table, past the picture's two.
    patterns = session.read(MSX_PATTERNS + MSX_PICTURE_BYTES,
                            TEXT_ROWS * ROW_BYTES, zone=VRAM)
    return decode_screen(patterns, glyphs)


def wait_screen(session, glyphs, wanted, timeout=90.0):
    """Let it play until those letters show up, and give back the screen.  A
    room draws its picture before it says anything, and a picture is seconds,
    so waiting a fixed while is waiting either too little or too long."""
    deadline = time.time() + timeout
    lines = screen(session, glyphs)
    while time.time() < deadline:
        lines = screen(session, glyphs)
        if any(wanted in line for line in lines if line):
            return lines
        time.sleep(1.0)
    return lines


def start_playing(session, where, database):
    """Put the interpreter in, let it take the machine, and hand it the
    database once there is somewhere to put it."""
    with open(BINARY, "rb") as f:
        blob = f.read()
    for at in range(0, len(blob), 512):
        session.command(
            f"write-memory-raw {CODE_AT + at} " + blob[at:at + 512].hex().upper()
        )
    session.command(f"write-memory-raw {where['database_ready']} 00")
    session.command(f"set-register PC={where['start']:04X}H")
    time.sleep(0.5)  # it switches to all RAM and waits for the word
    for at in range(0, len(database), 512):
        piece = database[at:at + 512]
        session.command(f"write-memory-raw {at} " + piece.hex().upper())
    assert bytes(session.read(0, 4)) == b"RGAC", "the database never landed"
    session.command(f"write-memory-raw {where['database_ready']} 01")


@needs_tools
def test_it_asks_and_answers_on_an_msx():
    with open(ADVENTURE, encoding="utf-8") as f:
        ddb = json.load(f)
    listing = build()
    where = {name: emulator.label_address(listing, name)
             for name in ("start", "database_ready", "done_flag")}
    with open(DATABASE, "rb") as f:
        database = f.read()
    built = Database(ddb, machine="msx")
    glyphs = glyph_table(built)
    prompt = ddb["messages"]["240"].strip()[:3]
    puzzled = ddb["messages"][NOT_UNDERSTOOD]

    session = emulator.Session(machine="MSX1")
    try:
        time.sleep(7.0)
        start_playing(session, where, database)
        opening = wait_screen(session, glyphs, prompt)
        assert any(prompt in line for line in opening if line), (
            f"the interpreter never asked: {opening}"
        )

        # A word the adventure does not know, so it has to say so.
        type_them(session, "XYZZY" + ENTER)
        answered = wait_screen(session, glyphs, puzzled[:6], timeout=30.0)

        room = ddb["locations"][str(ddb["init_loc"])]["graphic_id"]
        drawn = (bytes(session.read(MSX_PATTERNS, MSX_PICTURE_BYTES, zone=VRAM)),
                 bytes(session.read(MSX_COLOURS, MSX_PICTURE_BYTES, zone=VRAM)))
    finally:
        session.close()

    assert answered != opening, "typing changed nothing on screen"
    assert any("XYZZY" in line for line in answered), (
        f"what was typed never showed up: {answered}"
    )
    assert any(puzzled[:6] in line for line in answered), (
        f"expected {puzzled!r} somewhere in {answered}"
    )
    assert drawn == Renderer(ddb["gfx"], MsxDevice()).run(int(room)).vram(), (
        f"the picture of room {ddb['init_loc']} is not the one the reference draws"
    )


if __name__ == "__main__":
    test_it_asks_and_answers_on_an_msx()
    print("the MSX build plays")
