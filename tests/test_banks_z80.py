"""The interpreter playing with its database in memory banks, on a 128.

The point of the banks is that a section the interpreter reads through the
window at $C000 has to come out the same as one sitting next to the code, and
that asking for one does not lose the other.  So this makes an adventure whose
text and pictures cannot share a bank, plays it, and checks both: the room is
described, which reads the text bank, and the picture on the screen is exactly
what the reference renderer draws, which reads the other one.  Between the two
the machine pages twice.

The adventure is Los pájaros de Bangkok with enough filler messages added to
push the text out of the picture's bank.  Filler is random letters on purpose:
anything repetitive the packer would squeeze back down to nothing.
"""

import json
import os
import random
import subprocess
import sys
import tempfile

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
SOURCE = os.path.join(SPECTRUM, "game128.asm")
DATABASE = os.path.join(SPECTRUM, "game128.rgac")
SNAPSHOT = os.path.join(SPECTRUM, "game128.sna")
LISTING = os.path.join(SPECTRUM, "game128.lst")
DEFS = os.path.join(SPECTRUM, "banks.inc")
ADVENTURE = os.path.join(ROOT, "snapshots", "Bangkok1.json")

ENTER = chr(13)
NOT_UNDERSTOOD = "242"
PICTURE_ROWS = 128
BYTES_ACROSS = 32
ATTRIBUTES = 0x5800

if pytest is not None:
    needs_tools = pytest.mark.skipif(
        not emulator.available() or not os.path.exists(ADVENTURE),
        reason="sjasmplus and ZEsarUX must be in tools/, with a decompiled adventure",
    )
else:

    def needs_tools(func):
        return func


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
            messages[str(number)] = "".join(
                filler.choice(letters) for _ in range(60)
            )
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


def build(ddb):
    folder = tempfile.mkdtemp()
    source = os.path.join(folder, "banked.json")
    with open(source, "w", encoding="utf-8") as f:
        json.dump(ddb, f)
    subprocess.run(
        [sys.executable, "-m", "regac", "build", source, DATABASE,
         "-m", "spectrum128", "-b", "16k", "--defs", DEFS],
        cwd=ROOT, check=True, capture_output=True,
    )
    return emulator.assemble(SOURCE, listing=LISTING)


@needs_tools
def test_it_plays_with_its_database_in_banks():
    ddb = fattened()
    build(ddb)
    told = defined(DEFS)
    assert told["DB_BANK_COUNT"] >= 2, (
        "with everything in one bank nothing is ever paged, so this proves "
        f"nothing: {told}"
    )

    database = Database(ddb)
    glyphs = glyph_table(database)
    room = str(ddb["init_loc"])
    described = ddb["locations"][room]["desc"]
    picture = ddb["locations"][room]["graphic_id"]
    prompt = ddb["messages"]["240"]
    puzzled = ddb["messages"][NOT_UNDERSTOOD]
    assert picture, "the first room of this adventure is supposed to show one"

    session = emulator.Session(machine="128k")
    try:
        session.load(SNAPSHOT)
        opening = wait_screen(session, glyphs, prompt.strip()[:3])
        # The end of the description and not the start: this one is long
        # enough that its first lines have scrolled off by the time the
        # interpreter asks.
        tail = described.strip()[-16:]
        assert any(tail in line for line in opening), (
            f"the room was never described: {opening}"
        )
        bitmap = session.read(0x4000, 6144)
        attributes = session.read(ATTRIBUTES, 512)

        # The first room of this one is the title, and anything typed at it
        # moves the player on, so the word that means nothing goes to the
        # room after it.  Getting there draws another picture and prints
        # another description, which is another turn of the two banks.
        session.type("XYZZY" + ENTER)
        wait_screen(session, glyphs, prompt.strip()[:3], timeout=45.0)
        session.type("XYZZY" + ENTER)
        answered = wait_screen(session, glyphs, puzzled[:10], timeout=45.0)
    finally:
        session.close()

    reference = Renderer(ddb["gfx"], SpectrumDevice()).run(picture)
    wrong = sum(
        1
        for row in range(PICTURE_ROWS)
        for column in range(BYTES_ACROSS)
        if bitmap[screen_address(row, column)]
        != reference.pixels[row * BYTES_ACROSS + column]
    )
    wrong += sum(1 for n in range(512) if attributes[n] != reference.attrs[n])
    assert not wrong, f"{wrong} bytes of the picture differ from the reference"
    assert any(puzzled[:10] in line for line in answered), (
        f"expected {puzzled!r} somewhere in {answered}"
    )


if __name__ == "__main__":
    test_it_plays_with_its_database_in_banks()
    print("it plays out of its banks")
