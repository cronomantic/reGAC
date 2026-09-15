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
"""Music played by the interrupt on a Spectrum Next.

The chip is the Spectrum's, at the same ports and the same clock, so the
player is the Spectrum's too and what is left to get right is where the
interrupt can live: this map has a window at the bottom and layer 2 at the
top, and only $8000 to $BFFF stays put.  The tune is started at twenty eight
megahertz, which is where the interpreter runs, and then nothing but a counter
runs at all.

A tune is somebody's music and is not this project's to carry, so this asks
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
from test_music_z80 import TUNE, plays_while_counting, watched  # noqa: E402

NEXT = os.path.join(ROOT, "z80", "next")
SOURCE = os.path.join(NEXT, "test_music.asm")
IMAGE = os.path.join(NEXT, "music.nex")
LISTING = os.path.join(NEXT, "music.lst")

if pytest is not None:
    needs_tools = pytest.mark.skipif(
        not emulator.available() or not os.path.exists(TUNE),
        reason="sjasmplus and ZEsarUX must be in tools/, with a tune in music/",
    )
else:

    def needs_tools(func):
        return func


@needs_tools
def test_the_interrupt_plays_while_the_loop_only_counts():
    where = watched(emulator.assemble(SOURCE, listing=LISTING))
    session = emulator.Session(machine="TBBlue")
    try:
        session.load(IMAGE)
        time.sleep(1.5)
        plays_while_counting(session, where, "the Next")
    finally:
        session.close()


if __name__ == "__main__":
    test_the_interrupt_plays_while_the_loop_only_counts()
    print("the interrupt plays the tune")
