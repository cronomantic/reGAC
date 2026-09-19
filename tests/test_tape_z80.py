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
"""The tape a real Spectrum would load, which is what gets shipped.

A snapshot is a convenience for the tests and nothing a player can use, so
what the build writes is a .tap: a BASIC program carrying the loader in a REM,
and then the blocks with no header in front of them.  Here both tapes are made
and both are loaded in the emulator the way a person would, by typing LOAD "".

The 128 one is where it gets interesting, because its database is in memory
banks and each one travels as its own block that has to land in its own page.
So that tape is made from an adventure fattened until its text and its
pictures cannot share a bank, and what is checked afterwards is not only that
it plays: the picture on the screen is compared byte by byte against the
reference renderer, which it can only match if every block went where it
belonged.  The filler is random letters on purpose, because anything
repetitive the packer would squeeze back down to nothing.
"""

import json
import os
import random
import subprocess
import sys
import tempfile
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
from regac.devices import SpectrumDevice  # noqa: E402
from regac.gfx import Renderer  # noqa: E402
from test_game_z80 import glyph_table, screen, wait_screen  # noqa: E402

SPECTRUM = os.path.join(ROOT, "z80", "spectrum")
ADVENTURE = os.path.join(ROOT, "snapshots", "Bangkok1.json")

ENTER = chr(13)
NOT_UNDERSTOOD = "242"
# What this adventure does when it opens, which is its own doing: it says who
# wrote it, waits for a key and goes to the airport.  The room it starts in is
# never described -- see played() below.
OPENS_WITH = "FABIAN"
LANDS_ROOM = 15
LANDS_IN = "aeropuerto"
PICTURE_ROWS = 128
BYTES_ACROSS = 32
ATTRIBUTES = 0x5800

# Loading a tape takes tape time even hurried along, so the emulator is told
# to hurry it as far as it will.
TAPE_FLAGS = ["--fastautoload", "--simulaterealloadfast"]

if pytest is not None:
    needs_tools = pytest.mark.skipif(
        not emulator.available() or not os.path.exists(ADVENTURE),
        reason="sjasmplus and ZEsarUX must be in tools/, with a decompiled adventure",
    )
else:

    def needs_tools(func):
        return func


def wait_change(session, glyphs, before, timeout=30.0):
    """Let it play until the screen is not what it was."""
    deadline = time.time() + emulator.longer(timeout)
    while time.time() < deadline:
        time.sleep(0.5)
        now = [line for line in screen(session, glyphs)]
        if now != before:
            return now
    return before


def screen_address(row, column):
    return ((row & 0xC0) << 5) + ((row & 7) << 8) + ((row & 0x38) << 2) + column


def fattened():
    """The adventure with filler messages, so that its text and its pictures
    cannot fit in one bank together."""
    with open(ADVENTURE, encoding="utf-8") as f:
        ddb = json.load(f)
    messages = ddb["messages"]
    letters = sorted({c for m in messages.values() for c in m if c.isalpha()})
    filler = random.Random(7)
    for number in range(256):
        if str(number) not in messages:
            messages[str(number)] = "".join(filler.choice(letters) for _ in range(60))
    return ddb


def defined(path):
    """What the build told the assembler."""
    out = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            if " equ " in line:
                name, value = line.split(" equ ")
                out[name.strip()] = int(value)
    return out


