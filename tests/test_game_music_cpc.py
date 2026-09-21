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
"""A whole adventure played with the music on, on an Amstrad.

This is the machine that had no room for it.  Above $4000 the code and the
database are one stretch and the firmware's variables stop them at $B100,
because the tape is saved through its jumpblock; and the sixteen kilobytes
under $4000, which are empty and ours once both ROMs are out of the way, could
not be loaded into, because the BASIC line that loads the game is itself at
$0170 and a file landing down there would fall on the loader while it ran.

What gets round it is a mover.  The music travels as a second file with twenty
instructions in front of it: the loader brings it in at $4000, where nothing
is yet, calls it, and it carries the music down to $0300 -- clear of the BASIC
line -- and comes back.  Then the interpreter is loaded over the top and
started, and finds the music waiting.  Here the two files are put where they
belong directly, which is what the mover does and all it does; what is being
asked is whether an adventure plays with three hundred interrupts a second
going on underneath it.
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
from test_game_cpc import (ADVENTURE, BINARY, DATABASE, LISTING,  # noqa: E402
                           LOADS_AT, SOURCE, assembled, glyph_table, put,
                           screen, wait_screen)
from regac.media import CPC_LOW_ISLAND_AT  # noqa: E402
from test_music_z80 import TUNE, word  # noqa: E402

MUSIC_BINARY = os.path.join(ROOT, "z80", "cpc", "game_music.bin")
EFFECTS = os.path.join(ROOT, "music", "effects.asm")

ENTER = chr(13)
# Its own code, which is in its own vocabulary: room 5000 takes verb 29,
# and verb 29 of MegaCorp is REBECA.
PASSWORD = "REBECA"
NOT_UNDERSTOOD = "242"
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


def build():
    """The adventure with one condition of our own in front of its own: play
    the first tune on the first turn and never again."""
    with open(ADVENTURE, encoding="utf-8") as f:
        ddb = json.load(f)
    ddb["hpcs"] = compile_block(
        [f"IF ( RES? {A_FLAG} ) SET {A_FLAG} MUSIC 0 END"]
    ) + ddb["hpcs"]
    database = Database(ddb, machine="cpc")
    with open(DATABASE, "wb") as f:
        f.write(database.build())
    listing, low = assembled(("WITH_MUSIC", "WITH_EFFECTS"))
    return ddb, database, listing, low


@needs_tools
def test_an_adventure_plays_with_the_music_on():
    ddb, database, listing, low = build()
    glyphs = glyph_table(database)
    where = {name: emulator.label_address(listing, name)
             for name in ("music_playing", "music_tune", "music_at", "music_end",
                          "music_mover", "music_image", "music_rate",
                          "PLY_AKM_Track1_PtTrack")}
    prompt = ddb["messages"]["240"].strip()[:3]
    puzzled = ddb["messages"][NOT_UNDERSTOOD]

    with open(BINARY, "rb") as f:
        game = f.read()
    with open(MUSIC_BINARY, "rb") as f:
        # Past the mover, which is what the mover would have left at $0300.
        music = f.read()[where["music_image"] - where["music_mover"]:]

    session = emulator.Session(machine="CPC6128")
    try:
        time.sleep(3.0)
        # Where the music ends up is read from the listing, so it follows
        # the build: $0300 the usual way round, and up under the island when
        # the interpreter has taken the low memory instead.
        put(session, music, where["music_at"])
        put(session, game, LOADS_AT)
        session.jump(LOADS_AT)
        if low:
            time.sleep(0.5)
            with open(DATABASE, "rb") as f:
                put(session, f.read(), LOADS_AT)
            session.jump(CPC_LOW_ISLAND_AT)

        opening = wait_screen(session, glyphs, prompt)
        assert any(prompt in line for line in opening if line), (
            f"the interpreter never asked: {opening}"
        )
        assert session.read(where["music_playing"], 1)[0] == 1, (
            "the adventure asked for a tune and nothing is playing"
        )
        assert word(session, where["music_rate"]) == 300, (
            "the Amstrad forgot how often it wakes up"
        )
        at = word(session, where["PLY_AKM_Track1_PtTrack"])
        assert where["music_at"] <= at < where["music_end"], (
            f"the player is not reading the music under $4000: ${at:04X}"
        )

        # Past its own code first.  While the game is still asking for it,
        # its high priority table looks at every turn, and a description is
        # written over the line it starts on, so the complaint below would be
        # covered as soon as it is printed -- which is what the original does
        # there too, watched on it.
        # Not a key until it is asking and has been for a look: see
        # emulator.asked.
        emulator.asked(lambda: screen(session, glyphs),
                       ddb["messages"]["240"])
        session.type_keys(PASSWORD + ENTER)
        wait_screen(session, glyphs, ddb["locations"]["1"]["desc"][:12], timeout=30.0)
        # And then until it is asking again, because the description is
        # still going out and a key pressed while it is has nowhere to go.
        emulator.asked(lambda: screen(session, glyphs), ddb["messages"]["240"])
        session.type_keys("XYZZY" + ENTER)
        answered = wait_screen(session, glyphs, puzzled[:6], timeout=30.0)
        assert any(puzzled[:6] in line for line in answered), (
            f"the parser stopped answering with the music on: {answered}"
        )
        assert word(session, where["PLY_AKM_Track1_PtTrack"]) != at, (
            "the tune stopped while the adventure was played"
        )
    finally:
        session.close()


if __name__ == "__main__":
    test_an_adventure_plays_with_the_music_on()
    print("an adventure plays with the music on")
