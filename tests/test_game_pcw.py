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
"""The whole interpreter playing a real adventure on a PCW.

And playing it off a real disk, which on this machine is the only way there
is: nothing is written into memory by hand here, the machine is switched on
with the disk that `regac release` made in it and it starts itself, reads the
interpreter, the database's banks behind it, and runs.  So what this checks is
the whole chain -- boot sector, loader, paging, screen, keyboard, parser -- in
one go.
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
from regac.devices import PcwDevice  # noqa: E402
from regac.gfx import Renderer  # noqa: E402
from regac.media import PCW_HALF, banks_of, pcw_release  # noqa: E402
from test_keyboard_pcw import type_them  # noqa: E402
from test_text_pcw import ROW_BYTES, WINDOW_ROWS, decode_screen, glyph_table  # noqa: E402

PCW = os.path.join(ROOT, "z80", "pcw")
SOURCE = os.path.join(PCW, "game.asm")
DATABASE = os.path.join(PCW, "game.rgac")
BINARY = os.path.join(PCW, "game_code.bin")
LISTING = os.path.join(PCW, "game.lst")
BOOT = os.path.join(PCW, "boot.asm")
DEFS = os.path.join(PCW, "banks.inc")
ADVENTURE = os.path.join(ROOT, "snapshots", "megacorp2.json")

SCREEN = 0x8000
SCREEN_SLOT = 0xF2  # the port that says which half of it the map shows
BANK_MARK = 0x80
PICTURE_BANK = 2
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


def build(where):
    """Everything regac release does, which is what a person would run."""
    subprocess.run(
        [sys.executable, "-m", "regac", "build", ADVENTURE, DATABASE,
         "-m", "pcw", "-b", "16k", "--defs", DEFS],
        cwd=ROOT, check=True, capture_output=True,
    )
    emulator.assemble(BOOT, listing=os.path.join(PCW, "boot.lst"))
    emulator.assemble(SOURCE, listing=LISTING)
    with open(os.path.join(PCW, "boot.bin"), "rb") as f:
        boot = f.read()
    with open(BINARY, "rb") as f:
        code = f.read()
    with open(DATABASE, "rb") as f:
        banks = banks_of(f.read())
    path = str(where / "megacorp.dsk")
    with open(path, "wb") as f:
        f.write(pcw_release(boot, code, banks))
    return path


def screen(session, glyphs):
    return decode_screen(session.read(SCREEN, WINDOW_ROWS * ROW_BYTES), glyphs)


def wait_screen(session, glyphs, wanted, timeout=60.0):
    """Let it play until those letters show up, and give back the screen.

    A room draws its picture before it says anything, and a picture is
    seconds, so waiting a fixed while is waiting either too little or too
    long."""
    deadline = time.time() + emulator.longer(timeout)
    lines = screen(session, glyphs)
    while time.time() < deadline:
        lines = screen(session, glyphs)
        if any(wanted in line for line in lines if line):
            return lines
        time.sleep(1.0)
    return lines


@needs_tools
def test_it_asks_and_answers_on_a_pcw(tmp_path):
    with open(ADVENTURE, encoding="utf-8") as f:
        ddb = json.load(f)
    path = build(tmp_path)
    database = Database(ddb, machine="pcw")
    glyphs = glyph_table(database)
    prompt = ddb["messages"]["240"]
    puzzled = ddb["messages"][NOT_UNDERSTOOD]

    session = emulator.Session(
        machine="PCW8256", extra=["--enable-dsk", "--dsk-file", path]
    )
    try:
        opening = wait_screen(session, glyphs, prompt.strip()[:3])
        assert any(prompt.strip()[:3] in line for line in opening if line), (
            f"the interpreter never asked: {opening}"
        )

        # And what the room drew, which is in the half of the screen the map
        # does not show while there is text to print, so it has to be brought
        # into the window to be looked at.
        session.command("enter-cpu-step")
        session.command(f"write-port {SCREEN_SLOT} {BANK_MARK | PICTURE_BANK}")
        drawn = session.read(SCREEN, PCW_HALF)
        session.command("exit-cpu-step")

        # Past its own code first.  While the game is still asking for it,
        # its high priority table looks at every turn, and a description is
        # written over the line it starts on, so the complaint below would be
        # covered as soon as it is printed -- which is what the original does
        # there too, watched on it.
        type_them(session, PASSWORD + ENTER)
        wait_screen(session, glyphs, ddb["locations"]["1"]["desc"][:12], timeout=30.0)
        # And then until it asks again, because the description is still
        # going out and a key pressed while it is has nowhere to go.
        emulator.until(lambda: screen(session, glyphs),
                       lambda lines: emulator.asking(lines,
                                                     ddb["messages"]["240"]))
        # A word the adventure does not know, so it has to say so.
        type_them(session, "XYZZY" + ENTER)
        answered = wait_screen(session, glyphs, puzzled[:6], timeout=30.0)

    finally:
        session.close()

    room = ddb["locations"][str(ddb["init_loc"])]["graphic_id"]
    assert drawn == Renderer(ddb["gfx"], PcwDevice()).run(int(room)).screen(), (
        f"the picture of room {ddb['init_loc']} is not the one the reference draws"
    )

    assert answered != opening, "typing changed nothing on screen"
    assert any("XYZZY" in line for line in answered), (
        f"what was typed never showed up: {answered}"
    )
    assert any(puzzled[:6] in line for line in answered), (
        f"expected {puzzled!r} somewhere in {answered}"
    )


if __name__ == "__main__":
    import pathlib
    import tempfile

    test_it_asks_and_answers_on_a_pcw(pathlib.Path(tempfile.mkdtemp()))
    print("the PCW build plays")
