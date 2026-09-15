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
"""Music played by the interrupt on an MSX, which has none to spare.

Two things are this machine's own and both are checked here.  The interpreter
takes all sixty four kilobytes, so what is at $0038 is the database and a mode
one interrupt would run it as instructions: the build takes the machine that
same way before it plays a note, and the tune still has to move on.  And the
rate is not known until it runs -- fifty a second on a European television,
sixty on a Japanese or American one -- so the machine reads it out of the BIOS
before the BIOS is paged away, and what it made of it is compared against what
the ROM of the emulated machine actually says.

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
from test_music_z80 import TUNE, plays_while_counting, watched, word  # noqa: E402

MSX = os.path.join(ROOT, "z80", "msx")
SOURCE = os.path.join(MSX, "test_music.asm")
BINARY = os.path.join(MSX, "music.bin")
LISTING = os.path.join(MSX, "music.lst")
LOADS_AT = 0x8000

ROM_VERSION = 0x002B     # bit 7: a machine built for a fifty hertz television

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
    where = watched(emulator.assemble(SOURCE, listing=LISTING),
                    "machine_hertz", "music_rate")
    with open(BINARY, "rb") as f:
        blob = f.read()

    session = emulator.Session(machine="MSX1")
    try:
        time.sleep(7.0)                 # this one takes its time coming up
        # What the BIOS says, while the BIOS is still the thing at $002B.
        says = 50 if session.read(ROM_VERSION, 1)[0] & 0x80 else 60
        assert session.start_code(blob, LOADS_AT, where["playing_flag"]), (
            "the build never started"
        )
        assert word(session, where["machine_hertz"]) == says, (
            "the machine read the wrong television out of its own ROM"
        )
        assert word(session, where["music_rate"]) == says, (
            "and the music was never told"
        )
        plays_while_counting(session, where, "the MSX")
    finally:
        session.close()


if __name__ == "__main__":
    test_the_interrupt_plays_while_the_loop_only_counts()
    print("the interrupt plays the tune")
