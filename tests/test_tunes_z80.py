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
"""More than one tune in a build, and asking for each of them.

A build says what tunes it has in a list, one line to a tune: where it is and
which of its subsongs to play.  Starting one is then a number, and that is all
an adventure will ever have to say.

What is checked is not what comes out of the sound chip but **where the player
is reading**, which is the only thing that tells one tune from another: the
pointer it keeps into the tune it is playing has to be inside that tune and
not the other.  So the build carries two of them at two addresses, the test
asks for one and then the other, and each time looks at which of the two the
pointer has landed in.  Asking for a tune the build has not got is looked at
too: it must leave the one that is playing alone rather than read whatever is
at an address that is not there.

The tune is somebody's music and is not this project's to carry, so this asks
for one in music/ and steps aside when there is none.
"""

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
from test_music_z80 import TUNE, word  # noqa: E402

SPECTRUM = os.path.join(ROOT, "z80", "spectrum")
SOURCE = os.path.join(SPECTRUM, "test_tunes.asm")
SNAPSHOT = os.path.join(SPECTRUM, "tunes.sna")
LISTING = os.path.join(SPECTRUM, "tunes.lst")

NOT_THERE = 9                   # a tune of a build that has two

WATCHED = ("playing_flag", "tune_asked", "music_tune", "PLY_AKM_Track1_PtTrack",
           "first", "first_end", "second", "second_end")

if pytest is not None:
    needs_tools = pytest.mark.skipif(
        not emulator.available() or not os.path.exists(TUNE),
        reason="sjasmplus and ZEsarUX must be in tools/, with a tune in music/",
    )
else:

    def needs_tools(func):
        return func


def reading(session, where):
    """Which of the two tunes the player is reading from."""
    at = word(session, where["PLY_AKM_Track1_PtTrack"])
    for which in ("first", "second"):
        if where[which] <= at < where[which + "_end"]:
            return which
    return f"neither, ${at:04X}"


def ask_for(session, where, tune):
    session.command(f"write-memory {where['tune_asked']} {tune}")
    time.sleep(0.3)


@needs_tools
def test_each_tune_of_a_build_can_be_asked_for():
    listing = emulator.assemble(SOURCE, listing=LISTING)
    where = {name: emulator.label_address(listing, name) for name in WATCHED}

    session = emulator.Session(machine="128k")
    try:
        session.load(SNAPSHOT)
        time.sleep(emulator.longer(1.0))
        assert session.read(where["playing_flag"], 1)[0] == 0xFF, (
            "the build never got past starting a tune"
        )
        assert session.read(where["music_tune"], 1)[0] == 0
        assert reading(session, where) == "first", (
            f"it started the wrong tune: {reading(session, where)}"
        )

        ask_for(session, where, 1)
        assert session.read(where["music_tune"], 1)[0] == 1
        assert reading(session, where) == "second", (
            f"asking for the second played {reading(session, where)}"
        )

        ask_for(session, where, 0)
        assert session.read(where["music_tune"], 1)[0] == 0
        assert reading(session, where) == "first", (
            f"asking for the first back played {reading(session, where)}"
        )

        # And one it has not got, which must change nothing.
        ask_for(session, where, NOT_THERE)
        assert session.read(where["music_tune"], 1)[0] == 0, (
            "it thinks it is playing a tune that is not in the build"
        )
        assert reading(session, where) == "first", (
            f"a tune that is not there stopped the one that was:"
            f" {reading(session, where)}"
        )
    finally:
        session.close()


if __name__ == "__main__":
    test_each_tune_of_a_build_can_be_asked_for()
    print("each tune of a build can be asked for")
