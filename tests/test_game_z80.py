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
"""The whole interpreter playing a real adventure on a real Z80.

It loads MegaCorp, lets the interpreter describe where the player starts and
ask for an order, types one at the keyboard and checks what comes back.  The
keyboard is driven by holding each key down and letting it go in turn, which
keeps the timing in the test's hands rather than the emulator's.
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
import keystrokes  # noqa: E402
from regac.binary import S_FONT, Database, Reader  # noqa: E402

SPECTRUM = os.path.join(ROOT, "z80", "spectrum")
SOURCE = os.path.join(SPECTRUM, "game.asm")
DATABASE = os.path.join(SPECTRUM, "game.rgac")
SNAPSHOT = os.path.join(SPECTRUM, "game.sna")
LISTING = os.path.join(SPECTRUM, "game.lst")
ADVENTURE = os.path.join(ROOT, "snapshots", "megacorp2.json")

TEXT_THIRD = 0x5000
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
    with open(ADVENTURE, encoding="utf-8") as f:
        ddb = json.load(f)
    subprocess.run(
        [sys.executable, "-m", "regac", "build", ADVENTURE, DATABASE, "-m", "spectrum48"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return ddb, emulator.assemble(SOURCE, listing=LISTING)


def glyph_table(database):
    font = Reader(database.build()).section(S_FONT)
    first, count = font[0], font[1]
    table = {}
    for index in range(count):
        glyph = bytes(font[2 + index * 8 : 10 + index * 8])
        char = database.store.charset.chars.get(first + index)
        if char is not None:            # a hole in the run draws nothing
            table.setdefault(glyph, char)
    return table


def screen(session, glyphs):
    memory = session.read(TEXT_THIRD, 2048)
    lines = []
    for row in range(8):
        line = "".join(
            glyphs.get(bytes(memory[p * 256 + row * 32 + c] for p in range(8)), "?")
            for c in range(32)
        )
        lines.append(line.rstrip())
    return lines


def wait_screen(session, glyphs, wanted, timeout=30.0):
    """Let it play until those letters show up, and give back the screen.  A
    room draws its picture before it says anything, and that takes seconds."""
    deadline = time.time() + emulator.longer(timeout)
    lines = screen(session, glyphs)
    while time.time() < deadline:
        lines = screen(session, glyphs)
        if any(wanted in line for line in lines if line):
            return lines
        time.sleep(0.5)
    return lines


@needs_tools
def test_it_describes_asks_and_answers():
    ddb, listing = build()
    database = Database(ddb)
    glyphs = glyph_table(database)
    where = ddb["locations"][str(ddb["init_loc"])]["desc"]
    prompt = ddb["messages"]["240"]
    puzzled = ddb["messages"][NOT_UNDERSTOOD]

    session = emulator.Session()
    try:
        session.load(SNAPSHOT)
        opening = wait_screen(session, glyphs, prompt.strip()[:3])
        assert any(where[:16] in line for line in opening), (
            f"the room was never described: {opening}"
        )
        assert any(prompt.strip()[:3] in line for line in opening if line), (
            f"the interpreter never asked: {opening}"
        )

        # Past its own code first.  While the game is still asking for it,
        # its high priority table looks at every turn, and a description is
        # written over the line it starts on, so the complaint below would be
        # covered as soon as it is printed -- which is what the original does
        # there too, watched on it.
        session.type(PASSWORD + ENTER)
        wait_screen(session, glyphs, ddb["locations"]["1"]["desc"][:12], timeout=30.0)
        # A word the adventure does not know, so it has to say so.
        session.type("XYZZY" + ENTER)
        answered = wait_screen(session, glyphs, puzzled[:10], timeout=20.0)
    finally:
        session.close()

    assert answered != opening, "typing changed nothing on screen"
    assert any(puzzled[:10] in line for line in answered), (
        f"expected {puzzled!r} somewhere in {answered}"
    )


@needs_tools
def test_it_keeps_up_with_quick_typing_and_repeats_a_held_key():
    """Typing as people type: each key down before the last one is up, and a
    key held until it repeats.  See keystrokes.py for what the original does."""
    ddb, listing = build()
    glyphs = glyph_table(Database(ddb))
    prompt = ddb["messages"]["240"].strip()[:3]
    events = emulator.Session.EVENT_KEYS

    session = emulator.Session()
    try:
        session.load(SNAPSHOT)
        wait_screen(session, glyphs, prompt)
        keystrokes.play(session, keystrokes.ROLLED, events)
        rolled = wait_screen(session, glyphs, keystrokes.ROLLED_GIVES, timeout=20.0)
        time.sleep(3.0)
        keystrokes.play(session, keystrokes.HELD[:3], events)
        held = screen(session, glyphs)
    finally:
        session.close()

    assert any(keystrokes.ROLLED_GIVES in line for line in rolled), (
        f"keys typed over each other were lost: {rolled}"
    )
    assert any(keystrokes.HELD_KEY * 3 in line for line in held), (
        f"a key held down did not repeat: {held}"
    )


if __name__ == "__main__":
    test_it_describes_asks_and_answers()
    print("the interpreter plays")
