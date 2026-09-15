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
"""The whole way from what the author writes to a tune coming out.

An adventure says what music it has in its own source, in a section of its
own, one line to a tune: the file the tracker exported and which of its
subsongs to play.  `regac build` turns that into the little assembly source
the build includes -- the list in one half, the tunes in the other, each in a
module of its own and each assembled for the buffer -- and from there it is
the machine's business.

Nothing of that is visible on a screen, so what this does is the author's own
round: write the source, build it, assemble it, and then look at whether the
tune is playing and whether the two lines that name the same export really
became one copy of it and two tunes.
"""

import json
import os
import subprocess
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
from regac.srcgen import generate  # noqa: E402
from regac.srcparse import parse  # noqa: E402
from test_music_z80 import TUNE, word  # noqa: E402

SPECTRUM = os.path.join(ROOT, "z80", "spectrum")
MUSIC = os.path.join(ROOT, "music")
SOURCE = os.path.join(SPECTRUM, "game128.asm")
DATABASE = os.path.join(SPECTRUM, "game128.rgac")
SNAPSHOT = os.path.join(SPECTRUM, "game128.sna")
LISTING = os.path.join(SPECTRUM, "game128.lst")
DEFS = os.path.join(SPECTRUM, "banks.inc")
ADVENTURE = os.path.join(ROOT, "snapshots", "Bangkok1.json")
EFFECTS = os.path.join(MUSIC, "effects.asm")

# What the author's own folder holds, and what regac writes into it.
WRITTEN = os.path.join(MUSIC, "tunes.asm")
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


def test_the_source_keeps_what_the_author_wrote():
    """Two tunes out of one export and one out of another, written to a source
    and read back."""
    ddb = json.loads(json.dumps({"music": [
        {"file": "menu.akm.asm", "subsong": 0},
        {"file": "menu.akm.asm", "subsong": 1},
        {"file": "cueva.akm.asm", "subsong": 0},
    ]}))
    with open(ADVENTURE, encoding="utf-8") as f:
        whole = json.load(f)
    whole["music"] = ddb["music"]
    again = parse(generate(whole))
    assert again["music"] == ddb["music"]


@needs_tools
def test_an_adventure_says_what_tunes_it_has_and_they_play():
    with open(ADVENTURE, encoding="utf-8") as f:
        ddb = json.load(f)
    ddb["hpcs"] = compile_block(
        [f"IF ( RES? {A_FLAG} ) SET {A_FLAG} MUSIC 1 END"]
    ) + ddb["hpcs"]
    # The same export twice, which is what subsongs are for: one copy of the
    # bytes and two tunes.  This one has a single subsong, so both lines ask
    # for the same music -- what is being looked at is the shape of it.
    ddb["music"] = [{"file": "test.asm", "subsong": 0},
                    {"file": "test.asm", "subsong": 0}]

    # The adventure's own file goes where its tunes are, so that what it says
    # about them is what a person would write: a name and nothing else.
    source = os.path.join(MUSIC, "adventure.json")
    with open(source, "w", encoding="utf-8") as f:
        json.dump(ddb, f)
    subprocess.run(
        [sys.executable, "-m", "regac", "build", source, DATABASE,
         "-m", "spectrum128", "-b", "16k", "--defs", DEFS,
         "--music-defs", WRITTEN],
        cwd=ROOT, check=True, capture_output=True,
    )
    written = open(WRITTEN, encoding="utf-8").read()
    assert written.count("MUSIC_TUNE") == 2, written
    assert written.count('include "test.asm"') == 1, (
        f"the same export was carried twice over:\n{written}"
    )

    listing = emulator.assemble(SOURCE, listing=LISTING,
                                defines=("WITH_MUSIC", "WITH_EFFECTS"))
    where = {name: emulator.label_address(listing, name)
             for name in ("music_playing", "music_tune", "music_buffer",
                          "start", "PLY_AKM_Track1_PtTrack")}

    session = emulator.Session(machine="128k")
    try:
        session.load(SNAPSHOT)
        assert session.wait_for(where["music_playing"], 1, timeout=60.0), (
            "the adventure named its tunes and none of them played"
        )
        assert session.read(where["music_tune"], 1)[0] == 1, (
            "it played a tune, but not the one the condition asked for"
        )
        at = word(session, where["PLY_AKM_Track1_PtTrack"])
        assert where["music_buffer"] <= at < where["start"], (
            f"the player is not reading the buffer: ${at:04X}"
        )
    finally:
        session.close()
        if os.path.exists(source):
            os.remove(source)


if __name__ == "__main__":
    test_the_source_keeps_what_the_author_wrote()
    print("the source keeps what the author wrote")
    test_an_adventure_says_what_tunes_it_has_and_they_play()
    print("an adventure says what tunes it has and they play")
