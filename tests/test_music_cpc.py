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
"""Music played by the interrupt on an Amstrad, where there are six of them.

This machine interrupts three hundred times a second and a tune wants playing
fifty, so five interrupts in six do nothing but count -- and it is the one
machine here that keeps mode one, because with both ROMs out of the way $0038
is our own memory.  What is checked is what is checked everywhere: the tune
moves on while the main loop only counts.

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

CPC = os.path.join(ROOT, "z80", "cpc")
SOURCE = os.path.join(CPC, "test_music.asm")
BINARY = os.path.join(CPC, "music.bin")
LISTING = os.path.join(CPC, "music.lst")
LOADS_AT = 0x4000

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
    where = watched(emulator.assemble(SOURCE, listing=LISTING), "music_rate")
    with open(BINARY, "rb") as f:
        blob = f.read()

    session = emulator.Session(machine="CPC6128")
    try:
        time.sleep(3.0)
        assert session.start_code(blob, LOADS_AT, where["playing_flag"]), (
            "the build never started"
        )
        low, high = session.read(where["music_rate"], 2)
        assert high << 8 | low == 300, "the Amstrad forgot how often it wakes"
        plays_while_counting(session, where, "the Amstrad")
    finally:
        session.close()


if __name__ == "__main__":
    test_the_interrupt_plays_while_the_loop_only_counts()
    print("the interrupt plays the tune")
