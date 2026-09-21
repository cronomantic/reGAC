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
"""A whole adventure played with the music on, on an MSX.

Here the music goes above the interpreter rather than below it, because that
is where this machine's room is: the database has the bottom half of the map
to itself and the top half holds the code, the copy of the screen and very
little else.  It travels in the same block as the interpreter, so a cassette
needs nothing said to it.

What the Spectrum's version of this test asks, this one asks too -- the tune
is playing and it is the interrupt playing it, while the adventure prints, is
typed at and answers -- and it asks one thing more that only this machine can
be asked: all of that happens with the whole sixty four kilobytes taken, which
is to say with the database sitting where a mode one interrupt would have gone.
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
from test_game_msx import (ADVENTURE, BINARY, DATABASE, LISTING,  # noqa: E402
                           SOURCE, glyph_table, start_playing, type_them,
                           screen, wait_screen)
from test_music_z80 import TUNE, word  # noqa: E402

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
    database = Database(ddb, machine="msx")
    with open(DATABASE, "wb") as f:
        f.write(database.build())
    listing = emulator.assemble(SOURCE, listing=LISTING,
                                defines=("WITH_MUSIC", "WITH_EFFECTS"))
    return ddb, database, listing


@needs_tools
def test_an_adventure_plays_with_the_music_on():
    ddb, database, listing = build()
    glyphs = glyph_table(database)
    where = {name: emulator.label_address(listing, name)
             for name in ("start", "database_ready", "music_playing",
                          "music_tune", "music_rate", "machine_hertz",
                          "PLY_AKM_Track1_PtTrack")}
    prompt = ddb["messages"]["240"].strip()[:3]
    puzzled = ddb["messages"][NOT_UNDERSTOOD]

    session = emulator.Session(machine="MSX1")
    try:
        time.sleep(7.0)
        start_playing(session, where, database.build())
        opening = wait_screen(session, glyphs, prompt)
        assert any(prompt in line for line in opening if line), (
            f"the interpreter never asked: {opening}"
        )

        assert session.read(where["music_playing"], 1)[0] == 1, (
            "the adventure asked for a tune and nothing is playing"
        )
        assert session.read(where["music_tune"], 1)[0] == 0
        assert word(session, where["music_rate"]) == word(session, where["machine_hertz"]), (
            "the music was never told how often this machine wakes up"
        )

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
        # Where the tune is just before the parser is given something to
        # do, so that what is compared below is one turn of it and not a
        # whole game: the track loops, and over long enough it can come back
        # to the very place it started from.
        was = word(session, where["PLY_AKM_Track1_PtTrack"])
        type_them(session, "XYZZY" + ENTER)
        answered = wait_screen(session, glyphs, puzzled[:6], timeout=30.0)
        assert any(puzzled[:6] in line for line in answered), (
            f"the parser stopped answering with the music on: {answered}"
        )
        assert word(session, where["PLY_AKM_Track1_PtTrack"]) != was, (
            "the tune stopped while the adventure was played"
        )
        assert session.read(where["music_playing"], 1)[0] == 1
    finally:
        session.close()


if __name__ == "__main__":
    test_an_adventure_plays_with_the_music_on()
    print("an adventure plays with the music on")
