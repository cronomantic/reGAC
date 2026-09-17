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
"""Saving and loading a game on the MSX's cassette, which is the BIOS's.

The emulator can play a tape but not record one, so the two directions are
watched apart, as they are on the Amstrad.  Writing is watched going out: the
block is handed to the BIOS and what is checked is that it comes back saying
it wrote it.  Reading is watched coming in, off a tape with a block of known
bytes on it, and those bytes are compared one by one with what landed.

Both of them watch the thing that is this machine's own, though, and it is
worth saying what it is.  The interpreter runs with RAM in all four pages, so
the BIOS is not in the machine at all; each of these routines has to put it
back, use it, and take it away again -- and take it away with the interrupts
off, because an interrupt with our own map in place is a jump to $0038, where
there is no BIOS any more.  The build these tests run is taken whole in just
that way and has no database in it at all, so if that discipline slipped the
machine would go off into empty memory and nothing would ever finish.  That
anything finishes is half of what is being checked.
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
from regac.media import msx_block  # noqa: E402

MSX = os.path.join(ROOT, "z80", "msx")
SOURCE = os.path.join(MSX, "test_tape.asm")
BINARY = os.path.join(MSX, "tape.bin")
LISTING = os.path.join(MSX, "tape.lst")
TAPE = os.path.join(MSX, "save.cas")

LOADS_AT = 0x8000
BLOCK_LEN = 64
OUR_SLOTS = 0xAA                # RAM in all four pages, which is what we run in
SAVING, LOADING = 0, 1

if pytest is not None:
    needs_tools = pytest.mark.skipif(
        not emulator.available(),
        reason="sjasmplus and ZEsarUX must be in tools/",
    )
else:

    def needs_tools(func):
        return func


def build():
    listing = emulator.assemble(SOURCE, listing=LISTING)
    return {
        name: emulator.label_address(listing, name)
        for name in ("wanted", "ready_flag", "carry_seen", "slots_after",
                     "done_flag", "block", "load_area")
    }


def started(session, where, wanted):
    """Put the build in the machine, say which of the two to do, and start
    it."""
    with open(BINARY, "rb") as f:
        blob = f.read()
    for at in range(0, len(blob), 512):
        session.command(
            f"write-memory-raw {LOADS_AT + at} " + blob[at:at + 512].hex().upper()
        )
    session.command(f"write-memory-raw {where['wanted']} {wanted:02X}")
    session.jump(LOADS_AT)
    time.sleep(1.0)
    assert session.read(where["ready_flag"], 1)[0] == 1, "the build never started"


def waited(session, where, seconds):
    """Let the tape take its time, and say whether it finished.  Writing is
    not hurried along by the emulator the way reading is: the lead alone is
    seconds of it, one bit at a time, as it would be on a real machine."""
    deadline = time.time() + seconds
    while time.time() < deadline:
        time.sleep(1.0)
        if session.read(where["done_flag"], 1)[0] == 0xFF:
            return True
    return False


def gave_the_machine_back(session, where):
    """Whatever it did, the map has to be ours again and the interrupts off."""
    assert session.read(where["slots_after"], 1)[0] == OUR_SLOTS, (
        "the BIOS was left in the machine"
    )
    assert "IFF--" in session.command("get-registers"), (
        "the interrupts were left on, and $0038 is not the BIOS any more"
    )


@needs_tools
def test_it_writes_a_block():
    where = build()
    session = emulator.Session(machine="MSX1")
    try:
        time.sleep(7.0)
        started(session, where, SAVING)
        assert waited(session, where, 90), "the BIOS never gave it back"
        assert session.read(where["carry_seen"], 1)[0] == 1, "it says it did not write"
        assert session.read(where["block"], BLOCK_LEN) == bytes(range(BLOCK_LEN)), (
            "what it was asked to write came back changed"
        )
        gave_the_machine_back(session, where)
    finally:
        session.close()


@needs_tools
def test_it_reads_a_block_off_a_tape():
    where = build()
    wanted = bytes((index * 7 + 3) & 0xFF for index in range(BLOCK_LEN))
    with open(TAPE, "wb") as f:
        f.write(bytes(msx_block(bytearray(), wanted)))

    session = emulator.Session(machine="MSX1", extra=["--tape", TAPE])
    try:
        time.sleep(7.0)
        started(session, where, LOADING)
        assert waited(session, where, 60), "nothing ever came off the tape"
        assert session.read(where["carry_seen"], 1)[0] == 1, "it says it did not read"
        assert session.read(where["load_area"], BLOCK_LEN) == wanted
        gave_the_machine_back(session, where)
    finally:
        session.close()


if __name__ == "__main__":
    test_it_writes_a_block()
    print("it writes a block")
    test_it_reads_a_block_off_a_tape()
    print("it reads a block off a tape")
