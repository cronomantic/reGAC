"""The Amstrad interpreter printing, assembled and run for real.

The same check as the Spectrum's: the screen is read out of the emulator and
decoded back into text with the adventure's own font, so nothing is taken on
trust.  What differs is the reading, because a glyph is eight pixels across
and mode 1 keeps four pixels to a byte, so every character is two bytes wide
and its eight lines are two kilobytes apart.
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

CPC = os.path.join(ROOT, "z80", "cpc")
SOURCE = os.path.join(CPC, "main.asm")
DATABASE = os.path.join(CPC, "text.rgac")
BINARY = os.path.join(CPC, "text.bin")
LISTING = os.path.join(CPC, "text.lst")
ADVENTURE = os.path.join(ROOT, "snapshots", "megacorp2.json")

LOADS_AT = 0x4000
SCREEN = 0xC000
TEXT_TOP = 16  # the picture takes the sixteen rows above
WINDOW_ROWS = 9
COLUMNS = 40
LINE_BYTES = 80
MESSAGES_PRINTED = 6

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
        [sys.executable, "-m", "regac", "build", ADVENTURE, DATABASE, "-m", "cpc"],
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

    A character cell is two bytes at row * 80 + column * 2, and its eight
    lines are a block of 2048 apart.  Each pair of bytes holds eight pixels of
    pen one, four in the top half of each.
    """
    lines = []
    for row in range(WINDOW_ROWS):
        line = ""
        for column in range(COLUMNS):
            at = (TEXT_TOP + row) * LINE_BYTES + column * 2
            cell = bytes(
                (memory[block * 2048 + at] & 0xF0)
                | ((memory[block * 2048 + at + 1] >> 4) & 0x0F)
                for block in range(8)
            )
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
def test_the_amstrad_prints_what_the_database_holds():
    with open(ADVENTURE, encoding="utf-8") as f:
        ddb = json.load(f)
    listing = build()
    done = emulator.label_address(listing, "done_flag")
    with open(BINARY, "rb") as f:
        blob = f.read()

    session = emulator.Session(machine="CPC6128")
    try:
        time.sleep(3.0)
        for at in range(0, len(blob), 512):
            piece = blob[at:at + 512]
            session.command(f"write-memory-raw {LOADS_AT + at} " + piece.hex().upper())
        session.command(f"set-register PC={LOADS_AT:04X}H")
        finished = session.wait_for(done, 0xFF, timeout=40.0, every=0.1)
        memory = session.read(SCREEN, 0x4000)
    finally:
        session.close()
    assert finished, "the interpreter never reached the end of its run"

    database = Database(ddb)
    lines = decode_screen(memory, glyph_table(database))
    expected = wrapped(database.texts[:MESSAGES_PRINTED])
    visible = [line for line in lines if line]
    assert visible == expected[-len(visible):]
    assert len(visible) >= 5, "hardly anything was printed"


if __name__ == "__main__":
    test_the_amstrad_prints_what_the_database_holds()
    print("the Amstrad build prints what it should")
