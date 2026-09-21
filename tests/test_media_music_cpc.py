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
"""The Amstrad's disk with music on it, started the way a person would.

The music of an Amstrad cannot be loaded where it is going to live: it lives
under $4000, and the BASIC line that does the loading is itself at $0170.  So
it travels as a file with twenty instructions in front of it, and the loader
brings it in at $4000 -- where nothing is yet -- calls it, and those twenty
instructions carry it down to $0300 and come back.  Then the interpreter is
loaded over the top of where it was.

Three things have to be right for that and none of them shows on the screen:
the extra lines of BASIC, the mover, and the interpreter finding the music
where the mover left it.  So this makes the disk, puts it in a machine, types
RUN"JUEGO, and then looks at where the player is reading.
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
from regac.__main__ import write_database  # noqa: E402
from regac.binary import Reader  # noqa: E402
from regac.media import banks_of, cpc6128_disk  # noqa: E402
from test_game_cpc import glyph_table, wait_screen  # noqa: E402
from test_media_cpc import asking  # noqa: E402
from test_music_z80 import TUNE, word  # noqa: E402

CPC = os.path.join(ROOT, "z80", "cpc")
SOURCE = os.path.join(CPC, "game6128.asm")
DATABASE = os.path.join(CPC, "game6128.rgac")
BINARY = os.path.join(CPC, "game6128.bin")
MUSIC_BINARY = os.path.join(CPC, "game6128_music.bin")
LISTING = os.path.join(CPC, "game6128.lst")
DEFS = os.path.join(CPC, "banks6128.inc")
ADVENTURE = os.path.join(ROOT, "snapshots", "megacorp2.json")
EFFECTS = os.path.join(ROOT, "music", "effects.asm")

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
def test_the_disk_carries_the_music_under_4000(tmp_path):
    with open(ADVENTURE, encoding="utf-8") as f:
        ddb = json.load(f)
    ddb["hpcs"] = compile_block(
        [f"IF ( RES? {A_FLAG} ) SET {A_FLAG} MUSIC 0 END"]
    ) + ddb["hpcs"]
    # The 6128's database, in banks, with the include its game6128.asm wants.
    database = write_database(ddb, DATABASE, machine="cpc", banks="16k",
                              defs=DEFS)
    with open(DATABASE, "rb") as f:
        image = f.read()
    listing = emulator.assemble(SOURCE, listing=LISTING,
                                defines=("WITH_MUSIC", "WITH_EFFECTS"))
    where = {name: emulator.label_address(listing, name)
             for name in ("music_playing", "music_at", "music_end",
                          "PLY_AKM_Track1_PtTrack")}

    with open(BINARY, "rb") as f:
        code = f.read()
    with open(MUSIC_BINARY, "rb") as f:
        music = f.read()
    path = str(tmp_path / "juego.dsk")
    resident = image[:Reader(image).resident_size]
    with open(path, "wb") as f:
        f.write(cpc6128_disk(code, resident, banks_of(image), music=music))

    glyphs = glyph_table(database)
    session = emulator.Session(
        machine="CPC6128", extra=["--enable-dsk", "--dsk-file", path]
    )
    try:
        time.sleep(emulator.longer(4.0))
        session.type_keys('run"juego' + chr(13))
        screen = wait_screen(session, glyphs, asking(ddb), timeout=120.0)
        assert any(asking(ddb) in line for line in screen if line), (
            f"the adventure never got going: {screen}"
        )
        assert session.read(where["music_playing"], 1)[0] == 1, (
            "it loaded and played, but the tune never started"
        )
        at = word(session, where["PLY_AKM_Track1_PtTrack"])
        assert where["music_at"] <= at < where["music_end"], (
            f"the mover did not leave the music under $4000: ${at:04X}"
        )
        was = at
        deadline = time.time() + 5.0
        while (time.time() < deadline
               and word(session, where["PLY_AKM_Track1_PtTrack"]) == was):
            time.sleep(0.2)
        assert word(session, where["PLY_AKM_Track1_PtTrack"]) != was, (
            "the music arrived but never moved on"
        )
    finally:
        session.close()


if __name__ == "__main__":
    import tempfile
    import pathlib
    test_the_disk_carries_the_music_under_4000(pathlib.Path(tempfile.mkdtemp()))
    print("the disk carries the music under $4000")
