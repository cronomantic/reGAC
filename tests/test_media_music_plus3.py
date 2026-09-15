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
"""The +3's disk with music on it, started from the machine's own menu.

The machine is the 128's, so the music goes where it goes there: the player
below the interpreter and the tunes in a page of their own.  What is different
is everything around that.  Nothing travels as a block of a tape here -- the
loader is machine code, because BASIC cannot page, and what it reads is one
file with the pieces end to end -- so the music is two more pieces of that
file, and they have to be in the very order the table it walks asks for them.
A piece out of order is not a tune that sounds wrong: it is a bank of the
database loaded into the middle of the player.

And this machine has fewer pages to spare: +3DOS keeps two of the eight, so
the tunes take the last of the four the database could have had.  An adventure
of three banks has music here and one of four has not, which the build says
rather than finding out later.
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
from regac.conds import compile_block  # noqa: E402
from regac.media import banks_of, plus3_banked_disk  # noqa: E402
from test_game_z80 import glyph_table, wait_screen  # noqa: E402
from test_media_plus3 import MACHINE  # noqa: E402
from test_music_z80 import TUNE, word  # noqa: E402

SPECTRUM = os.path.join(ROOT, "z80", "spectrum")
SOURCE = os.path.join(SPECTRUM, "game3.asm")
DATABASE = os.path.join(SPECTRUM, "game3.rgac")
DEFS = os.path.join(SPECTRUM, "banks3.inc")
LISTING = os.path.join(SPECTRUM, "game3.lst")
PIECES = ("game3_boot.bin", "game3_code.bin", "game3_music.bin",
          "game3_tunes.bin")
ADVENTURE = os.path.join(ROOT, "snapshots", "Bangkok1.json")
EFFECTS = os.path.join(ROOT, "music", "effects.asm")

ENTER = chr(13)
A_FLAG = 250                    # one this adventure does not use

if pytest is not None:
    needs_tools = pytest.mark.skipif(
        not emulator.available()
        or not os.path.exists(ADVENTURE)
        or not os.path.exists(TUNE)
        or not os.path.exists(EFFECTS),
        reason="sjasmplus and ZEsarUX must be in tools/, with a decompiled"
               " adventure, a tune and a bank of effects",
    )
else:

    def needs_tools(func):
        return func


@needs_tools
def test_the_disk_carries_the_music_in_its_one_file(tmp_path):
    with open(ADVENTURE, encoding="utf-8") as f:
        ddb = json.load(f)
    ddb["hpcs"] = compile_block(
        [f"IF ( RES? {A_FLAG} ) SET {A_FLAG} MUSIC 0 END"]
    ) + ddb["hpcs"]

    source = str(tmp_path / "adventure.json")
    with open(source, "w", encoding="utf-8") as f:
        json.dump(ddb, f)
    subprocess.run(
        [sys.executable, "-m", "regac", "build", source, DATABASE,
         "-m", "spectrum128", "-b", "16k", "--defs", DEFS],
        cwd=ROOT, check=True, capture_output=True,
    )
    listing = emulator.assemble(SOURCE, listing=LISTING,
                                defines=("WITH_MUSIC", "WITH_EFFECTS"))
    where = {name: emulator.label_address(listing, name)
             for name in ("music_playing", "music_buffer", "start",
                          "PLY_AKM_Track1_PtTrack")}

    pieces = []
    for name in PIECES:
        with open(os.path.join(SPECTRUM, name), "rb") as f:
            pieces.append(f.read())
    boot, code, player, tunes = pieces
    with open(DATABASE, "rb") as f:
        banks = banks_of(f.read())

    path = str(tmp_path / "juego.dsk")
    with open(path, "wb") as f:
        f.write(plus3_banked_disk(boot, code, banks, music=(player, tunes)))

    glyphs = glyph_table(Database(ddb, machine="spectrum128", page_bits=14))
    described = ddb["locations"][str(ddb["init_loc"])]["desc"].strip()[-16:]

    session = emulator.Session(
        machine=MACHINE, extra=["--enable-dsk", "--dsk-file", path]
    )
    try:
        time.sleep(5.0)
        session.type(ENTER)             # the Loader entry of the menu
        screen = wait_screen(session, glyphs, described, timeout=120.0)
        assert any(described in line for line in screen), (
            f"the adventure never got going: {screen}"
        )
        assert session.wait_for(where["music_playing"], 1, timeout=30.0), (
            "it loaded and played, but the tune never started"
        )
        at = word(session, where["PLY_AKM_Track1_PtTrack"])
        assert where["music_buffer"] <= at < where["start"], (
            f"the player is not reading the buffer, so the pieces did not land"
            f" where the table said: ${at:04X}"
        )
        was = at
        deadline = time.time() + 5.0
        while (time.time() < deadline
               and word(session, where["PLY_AKM_Track1_PtTrack"]) == was):
            time.sleep(0.2)
        assert word(session, where["PLY_AKM_Track1_PtTrack"]) != was, (
            "the tune was copied but never moved on"
        )
    finally:
        session.close()


if __name__ == "__main__":
    import pathlib
    import tempfile
    test_the_disk_carries_the_music_in_its_one_file(
        pathlib.Path(tempfile.mkdtemp()))
    print("the disk carries the music in its one file")
