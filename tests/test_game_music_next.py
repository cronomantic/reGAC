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
"""A whole adventure played with the music on, on a Spectrum Next.

The map here looked full, and then it turned out to have seven kilobytes going
spare in the least likely place: this machine draws on layer 2, so the sixteen
kilobytes where a Spectrum keeps its screen hold nothing at all.  The player
goes at $4000, in the same page as what is resident of the database, and what
is left over up to the ROM's variables is the buffer a tune is played out of.
The tunes themselves are in two pages of their own, which this machine has by
the hundred, and the one being played is copied into the buffer when it
starts -- so what this looks at is where the player is reading.

What is checked is what the other machines are checked for: the adventure
asked for a tune, the interrupt is playing it, and the game goes on being a
game while it does -- here at twenty eight megahertz, where a frame is eight
times the work and the player is the same fifty calls a second.
"""

import json
import os
import sys

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
from test_game_next import (ADVENTURE, DATABASE, DEFS, IMAGE,  # noqa: E402
                            LISTING, SOURCE, glyph_table, screen,
                            wait_screen)
from test_music_z80 import TUNE, word  # noqa: E402

EFFECTS = os.path.join(ROOT, "music", "effects.asm")

MUSIC_CEILING = 0x5C00          # where the music's own room ends

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
    database = Database(ddb, machine="next", page_bits=14)
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
                          "PLY_AKM_Track1_PtTrack")}
    prompt = ddb["messages"]["240"].strip()[:3]
    puzzled = ddb["messages"][NOT_UNDERSTOOD]

    session = emulator.Session(machine="TBBlue")
    try:
        session.load(IMAGE)
        opening = wait_screen(session, glyphs, prompt)
        assert any(prompt in line for line in opening if line), (
            f"the interpreter never asked: {opening}"
        )

        assert session.read(where["music_playing"], 1)[0] == 1, (
            "the adventure asked for a tune and nothing is playing"
        )
        assert session.read(where["music_tune"], 1)[0] == 0
        # Watched rather than glanced at: the flag above is ours and this
        # pointer is the player's, and the player only moves it on its first
        # pass through the interrupt, a frame or so after the flag.  Read at
        # the wrong instant it is still zero, and then this says the music
        # never started when it had -- measured, it comes good a quarter of a
        # second later and then walks the tune.
        at = emulator.until(
            lambda: word(session, where["PLY_AKM_Track1_PtTrack"]),
            lambda seen: where["music_buffer"] <= seen < MUSIC_CEILING,
            timeout=10.0, every=0.1)
        assert where["music_buffer"] <= at < MUSIC_CEILING, (
            f"the player is not reading the buffer the tune was copied into:"
            f" ${at:04X}"
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
        session.type(PASSWORD + ENTER)
        wait_screen(session, glyphs, ddb["locations"]["1"]["desc"][:12], timeout=30.0)
        # And then until it is asking again, because the description is
        # still going out and a key pressed while it is has nowhere to go.
        emulator.asked(lambda: screen(session, glyphs), ddb["messages"]["240"])
        # Where the tune is just before the parser is given something to do,
        # so that what is compared is one turn of it and not a whole game: the
        # track loops, and over long enough it comes back to where it started.
        was = word(session, where["PLY_AKM_Track1_PtTrack"])
        session.type("XYZZY" + ENTER)
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
