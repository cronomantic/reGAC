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
"""Saving and loading a game on a Spectrum Next, in a file on its card.

La guerra de las vajillas is played, because it is the one of the eight whose
first room has a way out: NORTE takes it from room one to room four and SUR
back.  What is looked at is the room the game is in, the file on the card,
and the question the adventure asks when a turn is over -- asking afresh is
the only sign a save has finished, because nothing moves.

Twice, two ways.  Once through the emulator's own stand-in for the system,
which answers the calls from a folder of the computer the tests run on: that
one is quick and is where the ways of going wrong are tried.  And once with
the Next's own system, NextZXOS, booted off the card image the emulator comes
with and starting the adventure the way a person does -- which is where it was
found that the system takes no call without the ROM in place.
"""

import json
import os
import shutil
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
from fat16 import Card  # noqa: E402
from regac.binary import Database  # noqa: E402
from test_game_next import glyph_table, screen  # noqa: E402

NEXT = os.path.join(ROOT, "z80", "next")
SOURCE = os.path.join(NEXT, "game.asm")
DATABASE = os.path.join(NEXT, "game.rgac")
DEFS = os.path.join(NEXT, "banks.inc")
IMAGE = os.path.join(NEXT, "game.nex")
LISTING = os.path.join(NEXT, "game.lst")
VAJILLAS = os.path.join(ROOT, "snapshots", "vajillas1.json")
SAVE = "VAJILLAS.SAV"
# The card image ZEsarUX comes with: the Next's firmware and NextZXOS.
CARD = os.path.join(ROOT, "tools", "ZEsarUX_windows-13.0", "tbblue.mmc")
ENTER = chr(13)

if pytest is not None:
    needs_tools = pytest.mark.skipif(
        not emulator.available() or not os.path.exists(VAJILLAS),
        reason="sjasmplus and ZEsarUX must be in tools/, and La guerra de las "
               "vajillas in snapshots/",
    )
    needs_card = pytest.mark.skipif(
        not os.path.exists(CARD), reason="ZEsarUX's tbblue.mmc must be in tools/"
    )
else:

    def needs_tools(func):
        return func

    needs_card = needs_tools


def built():
    """Vajillas for the Next, its game kept under its own name, the way
    regac make says it; and where the room and the game are."""
    subprocess.run(
        [sys.executable, "-m", "regac", "build", VAJILLAS, DATABASE,
         "-m", "next", "-b", "16k", "--defs", DEFS],
        cwd=ROOT, check=True, capture_output=True,
    )
    listing = emulator.assemble(SOURCE, listing=LISTING,
                                defines=(f'SAVE_NAME="{SAVE}"',))
    with open(VAJILLAS, encoding="utf-8") as f:
        ddb = json.load(f)
    where = {name: emulator.label_address(listing, name)
             for name in ("vm_location", "vm_state", "vm_state_end",
                          "vm_seed", "vm_flags", "vm_counters", "obj_loc")}
    return ddb, where


class Game:
    """One machine with Vajillas on it, and what it is asked to do."""

    def __init__(self, session, ddb, where):
        self.session = session
        self.where = where
        self.glyphs = glyph_table(Database(ddb))
        self.prompt = ddb["messages"]["240"].strip()

    def room(self):
        low, high = self.session.read(self.where["vm_location"], 2)
        return low | high << 8

    def state(self, game=None):
        """What a game is, the one playing or one out of a file: the room,
        the weights, the flags and where every object is.  Not the counters
        -- Vajillas counts its turns in one of them, so every order moves it,
        a save or a load that does nothing as much as any other -- nor the
        seed or the stack, which a turn uses as it goes."""
        at = self.where["vm_state"]
        if game is None:
            game = bytes(self.session.read(at, self.where["vm_state_end"] - at))
        part = {name: self.where[name] - at for name in self.where}
        return (game[:part["vm_seed"]]
                + game[part["vm_flags"]:part["vm_counters"]]
                + game[part["obj_loc"]:])

    def asking(self):
        lines = [line for line in screen(self.session, self.glyphs) if line.strip()]
        return bool(lines) and lines[-1].strip() == self.prompt

    def settles_in(self, room, timeout=60.0):
        """Whether it gets to that room and is asked for the next order."""
        deadline = time.time() + emulator.longer(timeout)
        while time.time() < deadline:
            if self.room() == room and self.asking():
                return True
            time.sleep(0.5)
        return False

    def order(self, words, then_in, timeout=60.0):
        self.session.type(words + ENTER)
        time.sleep(emulator.longer(1.0))        # for the order to be taken
        assert self.settles_in(then_in, timeout), (
            f"after {words} it is in room {self.room()} and not {then_in}, or "
            f"it never asked again: {screen(self.session, self.glyphs)}"
        )