def written(ddb):
    """The adventure as a file of its own, for the build to read."""
    folder = tempfile.mkdtemp()
    path = os.path.join(folder, "adventure.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(ddb, f)
    return path


def build(source, database, machine, source_asm, listing, banks=None, defs=None,
          defines=()):
    order = [sys.executable, "-m", "regac", "build", source, database, "-m", machine]
    if banks:
        order += ["-b", banks, "--defs", defs]
    subprocess.run(order, cwd=ROOT, check=True, capture_output=True)
    return emulator.assemble(source_asm, listing=listing, defines=defines)


def played(tape, ddb, glyphs, machine, opens_with, lands_in):
    """Load the tape as a person would, let it get as far as asking for an
    order, and then talk to it.  Gives back the screen it drew.

    What this adventure does when it opens is its own business and not the
    interpreter's: from its high priority table it says its piece, waits for a
    key and goes elsewhere.  The room it opens in is never described, because
    the interpreter looks at that table before paying what a new room is owed
    -- which is how the original does it, measured, and what MegaCorp relies on
    to describe the room it opens in from its own condition.  So what says it
    has arrived is the adventure's own line, and the picture to look at is the
    one of the room its condition sends the player to.
    """
    prompt = ddb["messages"]["240"].strip()[:3]
    puzzled = ddb["messages"][NOT_UNDERSTOOD]
    session = emulator.Session(machine=machine, extra=TAPE_FLAGS)
    try:
        session.load(tape)
        opening = wait_screen(session, glyphs, opens_with, timeout=120.0)
        assert any(opens_with in line for line in opening), (
            f"the adventure never said its piece: {opening}"
        )

        # A key gets past the title and into the adventure proper, which is a
        # room drawn and a description printed.
        session.type(ENTER)
        wait_change(session, glyphs, opening, timeout=60.0)
        asking = wait_screen(session, glyphs, lands_in, timeout=60.0)
        assert any(lands_in in line for line in asking), (
            f"it never got to the room it opens into: {asking}"
        )
        bitmap = session.read(0x4000, 6144)
        attributes = session.read(ATTRIBUTES, 512)
        asking = wait_screen(session, glyphs, prompt, timeout=60.0)
        assert any(prompt in line for line in asking), (
            f"it never asked for an order: {asking}"
        )

        # And a word it does not know, to see it answer
        session.type("XYZZY" + ENTER)
        answered = wait_screen(session, glyphs, puzzled[:10], timeout=60.0)
    finally:
        session.close()
    assert any(puzzled[:10] in line for line in answered), (
        f"it never said it did not understand: {answered}"
    )
    return bitmap, attributes


def same_picture(ddb, bitmap, attributes, number):
    wrong = sum(
        1
        for row in range(PICTURE_ROWS)
        for column in range(BYTES_ACROSS)
        if bitmap[screen_address(row, column)]
        != reference(ddb, number).pixels[row * BYTES_ACROSS + column]
    )
    return wrong + sum(
        1 for n in range(512) if attributes[n] != reference(ddb, number).attrs[n]
    )


def reference(ddb, number, drawn={}):
    if number not in drawn:
        drawn[number] = Renderer(ddb["gfx"], SpectrumDevice()).run(number)
    return drawn[number]


def blocks_of(tape):
    """Every block of a tape image: what it holds, without the flag byte and
    the checksum that wrap it."""
    with open(tape, "rb") as f:
        image = f.read()
    at, found = 0, []
    while at < len(image):
        length = image[at] | image[at + 1] << 8
        found.append(image[at + 2:at + 2 + length])
        at += 2 + length
    return found


@needs_tools
def test_a_loading_screen_travels_first(tmp_path):
    """A dump of the machine's own screen, put on the tape ahead of everything
    so that there is something to look at while the rest comes in."""
    filler = random.Random(11)
    screen = bytes(filler.randrange(256) for _ in range(6912))
    with open(os.path.join(SPECTRUM, "screen.bin"), "wb") as f:
        f.write(screen)
    build(ADVENTURE, os.path.join(SPECTRUM, "game.rgac"), "spectrum48",
          os.path.join(SPECTRUM, "game.asm"), os.path.join(SPECTRUM, "game.lst"))
    plain = blocks_of(os.path.join(SPECTRUM, "game.tap"))
    emulator.assemble(os.path.join(SPECTRUM, "game.asm"),
                      listing=os.path.join(SPECTRUM, "game.lst"),
                      defines=("SCREEN",))
    with_screen = blocks_of(os.path.join(SPECTRUM, "game.tap"))

    assert len(with_screen) == len(plain) + 1, "no extra block came out"
    # header, the BASIC, then the screen, then the interpreter
    carried = with_screen[2]
    assert carried[1:-1] == screen, "what travelled is not the screen given"
    assert with_screen[3] == plain[2], "the interpreter changed as well"


@needs_tools
def test_the_loader_puts_the_screen_up_and_runs_what_follows():
    """The same tape but with nothing worth running on it.

    Watching this on the real tape is hopeless: the emulator swallows a whole
    tape in a couple of seconds and the interpreter clears the screen the
    moment it starts, so the screen is up and gone between two looks.  With a
    program that does nothing, what the loader left is still there.
    """
    filler = random.Random(3)
    screen = bytes(filler.randrange(256) for _ in range(6912))
    with open(os.path.join(SPECTRUM, "screen.bin"), "wb") as f:
        f.write(screen)
    emulator.assemble(os.path.join(SPECTRUM, "test_loader.asm"),
                      listing=os.path.join(SPECTRUM, "loader.lst"),
                      defines=("SCREEN",))

    session = emulator.Session(machine="48k")
    try:
        time.sleep(2.5)
        session.command("smartload " + os.path.join(SPECTRUM, "loader.tap"))
        time.sleep(12.0)
        shown = bytes(session.read(0x4000, 6912))
        ran = session.read(0x9000, 1)[0]
    finally:
        session.close()
    assert shown == screen, "the loading screen is not what was put on the tape"
    assert ran == 0x2A, "what came after the screen never ran"


@needs_tools
def test_the_48_tape_loads_and_plays():
    with open(ADVENTURE, encoding="utf-8") as f:
        ddb = json.load(f)
    build(
        ADVENTURE,
        os.path.join(SPECTRUM, "game.rgac"),
        "spectrum48",
        os.path.join(SPECTRUM, "game.asm"),
        os.path.join(SPECTRUM, "game.lst"),
    )
    glyphs = glyph_table(Database(ddb))
    played(os.path.join(SPECTRUM, "game.tap"), ddb, glyphs, "48k",
           OPENS_WITH, LANDS_IN)


@needs_tools
def test_the_128_tape_carries_its_banks_to_their_pages():
    ddb = fattened()
    defs = os.path.join(SPECTRUM, "banks.inc")
    build(
        written(ddb),
        os.path.join(SPECTRUM, "game128.rgac"),
        "spectrum128",
        os.path.join(SPECTRUM, "game128.asm"),
        os.path.join(SPECTRUM, "game128.lst"),
        banks="16k",
        defs=defs,
    )
    told = defined(defs)
    assert told["DB_BANK_COUNT"] >= 2, (
        "with everything in one bank nothing is ever paged, so this proves "
        f"nothing: {told}"
    )
    glyphs = glyph_table(Database(ddb))
    bitmap, attributes = played(
        os.path.join(SPECTRUM, "game128.tap"), ddb, glyphs, "128k",
        OPENS_WITH, LANDS_IN
    )
    picture = ddb["locations"][str(LANDS_ROOM)]["graphic_id"]
    assert picture, "the room this adventure opens into is supposed to show one"
    wrong = same_picture(ddb, bitmap, attributes, picture)
    assert not wrong, f"{wrong} bytes of the picture differ from the reference"


if __name__ == "__main__":
    test_the_48_tape_loads_and_plays()
    print("the 48 tape loads and plays")
    test_the_128_tape_carries_its_banks_to_their_pages()
    print("the 128 tape carries its banks to their pages")
