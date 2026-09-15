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
"""The tape of a 128 with music on it, loaded the way a person would.

A snapshot proves the playing and nothing else.  What this proves is the two
blocks the music travels in and where they land: the player and its buffer go
below the interpreter, in the page that is always there, and the tunes go into
a page of their own -- the one after the last the database took.  Neither is
reachable when the other is being loaded, and the loader itself is down there
among them, in the BASIC line it travelled in, which is why the music's blocks
come after the interpreter's in the table rather than before.

If any of that is wrong the tape still loads and the adventure still plays;
what does not happen is a tune.  So this loads the tape by typing LOAD "",
waits for the adventure to be playing, and then looks at where the player has
got to: inside the buffer, which is the one place a tune can only be if it was
copied there out of its page.
"""

import json
import os
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
from test_game_z80 import glyph_table, wait_screen  # noqa: E402
from test_music_z80 import TUNE, word  # noqa: E402
from test_tape_z80 import TAPE_FLAGS, build, written  # noqa: E402

SPECTRUM = os.path.join(ROOT, "z80", "spectrum")
ADVENTURE = os.path.join(ROOT, "snapshots", "Bangkok1.json")
TAPE = os.path.join(SPECTRUM, "game128.tap")
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
def test_the_tape_carries_the_tunes_to_their_page():
    with open(ADVENTURE, encoding="utf-8") as f:
        ddb = json.load(f)
    ddb["hpcs"] = compile_block(
        [f"IF ( RES? {A_FLAG} ) SET {A_FLAG} MUSIC 0 END"]
    ) + ddb["hpcs"]

    listing = build(
        written(ddb),
        os.path.join(SPECTRUM, "game128.rgac"),
        "spectrum128",
        os.path.join(SPECTRUM, "game128.asm"),
        os.path.join(SPECTRUM, "game128.lst"),
        banks="16k",
        defs=os.path.join(SPECTRUM, "banks.inc"),
        defines=("WITH_MUSIC", "WITH_EFFECTS"),
    )
    where = {name: emulator.label_address(listing, name)
             for name in ("music_playing", "music_buffer", "start",
                          "PLY_AKM_Track1_PtTrack")}
    glyphs = glyph_table(Database(ddb, machine="spectrum128", page_bits=14))
    described = ddb["locations"][str(ddb["init_loc"])]["desc"].strip()

    session = emulator.Session(machine="128k", extra=TAPE_FLAGS)
    try:
        session.load(TAPE)
        # The end of the description and not the start: this one is long
        # enough that its first lines have scrolled off by then.
        arrived = wait_screen(session, glyphs, described[-16:], timeout=180.0)
        assert any(described[-16:] in line for line in arrived), (
            f"the tape never got as far as playing: {arrived}"
        )

        assert session.wait_for(where["music_playing"], 1, timeout=30.0), (
            "it loaded and played, but the tune never started"
        )
        at = word(session, where["PLY_AKM_Track1_PtTrack"])
        assert where["music_buffer"] <= at < where["start"], (
            f"the player is not reading the buffer, so the tunes did not"
            f" arrive in their page: ${at:04X}"
        )
        was = at
        deadline = time.time() + 5.0
        while time.time() < deadline and word(session, where["PLY_AKM_Track1_PtTrack"]) == was:
            time.sleep(0.2)
        assert word(session, where["PLY_AKM_Track1_PtTrack"]) != was, (
            "the tune was copied but never moved on"
        )
    finally:
        session.close()


if __name__ == "__main__":
    test_the_tape_carries_the_tunes_to_their_page()
    print("the tape carries the tunes to their page")
