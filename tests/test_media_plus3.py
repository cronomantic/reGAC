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
from test_game_z80 import glyph_table, screen, wait_screen  # noqa: E402
from test_tape_z80 import fattened, same_picture, screen_address  # noqa: E402,F401

SPECTRUM = os.path.join(ROOT, "z80", "spectrum")
SOURCE = os.path.join(SPECTRUM, "game.asm")
DATABASE = os.path.join(SPECTRUM, "game.rgac")
BINARY = os.path.join(SPECTRUM, "game.bin")
LISTING = os.path.join(SPECTRUM, "game.lst")
ADVENTURE = os.path.join(ROOT, "snapshots", "Bangkok1.json")
MACHINE = "P341"                # a +3 with the last of its ROMs
ENTER = chr(13)
# What this adventure does when it opens, which is its own doing and not the
# interpreter's: it says who wrote it, waits for a key and goes to the
# airport.  The room it starts in is never described -- the high priority
# conditions are looked at before a new room is paid its description, and a
# LOOK there stands in for it.  Measured on the original; see
# doc/pendiente.md.
OPENS_WITH = "FABIAN"
LANDS_ROOM = 15
LANDS_IN = "aeropuerto"

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

    session = emulator.Session(
        machine=MACHINE, extra=["--enable-dsk", "--dsk-file", path]
    )
    try:
        time.sleep(emulator.longer(5.0))
        session.type(ENTER)                     # Loader, the first entry
        screen = wait_screen(session, glyphs, OPENS_WITH, timeout=90.0)
    finally:
        session.close()
    assert any(OPENS_WITH in line for line in screen), (
        f"the adventure never got going: {screen}"
    )


@needs_tools
def test_a_loading_screen_goes_on_the_disk(tmp_path):
    """The Spectrum's own screen dump, as a file of its own, put up by the
    loader before the interpreter comes in."""
    import random

    filler = random.Random(17)
    screen = bytes(filler.randrange(256) for _ in range(6912))
    path = str(tmp_path / "juego.dsk")
    with open(path, "wb") as f:
        f.write(plus3_disk(built(), screen=screen))
    image = open(path, "rb").read()
    # A sector's worth is enough to look for: a disk image breaks a file up
    # with a track header every nine of them, so the whole thing is not in
    # there end to end.
    assert screen[:512] in image, "the screen never made it onto the disk"
    # and the loader says to put it up: the name is in the BASIC it runs
    assert image.count(b"SCREEN") >= 2, "the loader does not ask for it"


BANKED_SOURCE = os.path.join(SPECTRUM, "game3.asm")
BANKED_DATABASE = os.path.join(SPECTRUM, "game3.rgac")
BANKED_DEFS = os.path.join(SPECTRUM, "banks3.inc")
BANKED_LISTING = os.path.join(SPECTRUM, "game3.lst")
BANKED_CODE = os.path.join(SPECTRUM, "game3_code.bin")
BANKED_BOOT = os.path.join(SPECTRUM, "game3_boot.bin")
ATTRIBUTES = 0x5800


def banked(ddb, where, defines=()):
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
    emulator.assemble(BANKED_SOURCE, listing=BANKED_LISTING, defines=defines)
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
    picture = ddb["locations"][str(LANDS_ROOM)]["graphic_id"]

    session = emulator.Session(
        machine=MACHINE, extra=["--enable-dsk", "--dsk-file", path]
    )
    try:
        time.sleep(emulator.longer(5.0))
        session.type(ENTER)
        wait_screen(session, glyphs, OPENS_WITH, timeout=120.0)
        # And the rest of the title before pressing anything: the interpreter
        # looks at the keyboard only when it stops to ask, so a key pressed
        # while the title is still going out is a key nobody hears -- and
        # then it waits for one that never comes.  The last word of the title
        # is what says it has finished.
        wait_screen(session, glyphs,
                    ddb["locations"][str(ddb["init_loc"])]["desc"].split()[-1],
                    timeout=60.0)
        session.type(ENTER)                     # past the title it waits on
        screen = wait_screen(session, glyphs, LANDS_IN, timeout=120.0)
        bitmap = session.read(0x4000, 6144)
        attributes = session.read(ATTRIBUTES, 512)
    finally:
        session.close()
    assert any(LANDS_IN in line for line in screen), (
        f"the adventure never got going: {screen}"
    )
    wrong = same_picture(ddb, bitmap, attributes, picture)
    assert not wrong, f"{wrong} bytes of the picture differ from the reference"


VAJILLAS = os.path.join(ROOT, "snapshots", "vajillas1.json")
SAVE = "VAJILLAS.SAV"