@needs_tools
def test_a_game_is_kept_in_a_file_beside_the_nex(tmp_path):
    ddb, where = built()
    folder = str(tmp_path)
    nex = os.path.join(folder, "vajillas.nex")
    shutil.copyfile(IMAGE, nex)
    saved = os.path.join(folder, SAVE)
    # Something under the name that is not a game: too short to be one.
    with open(saved, "wb") as f:
        f.write(bytes(10))
    # The emulator, handed a .nex, answers the system's calls from the folder
    # the file is in: that is its stand-in for the card.
    session = emulator.Session(machine="TBBlue")
    try:
        session.load(nex)
        game = Game(session, ddb, where)
        start = ddb["init_loc"]
        assert game.settles_in(start, 90.0), "the adventure never asked"
        game.order("NORTE", 4)
        # A file that is not a whole game leaves the game as it was.
        before = game.state()
        game.order("LOAD", 4)
        assert game.state() == before, "a short file changed the game"
        # A save makes the file anew, whatever it had, with the game in it.
        game.order("SAVE", 4)
        with open(saved, "rb") as f:
            kept = f.read()
        assert game.state(kept) == game.state(), (
            f"what is in {SAVE} is not the game: {len(kept)} bytes, "
            f"{kept[:8].hex()}"
        )
        game.order("SUR", start)
        game.order("LOAD", 4)
    finally:
        session.close()


@needs_tools
def test_a_game_with_no_file_to_load_goes_on(tmp_path):
    ddb, where = built()
    nex = str(tmp_path / "vajillas.nex")
    shutil.copyfile(IMAGE, nex)
    session = emulator.Session(machine="TBBlue")
    try:
        session.load(nex)
        game = Game(session, ddb, where)
        start = ddb["init_loc"]
        assert game.settles_in(start, 90.0), "the adventure never asked"
        before = game.state()
        game.order("LOAD", start)
        assert game.state() == before, "loading nothing changed the game"
        game.order("NORTE", 4)
    finally:
        session.close()
    assert os.listdir(str(tmp_path)) == ["vajillas.nex"], (
        f"a LOAD made something: {os.listdir(str(tmp_path))}"
    )


def plus3_basic(lines):
    """A BASIC program as NextZXOS keeps one on its card: the +3's header
    and the lines, which here are only dot commands and so need no
    tokens."""
    body = b""
    for number, text in lines:
        line = text.encode("ascii") + b"\r"
        body += number.to_bytes(2, "big") + len(line).to_bytes(2, "little") + line
    header = bytearray(128)
    header[0:8] = b"PLUS3DOS"
    header[8] = 0x1A                            # the end of a text file
    header[9] = 1                               # issue and version
    header[11:15] = (128 + len(body)).to_bytes(4, "little")
    header[15] = 0                              # a program
    header[16:18] = len(body).to_bytes(2, "little")
    header[18:20] = lines[0][0].to_bytes(2, "little")   # run from the first
    header[20:22] = len(body).to_bytes(2, "little")     # and no variables
    header[127] = sum(header[:127]) & 0xFF
    return bytes(header) + body


# The firmware's own settings as they come on the card, but with a video mode
# chosen: as the card comes, the first boot puts up a test card and waits for
# somebody to press enter at it.
CONFIG = b"ps2=0\ntiming=7\ndefault=0\n"


@needs_tools
@needs_card
def test_a_game_saved_and_loaded_on_nextzxos(tmp_path):
    ddb, where = built()
    folder = str(tmp_path)
    card = os.path.join(folder, "card.mmc")
    shutil.copyfile(CARD, card)
    pieces = {
        "vajillas.nex": (open(IMAGE, "rb").read(), "games/vajillas.nex"),
        # What NextZXOS runs once it is up: into the folder, and the
        # adventure started from there -- as the browser does when a person
        # picks it, going into the folder first.
        "autoexec.bas": (plus3_basic([(10, ".cd /games"),
                                      (20, ".nexload vajillas.nex")]),
                         "nextzxos/autoexec.bas"),
        "config.ini": (CONFIG, "machines/next/config.ini"),
    }
    copied = []
    for name, (data, on_card) in pieces.items():
        path = os.path.join(folder, name)
        with open(path, "wb") as f:
            f.write(data)
        copied += ["--copy-file-to-mmc", path, on_card]
    session = emulator.Session(machine="TBBlue", extra=[
        "--enable-mmc", "--enable-divmmc-ports", "--mmc-file", card,
    ] + copied)
    try:
        game = Game(session, ddb, where)
        start = ddb["init_loc"]
        assert game.settles_in(start, 120.0), (
            "NextZXOS never got the adventure going"
        )
        game.order("SAVE", start)
        game.order("NORTE", 4)
        game.order("LOAD", start)
    finally:
        session.close()
    time.sleep(emulator.longer(1.0))
    kept = Card(card).read("games/" + SAVE)
    assert kept is not None, f"no {SAVE} beside the adventure on the card"
    assert len(kept) == where["vm_state_end"] - where["vm_state"], len(kept)
    assert kept[0] | kept[1] << 8 == start, (
        f"the game on the card is not in room {start}: {kept[:8].hex()}"
    )


if __name__ == "__main__":
    import pathlib
    import tempfile

    for test in (test_a_game_is_kept_in_a_file_beside_the_nex,
                 test_a_game_with_no_file_to_load_goes_on,
                 test_a_game_saved_and_loaded_on_nextzxos):
        test(pathlib.Path(tempfile.mkdtemp()))
        print(test.__name__)
