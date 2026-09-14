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
    deadline = time.time() + timeout
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


def build(source, database, machine, source_asm, listing, banks=None, defs=None):
    order = [sys.executable, "-m", "regac", "build", source, database, "-m", machine]
    if banks:
        order += ["-b", banks, "--defs", defs]
    subprocess.run(order, cwd=ROOT, check=True, capture_output=True)
    return emulator.assemble(source_asm, listing=listing)


def played(tape, ddb, glyphs, machine):
    """Load the tape as a person would, let it get as far as describing where
    the player is, and then talk to it.  Gives back the screen it drew.

    This adventure opens on its title, which is a room like any other: it
    draws its picture, says its piece and waits for a key.  So what says it
    has arrived is the description and not the prompt, which that room never
    gives.
    """
    room = str(ddb["init_loc"])
    described = ddb["locations"][room]["desc"].strip()
    prompt = ddb["messages"]["240"].strip()[:3]
    puzzled = ddb["messages"][NOT_UNDERSTOOD]
    session = emulator.Session(machine=machine, extra=TAPE_FLAGS)
    try:
        session.load(tape)
        # The end of the description and not the start: this one is long
        # enough that its first lines have scrolled off by then.
        opening = wait_screen(session, glyphs, described[-16:], timeout=120.0)
        assert any(described[-16:] in line for line in opening), (
            f"the room was never described: {opening}"
        )
        bitmap = session.read(0x4000, 6144)
        attributes = session.read(ATTRIBUTES, 512)

        # A key gets past the title and into the adventure proper, which is
        # another room drawn and another description printed.
        session.type(ENTER)
        wait_change(session, glyphs, opening, timeout=60.0)
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
    played(os.path.join(SPECTRUM, "game.tap"), ddb, glyphs, "48k")


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
        os.path.join(SPECTRUM, "game128.tap"), ddb, glyphs, "128k"
    )
    picture = ddb["locations"][str(ddb["init_loc"])]["graphic_id"]
    assert picture, "the first room of this adventure is supposed to show one"
    wrong = same_picture(ddb, bitmap, attributes, picture)
    assert not wrong, f"{wrong} bytes of the picture differ from the reference"


if __name__ == "__main__":
    test_the_48_tape_loads_and_plays()
    print("the 48 tape loads and plays")
    test_the_128_tape_carries_its_banks_to_their_pages()
    print("the 128 tape carries its banks to their pages")
