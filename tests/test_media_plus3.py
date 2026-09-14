"""The disk a Spectrum +3 loads, started the way its owner would start it.

Nothing is typed here: a +3 with a disk in it offers Loader as the first thing
on its menu, and what Loader runs is the BASIC program called DISK.  So the
test presses enter on that menu and waits for the adventure to describe where
the player is, which it can only do if the loader ran, the code came off the
disk and the interpreter started.
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
from regac.media import plus3_disk  # noqa: E402
from test_game_z80 import glyph_table, wait_screen  # noqa: E402

SPECTRUM = os.path.join(ROOT, "z80", "spectrum")
SOURCE = os.path.join(SPECTRUM, "game.asm")
DATABASE = os.path.join(SPECTRUM, "game.rgac")
BINARY = os.path.join(SPECTRUM, "game.bin")
LISTING = os.path.join(SPECTRUM, "game.lst")
ADVENTURE = os.path.join(ROOT, "snapshots", "Bangkok1.json")
MACHINE = "P341"                # a +3 with the last of its ROMs
ENTER = chr(13)

if pytest is not None:
    needs_tools = pytest.mark.skipif(
        not emulator.available() or not os.path.exists(ADVENTURE),
        reason="sjasmplus and ZEsarUX must be in tools/, with a decompiled adventure",
    )
else:

    def needs_tools(func):
        return func


def built():
    """The interpreter with an adventure in it, as the assembler leaves it."""
    subprocess.run(
        [sys.executable, "-m", "regac", "build", ADVENTURE, DATABASE,
         "-m", "spectrum48"],
        cwd=ROOT, check=True, capture_output=True,
    )
    emulator.assemble(SOURCE, listing=LISTING)
    with open(BINARY, "rb") as f:
        return f.read()


@needs_tools
def test_the_disk_starts_from_the_menu(tmp_path):
    with open(ADVENTURE, encoding="utf-8") as f:
        ddb = json.load(f)
    path = str(tmp_path / "juego.dsk")
    with open(path, "wb") as f:
        f.write(plus3_disk(built()))
    glyphs = glyph_table(Database(ddb))
    # The end of the description and not the start: this one is long enough
    # that its first lines have scrolled off by the time it asks.
    described = ddb["locations"][str(ddb["init_loc"])]["desc"].strip()[-16:]

    session = emulator.Session(
        machine=MACHINE, extra=["--enable-dsk", "--dsk-file", path]
    )
    try:
        time.sleep(5.0)
        session.type(ENTER)                     # Loader, the first entry
        screen = wait_screen(session, glyphs, described, timeout=90.0)
    finally:
        session.close()
    assert any(described in line for line in screen), (
        f"the adventure never got going: {screen}"
    )


if __name__ == "__main__":
    test_the_disk_starts_from_the_menu  # runs under pytest, which gives a folder
