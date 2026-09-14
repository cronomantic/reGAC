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
"""An MSX adventure off a cassette, loaded the way a person would load it.

The machine is given the tape and the order that starts it -- `BLOAD"CAS:",R`
and nothing else -- and from there nobody helps: the ROM reads the interpreter
into the thirty two kilobytes it can reach, starts it, and the interpreter
reads the database itself, a chunk at a time, taking the machine back for each
one because the BIOS is in the way of where the bytes have to go.

What is checked is that the database arrived whole and that the adventure is
then playing, which is the only proof that the chunks went where they were
meant to.
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
from regac.binary import Database  # noqa: E402
from regac.media import MSX_CHUNK, MSX_MARKER, msx_tape  # noqa: E402
from test_game_msx import build, glyph_table, wait_screen  # noqa: E402

MSX = os.path.join(ROOT, "z80", "msx")
DATABASE = os.path.join(MSX, "game.rgac")
BINARY = os.path.join(MSX, "game.bin")
TAPE = os.path.join(MSX, "game.cas")
ADVENTURE = os.path.join(ROOT, "snapshots", "megacorp2.json")

BLOAD = 'BLOAD"CAS:",R' + chr(13)
DB_AT = 0x0000

if pytest is not None:
    needs_tools = pytest.mark.skipif(
        not emulator.available() or not os.path.exists(ADVENTURE),
        reason="sjasmplus and ZEsarUX must be in tools/, with a decompiled adventure",
    )
else:

    def needs_tools(func):
        return func


def tape_of(code, database):
    with open(TAPE, "wb") as f:
        f.write(msx_tape(code, database))
    return TAPE


def blocks(tape):
    """Where each block of a cassette starts, which is where its marker is."""
    found, at = [], 0
    while True:
        at = tape.find(MSX_MARKER, at)
        if at < 0:
            return found
        found.append(at + len(MSX_MARKER))
        at += len(MSX_MARKER)


def test_the_tape_is_the_shape_a_machine_reads():
    """Two blocks for the interpreter, which is a file and has a name, and a
    block of its own for each chunk of the database, which is not."""
    code = bytes(range(256)) * 8
    database = bytes(range(251)) * 100                  # 25100, four chunks
    tape = msx_tape(code, database, load=0x8000)
    at = blocks(tape)
    assert len(at) == 2 + 4
    assert all(place % 8 == 0 for place in at), "a marker is not on an eighth byte"
    assert tape[at[0]:at[0] + 10] == bytes([0xD0]) * 10
    assert tape[at[0] + 10:at[0] + 16] == b"GAME  "
    assert tape[at[1]:at[1] + 6] == bytes(
        [0x00, 0x80, 0xFF, 0x87, 0x00, 0x80]                # where, to, and start
    )
    assert tape[at[1] + 6:at[1] + 6 + len(code)] == code
    # The first chunk is headed by the size of the whole, and nothing else is.
    assert tape[at[2]:at[2] + 2] == bytes([len(database) & 0xFF, len(database) >> 8])
    assert tape[at[2] + 2:at[2] + 2 + MSX_CHUNK] == database[:MSX_CHUNK]
    assert tape[at[5]:at[5] + len(database) % MSX_CHUNK] == database[3 * MSX_CHUNK:]


@needs_tools
def test_an_adventure_loads_off_a_cassette_and_plays():
    with open(ADVENTURE, encoding="utf-8") as f:
        ddb = json.load(f)
    build()
    with open(BINARY, "rb") as f:
        code = f.read()
    with open(DATABASE, "rb") as f:
        database = f.read()
    glyphs = glyph_table(Database(ddb, machine="msx"))
    prompt = ddb["messages"]["240"].strip()[:3]

    session = emulator.Session(machine="MSX1",
                               extra=["--tape", tape_of(code, database)])
    try:
        time.sleep(10.0)                # the ROM has its own things to do first
        session.msx_type(BLOAD)
        opening = wait_screen(session, glyphs, prompt, timeout=120.0)
        landed = bytes(session.read(DB_AT, len(database)))
    finally:
        session.close()

    assert landed == database, (
        "the database off the tape is not the database that was built: "
        f"{sum(a != b for a, b in zip(landed, database))} bytes differ"
    )
    assert any(prompt in line for line in opening if line), (
        f"it never got as far as asking: {opening}"
    )


if __name__ == "__main__":
    test_the_tape_is_the_shape_a_machine_reads()
    print("the tape is the shape a machine reads")
    test_an_adventure_loads_off_a_cassette_and_plays()
    print("and an adventure loads off it and plays")
