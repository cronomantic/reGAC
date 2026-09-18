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
"""The whole interpreter playing a real adventure on an Amstrad.

It loads MegaCorp, lets the interpreter say its piece and ask for an order,
types one at the keyboard and checks what comes back.  The keyboard is driven
one press and one release at a time, which keeps the timing in the test's
hands rather than the emulator's.
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
from test_text_cpc import decode_screen, glyph_table  # noqa: E402

CPC = os.path.join(ROOT, "z80", "cpc")
SOURCE = os.path.join(CPC, "game.asm")
DATABASE = os.path.join(CPC, "game.rgac")
BINARY = os.path.join(CPC, "game.bin")
LISTING = os.path.join(CPC, "game.lst")
ADVENTURE = os.path.join(ROOT, "snapshots", "megacorp2.json")

LOADS_AT = 0x4000
SCREEN = 0xC000
ENTER = chr(13)
# Its own code, which is in its own vocabulary: room 5000 takes verb 29,
# and verb 29 of MegaCorp is REBECA.
PASSWORD = "REBECA"
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
        [sys.executable, "-m", "regac", "build", ADVENTURE, DATABASE, "-m", "cpc"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return emulator.assemble(SOURCE, listing=LISTING)


def start(session):
    with open(BINARY, "rb") as f:
        blob = f.read()
    for at in range(0, len(blob), 512):
        session.command(f"write-memory-raw {LOADS_AT + at} " + blob[at:at + 512].hex().upper())
    session.jump(LOADS_AT)


def screen(session, glyphs):
    return decode_screen(session.read(SCREEN, 0x4000), glyphs)


def wait_screen(session, glyphs, wanted, timeout=60.0):
    """Let it play until those letters show up, and give back the screen.

    A room draws its picture before it says anything, and a picture is
    seconds, so waiting a fixed while is waiting either too little or too
    long."""
    deadline = time.time() + timeout
    lines = screen(session, glyphs)
    while time.time() < deadline:
        lines = screen(session, glyphs)
        if any(wanted in line for line in lines if line):
            return lines
        time.sleep(1.0)
    return lines


@needs_tools
def test_it_asks_and_answers_on_an_amstrad():
    with open(ADVENTURE, encoding="utf-8") as f:
        ddb = json.load(f)
    build()
    database = Database(ddb)
    glyphs = glyph_table(database)
    prompt = ddb["messages"]["240"]
    puzzled = ddb["messages"][NOT_UNDERSTOOD]

    session = emulator.Session(machine="CPC6128")
    try:
        time.sleep(3.0)
        start(session)
        # Loading from its tape is the longest wait in the suite, and a
        # machine that is running four emulators at once takes longer
        # still, so this one is given room.
        opening = wait_screen(session, glyphs, prompt.strip()[:3], timeout=180.0)
        assert any(prompt.strip()[:3] in line for line in opening if line), (
            f"the interpreter never asked: {opening}"
        )

        # Past its own code first.  While the game is still asking for it,
        # its high priority table looks at every turn, and a description is
        # written over the line it starts on, so the complaint below would be
        # covered as soon as it is printed -- which is what the original does
        # there too, watched on it.
        session.type_keys(PASSWORD + ENTER)
        wait_screen(session, glyphs, ddb["locations"]["1"]["desc"][:12], timeout=30.0)
        # A word the adventure does not know, so it has to say so.
        session.type_keys("XYZZY" + ENTER)
        answered = wait_screen(session, glyphs, puzzled[:6], timeout=30.0)
    finally:
        session.close()

    assert answered != opening, "typing changed nothing on screen"
    assert any("XYZZY" in line for line in answered), (
        f"what was typed never showed up: {answered}"
    )
    assert any(puzzled[:6] in line for line in answered), (
        f"expected {puzzled!r} somewhere in {answered}"
    )


if __name__ == "__main__":
    test_it_asks_and_answers_on_an_amstrad()
    print("the Amstrad build plays")
