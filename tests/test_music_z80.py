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
"""Music played by the interrupt while the game gets on with something else.

The build this loads does nothing at all but count: it starts a tune and then
spins on a sixteen-bit sum for ever.  Nothing in that loop touches the sound
chip, so if the tune moves on anyway, it is the interrupt playing it -- which
means the mode two table is where it should be, the routine the machine jumps
to is in a page that never moves, and the player is reading a tune that no
bank switching can take away from it.  That is the whole of what a machine has
to get right before music can be turned on in the interpreter.

Arkos Tracker's players are MIT and travel with us in z80/arkos/; a tune is
somebody's music and does not, so this asks for one in music/ and steps aside
when there is none.  Any song exported from Arkos Tracker 3 as an AKM source
will do.

The three other machines ask the same question of themselves, in
test_music_cpc.py, test_music_msx.py and test_music_next.py, and use the
looking done here.
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

SPECTRUM = os.path.join(ROOT, "z80", "spectrum")
SOURCE = os.path.join(SPECTRUM, "test_music.asm")
SNAPSHOT = os.path.join(SPECTRUM, "music.sna")
LISTING = os.path.join(SPECTRUM, "music.lst")
TUNE = os.path.join(ROOT, "music", "test.asm")

# The tune's own working variables, which the player moves as it goes: where
# in the first channel's track it has got to, and what the three volumes are.
WATCHED = ("playing_flag", "spins",
           "PLY_AKM_Track1_PtTrack",
           "PLY_AKM_Track1_Volume",
           "PLY_AKM_Track2_Volume",
           "PLY_AKM_Track3_Volume")

if pytest is not None:
    needs_tools = pytest.mark.skipif(
        not emulator.available() or not os.path.exists(TUNE),
        reason="sjasmplus and ZEsarUX must be in tools/, with a tune in music/",
    )
else:

    def needs_tools(func):
        return func


def word(session, address):
    low, high = session.read(address, 2)
    return high << 8 | low


def watched(listing, *also):
    """Where the build keeps what is worth looking at."""
    return {name: emulator.label_address(listing, name)
            for name in WATCHED + also}


def plays_while_counting(session, where, machine):
    """Six looks half a second apart.  The counter says the main loop is
    running; the track pointer and the volumes say the player is running too,
    and the main loop is not the one calling it."""
    assert session.read(where["playing_flag"], 1)[0] == 0xFF, (
        f"{machine}: the build never got past starting the tune"
    )
    spins, places, volumes = [], set(), set()
    for _ in range(6):
        time.sleep(0.5)
        spins.append(word(session, where["spins"]))
        places.add(word(session, where["PLY_AKM_Track1_PtTrack"]))
        volumes.add(tuple(session.read(where[f"PLY_AKM_Track{c}_Volume"], 1)[0]
                          for c in (1, 2, 3)))

    assert len(set(spins)) > 1, f"{machine}: the main loop stopped counting: {spins}"
    assert len(places) > 1, (
        f"{machine}: the tune never moved on, so nothing is being played: {places}"
    )
    assert len(volumes) > 1, (
        f"{machine}: the volumes never changed, so the chip is not being fed:"
        f" {volumes}"
    )


@needs_tools
def test_the_interrupt_plays_while_the_loop_only_counts():
    where = watched(emulator.assemble(SOURCE, listing=LISTING))
    session = emulator.Session(machine="128k")
    try:
        session.load(SNAPSHOT)
        time.sleep(1.0)
        plays_while_counting(session, where, "the Spectrum")
    finally:
        session.close()


if __name__ == "__main__":
    test_the_interrupt_plays_while_the_loop_only_counts()
    print("the interrupt plays the tune")
