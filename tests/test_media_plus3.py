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
from regac.media import banks_of, plus3_banked_disk, plus3_disk  # noqa: E402
from test_game_z80 import glyph_table, wait_screen  # noqa: E402
from test_tape_z80 import fattened, same_picture, screen_address  # noqa: E402,F401

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


BANKED_SOURCE = os.path.join(SPECTRUM, "game3.asm")
BANKED_DATABASE = os.path.join(SPECTRUM, "game3.rgac")
BANKED_DEFS = os.path.join(SPECTRUM, "banks3.inc")
BANKED_LISTING = os.path.join(SPECTRUM, "game3.lst")
BANKED_CODE = os.path.join(SPECTRUM, "game3_code.bin")
BANKED_BOOT = os.path.join(SPECTRUM, "game3_boot.bin")
ATTRIBUTES = 0x5800


def banked(ddb, where):
    """The adventure built with its database in banks, and the two pieces the
    disk is made of."""
    source = os.path.join(where, "adventure.json")
    with open(source, "w", encoding="utf-8") as f:
        json.dump(ddb, f)
    subprocess.run(
        [sys.executable, "-m", "regac", "build", source, BANKED_DATABASE,
         "-m", "spectrum128", "-b", "16k", "--defs", BANKED_DEFS],
        cwd=ROOT, check=True, capture_output=True,
    )
    emulator.assemble(BANKED_SOURCE, listing=BANKED_LISTING)
    pieces = []
    for path in (BANKED_BOOT, BANKED_CODE, BANKED_DATABASE):
        with open(path, "rb") as f:
            pieces.append(f.read())
    return pieces[0], pieces[1], banks_of(pieces[2])


@needs_tools
def test_a_banked_disk_puts_each_bank_in_its_page(tmp_path):
    """The loader in this one is machine code, because paging is not something
    BASIC can do, and it is +3DOS that reads each bank into the page it is
    told.  What says it went right is the picture on the screen, which comes
    out of one bank while the description comes out of another."""
    ddb = fattened()
    boot, code, banks = banked(ddb, str(tmp_path))
    assert len(banks) >= 2, (
        f"with one bank nothing is ever paged, so this proves nothing: {banks}"
    )
    path = str(tmp_path / "juego.dsk")
    with open(path, "wb") as f:
        f.write(plus3_banked_disk(boot, code, banks))

    glyphs = glyph_table(Database(ddb))
    room = str(ddb["init_loc"])
    described = ddb["locations"][room]["desc"].strip()[-16:]
    picture = ddb["locations"][room]["graphic_id"]

    session = emulator.Session(
        machine=MACHINE, extra=["--enable-dsk", "--dsk-file", path]
    )
    try:
        time.sleep(5.0)
        session.type(ENTER)
        screen = wait_screen(session, glyphs, described, timeout=120.0)
        bitmap = session.read(0x4000, 6144)
        attributes = session.read(ATTRIBUTES, 512)
    finally:
        session.close()
    assert any(described in line for line in screen), (
        f"the adventure never got going: {screen}"
    )
    wrong = same_picture(ddb, bitmap, attributes, picture)
    assert not wrong, f"{wrong} bytes of the picture differ from the reference"


if __name__ == "__main__":
    test_the_disk_starts_from_the_menu  # runs under pytest, which gives a folder
