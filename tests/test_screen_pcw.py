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
"""A loading screen on a PCW, which the boot sector has to turn the video on
for.

Nothing shows on this machine until somebody builds the table the video reads,
and until the interpreter runs there is nobody to do it -- so the boot sector
does, before it loads anything, and the screen goes in as the first piece.  It
is the whole screen, both halves one after the other, and the bottom half
lives in a bank the map does not show, so it goes in through the same window
the database uses.

The payload here does nothing at all, which is the only way to look at a
loading screen: the interpreter wipes the screen as it starts, as every
machine's does.
"""

import os
import random
import subprocess
import sys

try:
    import pytest
except ImportError:
    pytest = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import emulator  # noqa: E402
from regac.media import PCW_HALF, PCW_SCREEN_BYTES, banks_of, pcw_release  # noqa: E402

PCW = os.path.join(ROOT, "z80", "pcw")
BOOT = os.path.join(PCW, "boot.asm")
SOURCE = os.path.join(PCW, "test_screen.asm")
ADVENTURE = os.path.join(ROOT, "snapshots", "megacorp2.json")

SCREEN_AT = 0x8000  # the half of the screen the map shows
KEPT_AT = 0xD000  # where the payload leaves what it fetched of the other
SAMPLE = 512

if pytest is not None:
    needs_tools = pytest.mark.skipif(
        not emulator.available(), reason="sjasmplus and ZEsarUX must be in tools/"
    )
else:

    def needs_tools(func):
        return func


def a_screen():
    """A screen no accident would produce, so that finding it means it came
    off the disk."""
    filler = random.Random(7)
    return bytes(filler.randrange(256) for _ in range(PCW_SCREEN_BYTES))


@needs_tools
def test_the_loading_screen_arrives_whole(tmp_path):
    emulator.assemble(BOOT, listing=os.path.join(PCW, "boot.lst"))
    listing = emulator.assemble(SOURCE, listing=os.path.join(PCW, "screen.lst"))
    done = emulator.label_address(listing, "done_flag")
    with open(os.path.join(PCW, "boot.bin"), "rb") as f:
        boot = f.read()
    with open(os.path.join(PCW, "screen.bin"), "rb") as f:
        blob = f.read()
    screen = a_screen()
    path = str(tmp_path / "conpantalla.dsk")
    with open(path, "wb") as f:
        f.write(pcw_release(boot, blob, [], screen))

    session = emulator.Session(
        machine="PCW8256", extra=["--enable-dsk", "--dsk-file", path]
    )
    try:
        arrived = session.wait_for(done, 0xFF, timeout=60.0, every=0.3)
        top = session.read(SCREEN_AT, PCW_HALF)
        kept = session.read(KEPT_AT, 2 * SAMPLE)
        ports = session.command("get-io-ports")
    finally:
        session.close()

    assert arrived, "the disk never finished loading"
    assert top == screen[:PCW_HALF], "the top half of the screen is not the one sent"
    bottom = screen[PCW_HALF:]
    assert kept[:SAMPLE] == bottom[:SAMPLE], "the bottom half starts wrong"
    assert kept[SAMPLE:] == bottom[-SAMPLE:], "the bottom half ends wrong"
    # And the video was actually turned on to show it.
    assert "PCW port F7H: 40" in ports, f"the display was left off: {ports}"


@needs_tools
def test_an_adventure_still_starts_behind_its_screen(tmp_path):
    """With a screen in front of it the interpreter is no longer the first
    piece on the disk, so the loader has to be told where to jump rather than
    jumping into whatever came first."""
    from test_game_pcw import DATABASE, DEFS, LISTING, SOURCE as GAME

    subprocess.run(
        [sys.executable, "-m", "regac", "build", ADVENTURE, DATABASE,
         "-m", "pcw", "-b", "16k", "--defs", DEFS],
        cwd=ROOT, check=True, capture_output=True,
    )
    emulator.assemble(BOOT, listing=os.path.join(PCW, "boot.lst"))
    listing = emulator.assemble(GAME, listing=LISTING)
    done = emulator.label_address(listing, "done_flag")
    with open(os.path.join(PCW, "boot.bin"), "rb") as f:
        boot = f.read()
    with open(os.path.join(PCW, "game_code.bin"), "rb") as f:
        code = f.read()
    with open(DATABASE, "rb") as f:
        banks = banks_of(f.read())
    path = str(tmp_path / "megacorp.dsk")
    with open(path, "wb") as f:
        f.write(pcw_release(boot, code, banks, a_screen()))

    session = emulator.Session(
        machine="PCW8256", extra=["--enable-dsk", "--dsk-file", path]
    )
    try:
        # It is playing when it has cleared the screen the loader left and is
        # waiting for an order, which is what the flag never being set means.
        running = session.wait_for(done, 0xFF, timeout=25.0, every=0.5)
        where = session.pc()
        screen = session.read(SCREEN_AT, PCW_HALF)
    finally:
        session.close()

    assert not running, "the interpreter ran off the end instead of playing"
    assert 0x0100 <= where < 0x4000, f"it is not in the interpreter, it is at ${where:04X}"
    assert screen != a_screen()[:PCW_HALF], "it never got as far as clearing the screen"


if __name__ == "__main__":
    import pathlib
    import tempfile

    test_the_loading_screen_arrives_whole(pathlib.Path(tempfile.mkdtemp()))
    print("the loading screen arrives whole")
