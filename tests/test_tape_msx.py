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
meant to.  And, with a loading screen on the tape, that it is up on the screen
while the rest of it is still coming in.
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
from regac.devices import MSX_PICTURE_BYTES, MsxDevice  # noqa: E402
from regac.gfx import Renderer  # noqa: E402
from regac.media import MSX_BSAVE, MSX_CHUNK, MSX_MARKER  # noqa: E402
from regac.media import MSX_SCREEN_BYTES, msx_screen, msx_tape  # noqa: E402
from test_game_msx import build, glyph_table, wait_screen  # noqa: E402

MSX = os.path.join(ROOT, "z80", "msx")
DATABASE = os.path.join(MSX, "game.rgac")
BINARY = os.path.join(MSX, "game.bin")
TAPE = os.path.join(MSX, "game.cas")
ADVENTURE = os.path.join(ROOT, "snapshots", "megacorp2.json")

BLOAD = 'BLOAD"CAS:",R' + chr(13)
DB_AT = 0x0000
VRAM = 24                       # the emulator's name for the video chip's own

# What a loading screen is made of, in the order the chip keeps it: six
# kilobytes of patterns, the names that turn those into a bitmap, the sprites,
# and six kilobytes of colours.
VRAM_NAMES = 0x1800
VRAM_SPRITES = 0x1B00
VRAM_COLOURS = 0x2000

# The screen is in the chip long before the adventure is playing -- it comes
# in front of the database, which is two thirds of the tape -- so it is looked
# for while the rest is still being read, and it is gone once the game starts
# printing and drawing over it.
SCREEN_TIMEOUT = 60.0

if pytest is not None:
    needs_tools = pytest.mark.skipif(
        not emulator.available() or not os.path.exists(ADVENTURE),
        reason="sjasmplus and ZEsarUX must be in tools/, with a decompiled adventure",
    )
else:

    def needs_tools(func):
        return func


def tape_of(code, database, screen=None):
    with open(TAPE, "wb") as f:
        f.write(msx_tape(code, database, screen))
    return TAPE


def a_screen(ddb, room):
    """A loading screen as the chip holds it: the picture of a room in the
    patterns and the colours, the name table that makes those a bitmap, and
    the sprites told there are none.  The eight rows the text uses are left
    black, which is what a real one would do with them."""
    patterns, colours = Renderer(ddb["gfx"], MsxDevice()).run(room).vram()
    text_rows = VRAM_NAMES - MSX_PICTURE_BYTES
    screen = (bytes(patterns) + bytes(text_rows)
              + bytes(range(256)) * 3
              + bytes([0xD0]) + bytes(VRAM_COLOURS - VRAM_SPRITES - 1)
              + bytes(colours) + bytes(text_rows))
    assert len(screen) == MSX_SCREEN_BYTES
    return screen


def wait_for_screen(session, wanted, timeout=SCREEN_TIMEOUT):
    """Watch the video chip until the loading screen is all there, and give
    back what it held.  Looking is the only way: the screen goes in while the
    tape is still running and the adventure paints over it when it starts, so
    a fixed wait would be too early or too late."""
    deadline = time.time() + emulator.longer(timeout)
    while True:
        shown = bytes(session.read(0, MSX_SCREEN_BYTES, zone=VRAM))
        if shown == wanted or time.time() > deadline:
            return shown
        time.sleep(0.2)


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
    # The first chunk is headed by what is coming, and nothing else is.
    head = bytes([len(database) & 0xFF, len(database) >> 8, 0])
    assert tape[at[2]:at[2] + 3] == head, "the first block does not say what follows"
    assert tape[at[2] + 3:at[2] + 3 + MSX_CHUNK] == database[:MSX_CHUNK]
    assert tape[at[5]:at[5] + len(database) % MSX_CHUNK] == database[3 * MSX_CHUNK:]


def test_a_loading_screen_rides_in_front_of_the_first_chunk():
    """It needs no block of its own: it goes straight into the video chip as
    it is read, so stopping the motor for it would buy nothing."""
    code, database = bytes(16), bytes(range(251)) * 100
    screen = bytes(range(256)) * (MSX_SCREEN_BYTES // 256)
    tape = msx_tape(code, database, screen)
    at = blocks(tape)
    assert len(at) == 2 + 4, "the screen took a block of its own"
    assert tape[at[2]:at[2] + 3] == bytes(
        [len(database) & 0xFF, len(database) >> 8, 1]       # and one says it comes
    )
    assert tape[at[2] + 3:at[2] + 3 + MSX_SCREEN_BYTES] == screen
    at_chunk = at[2] + 3 + MSX_SCREEN_BYTES
    assert tape[at_chunk:at_chunk + MSX_CHUNK] == database[:MSX_CHUNK]


def test_a_screen_saved_on_an_msx_is_taken_as_it_comes():
    """A .SC2 is the chip's own memory with a BSAVE header in front of it,
    which is what a person will have, so the header goes and nothing else is
    asked of it."""
    dump = bytes(range(256)) * (MSX_SCREEN_BYTES // 256)
    sc2 = bytes([0xFE, 0x00, 0x00, 0xFF, 0x37, 0x00, 0x00]) + dump
    assert len(sc2) == MSX_SCREEN_BYTES + MSX_BSAVE
    assert msx_screen(sc2) == dump
    assert msx_screen(dump) == dump


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
    screen = a_screen(ddb, int(ddb["locations"]["1"]["graphic_id"]))

    session = emulator.Session(
        machine="MSX1", extra=["--tape", tape_of(code, database, screen)]
    )
    try:
        time.sleep(10.0)                # the ROM has its own things to do first
        session.msx_type(BLOAD)
        shown = wait_for_screen(session, screen)
        opening = wait_screen(session, glyphs, prompt, timeout=120.0)
        landed = bytes(session.read(DB_AT, len(database)))
    finally:
        session.close()

    assert shown == screen, (
        "the loading screen never reached the video chip whole: "
        f"{sum(a != b for a, b in zip(shown, screen))} bytes differ"
    )
    assert landed == database, (
        "the database off the tape is not the database that was built: "
        f"{sum(a != b for a, b in zip(landed, database))} bytes differ"
    )
    assert any(prompt in line for line in opening if line), (
        f"it never got as far as asking: {opening}"
    )


if __name__ == "__main__":
    test_the_tape_is_the_shape_a_machine_reads()
    test_a_loading_screen_rides_in_front_of_the_first_chunk()
    test_a_screen_saved_on_an_msx_is_taken_as_it_comes()
    print("the tape is the shape a machine reads")
    test_an_adventure_loads_off_a_cassette_and_plays()
    print("and an adventure loads off it and plays, with its screen up first")