class Vajillas:
    """La guerra de las vajillas on a +3 disk, the way regac make leaves it:
    its game kept under its own name.  It is the one of the eight whose first
    room has a way out, NORTE to room four and SUR back."""

    def __init__(self, where):
        if not os.path.exists(VAJILLAS):
            pytest.skip("La guerra de las vajillas must be in snapshots/")
        with open(VAJILLAS, encoding="utf-8") as f:
            self.ddb = json.load(f)
        boot, code, banks = banked(self.ddb, where,
                                   defines=(f'SAVE_NAME="{SAVE}"',))
        self.image = plus3_banked_disk(boot, code, banks)
        self.where = {name: emulator.label_address(BANKED_LISTING, name)
                      for name in ("vm_location", "vm_state", "vm_state_end",
                                   "vm_seed", "vm_flags", "vm_counters",
                                   "obj_loc")}
        self.glyphs = glyph_table(Database(self.ddb))
        self.prompt = self.ddb["messages"]["240"]
        self.start = self.ddb["init_loc"]
        self.session = None

    def started(self, path, extra=()):
        """The disk in the drive, Loader off the menu, and the first order
        asked for."""
        self.session = emulator.Session(
            machine=MACHINE,
            extra=["--enable-dsk", "--dsk-file", path] + list(extra))
        time.sleep(emulator.longer(5.0))
        self.session.type(ENTER)                # Loader, the first entry
        assert self.settles_in(self.start, 120.0), (
            f"the adventure never asked: {self.screen()}"
        )

    def screen(self):
        return screen(self.session, self.glyphs)

    def room(self):
        low, high = self.session.read(self.where["vm_location"], 2)
        return low | high << 8

    def block(self):
        at = self.where["vm_state"]
        return bytes(self.session.read(at, self.where["vm_state_end"] - at))

    def game(self):
        """The room, the weights, the flags and where every object is: not the
        counters, which Vajillas counts its turns in, nor the seed."""
        block = self.block()
        part = {name: self.where[name] - self.where["vm_state"]
                for name in self.where}
        return (block[:part["vm_seed"]]
                + block[part["vm_flags"]:part["vm_counters"]]
                + block[part["obj_loc"]:])

    def settles_in(self, wanted, timeout=60.0):
        """Whether it is asking again, in that room.  Asking afresh is the
        only sign a save or a load is over, because nothing moves; and a
        machine that stopped to ask something of its own never gets there."""
        lines = emulator.asked(self.screen, self.prompt, timeout)
        return emulator.asking(lines, self.prompt) and self.room() == wanted

    def order(self, words, then_in):
        self.session.type(words + ENTER)
        time.sleep(emulator.longer(1.0))        # for the order to be taken
        assert self.settles_in(then_in), (
            f"after {words} it is in room {self.room()} and not {then_in}, or "
            f"it never asked again: {self.screen()}"
        )


@needs_tools
def test_a_game_is_saved_on_the_disk_and_loaded_off_it(tmp_path):
    """SAVE and LOAD on a +3 go to its disk, in a file of their own, by way of
    +3DOS.  A load with nothing to load leaves the game alone; a save makes
    the file, and a load brings back what it saved.  And the file is on the
    disk, read from the outside once the machine is off: the emulator writes
    to the image only with --dsk-persistent-writes."""
    game = Vajillas(str(tmp_path))
    path = str(tmp_path / "juego.dsk")
    with open(path, "wb") as f:
        f.write(game.image)
    try:
        game.started(path, extra=["--dsk-persistent-writes"])
        before = game.game()
        game.order("LOAD", game.start)
        assert game.game() == before, "a load with no file changed the game"
        game.order("NORTE", 4)
        game.order("SAVE", 4)
        played, block = game.game(), game.block()
        game.order("SUR", game.start)
        game.order("LOAD", 4)
        assert game.game() == played, "what was loaded is not what was saved"
    finally:
        if game.session is not None:
            game.session.close()

    with open(path, "rb") as f:
        image = f.read()
    assert SAVE.replace(".", "").encode() in image, (
        f"there is no {SAVE} in the directory"
    )
    # Where every object is, which nothing moved after the save -- the
    # counters did, because the turn the save was made in went on to count
    # itself.  In its two pieces, a sector each, because a disk image breaks
    # a file up with a track header every nine of them.
    objects = game.where["obj_loc"] - game.where["vm_state"]
    for piece in (block[objects:512], block[512:]):
        assert piece in image, f"the game is not in {SAVE}"


@needs_tools
def test_a_protected_disk_leaves_the_game_going(tmp_path):
    """No disk to write on is said nothing about, as on the other machines:
    +3DOS is told not to ask "Retry, Ignore or Cancel?", which would stop
    the machine over the picture waiting for a key.  So the save comes back,
    the adventure asks for the next order, and the game is as it was."""
    game = Vajillas(str(tmp_path))
    path = str(tmp_path / "juego.dsk")
    with open(path, "wb") as f:
        f.write(game.image)
    try:
        game.started(path, extra=["--dsk-write-protection"])
        game.order("NORTE", 4)
        before = game.game()
        game.order("SAVE", 4)
        assert game.game() == before, "a save that did not go changed the game"
        game.order("SUR", game.start)
    finally:
        if game.session is not None:
            game.session.close()


if __name__ == "__main__":
    test_the_disk_starts_from_the_menu  # runs under pytest, which gives a folder
