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
"""A whole adventure played with the music on.

A real decompiled adventure is built for a 128 with the music in it, given one
extra condition -- play the first tune, once, on the first turn -- and then
played.  Two things are being asked at once.

The first is whether it fits at all.  Above the interpreter there is nothing
to spare: the code, what is resident of the database and the interrupt's
corner reach $C000 between them.  Below it there is a great deal of room and
nothing in it but the BASIC line the loader travelled in, which has done its
work by then, so the player goes at $6000 and what is left over up to $7C00 is
the buffer a tune is played out of.  The tunes themselves are in a page of
their own, and the one being played is copied down when it starts -- which is
what this checks by looking at where the player is reading.

The second is whether an adventure still plays with the interrupts on, which
until now it never has: it puts its title up, asks for an order and answers a
word it does not know, all of it fifty times a second slower than before and
none of it any different.
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
from test_game_z80 import glyph_table, screen, wait_screen  # noqa: E402
from test_music_z80 import TUNE, word  # noqa: E402

SPECTRUM = os.path.join(ROOT, "z80", "spectrum")
SOURCE = os.path.join(SPECTRUM, "game128.asm")
DATABASE = os.path.join(SPECTRUM, "game128.rgac")
SNAPSHOT = os.path.join(SPECTRUM, "game128.sna")
LISTING = os.path.join(SPECTRUM, "game128.lst")
DEFS = os.path.join(SPECTRUM, "banks.inc")
ADVENTURE = os.path.join(ROOT, "snapshots", "Bangkok1.json")
EFFECTS = os.path.join(ROOT, "music", "effects.asm")

ENTER = chr(13)
NOT_UNDERSTOOD = "242"          # what GAC says to a word it does not know
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
    """The adventure, with one condition of our own in front of its own: play
    the first tune on the first turn and never again."""
    with open(ADVENTURE, encoding="utf-8") as f:
        ddb = json.load(f)
    ddb["hpcs"] = compile_block(
        [f"IF ( RES? {A_FLAG} ) SET {A_FLAG} MUSIC 0 END"]
    ) + ddb["hpcs"]

    database = Database(ddb, machine="spectrum128", page_bits=14)
    with open(DATABASE, "wb") as f:
        f.write(database.build())
    with open(DEFS, "w", encoding="utf-8") as f:
        f.write("; Written by the test.\n")
        f.write(f"DB_RESIDENT_SIZE equ {database.resident_size}\n")
        f.write(f"DB_BANK_COUNT    equ {len(database.banks)}\n")
        f.write(f"DB_BANK_BYTES    equ {1 << database.page_bits if database.banks else 0}\n")
        for n, bank in enumerate(database.banks):
            f.write(f"DB_BANK_USED_{n}   equ {len(bank)}\n")
    listing = emulator.assemble(SOURCE, listing=LISTING,
                                defines=("WITH_MUSIC", "WITH_EFFECTS"))
    return ddb, database, listing


@needs_tools
def test_an_adventure_plays_with_the_music_on():
    ddb, database, listing = build()
    glyphs = glyph_table(database)
    where = {name: emulator.label_address(listing, name)
             for name in ("music_playing", "music_tune", "music_buffer",
                          "music_store", "start", "PLY_AKM_Track1_PtTrack")}
    prompt = ddb["messages"]["240"].strip()[:3]
    puzzled = ddb["messages"][NOT_UNDERSTOOD]

    session = emulator.Session(machine="128k")
    try:
        session.load(SNAPSHOT)
        # The condition is the first of the high priority ones, so the tune is
        # asked for on the very first turn, before this adventure's own title
        # has finished being put up.
        assert session.wait_for(where["music_playing"], 1, timeout=60.0), (
            "the adventure asked for a tune and nothing is playing"
        )
        assert session.read(where["music_tune"], 1)[0] == 0
        at = word(session, where["PLY_AKM_Track1_PtTrack"])
        assert where["music_buffer"] <= at < where["start"], (
            f"the player is not reading the buffer the tune was copied into:"
            f" ${at:04X}"
        )
        assert any(screen(session, glyphs)), "nothing was ever printed"

        # A key gets past the title, and then it is a game: it asks for an
        # order and answers a word it does not know.
        session.type(ENTER)
        asking = wait_screen(session, glyphs, prompt, timeout=120.0)
        assert any(prompt in line for line in asking if line), (
            f"it never asked for an order with the music on: {asking}"
        )
        # Where the tune is just before the parser is given something to do,
        # so that what is compared is one turn of it and not a whole game: the
        # track loops, and over long enough it comes back to where it started.
        was = word(session, where["PLY_AKM_Track1_PtTrack"])
        session.type("XYZZY" + ENTER)
        answered = wait_screen(session, glyphs, puzzled[:10], timeout=60.0)
        assert any(puzzled[:10] in line for line in answered if line), (
            f"the parser stopped answering with the music on: {answered}"
        )
        deadline = time.time() + 5.0
        while time.time() < deadline:
            at = word(session, where["PLY_AKM_Track1_PtTrack"])
            if at != was:
                break
            time.sleep(0.2)
        assert at != was, "the tune stopped while the adventure was played"
        assert session.read(where["music_playing"], 1)[0] == 1
    finally:
        session.close()


if __name__ == "__main__":
    test_an_adventure_plays_with_the_music_on()
    print("an adventure plays with the music on")
