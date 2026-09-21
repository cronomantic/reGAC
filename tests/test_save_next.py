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
"""Saving and loading a game on a Spectrum Next, through the Spectrum's ROM.

The emulator plays tapes and does not record them, so the two directions are
watched apart, as they are on the Amstrad and the MSX.  Writing is watched
going out: the block is handed to the ROM and what is checked is that it comes
back saying it wrote it.  Reading is watched coming in, off a real tape with a
block of known bytes on it, compared one by one with what landed.

What is this machine's own is that the ROM is not in the machine.  The first
sixteen kilobytes are the window a bank of the database appears in, so each of
these routines has to bring the ROM back, use it, and put the window back
afterwards -- and both tests look at the register that owns that window when
it is over, because a save that left the ROM there would take the database
away with it and nothing would say so until the next room.
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

NEXT = os.path.join(ROOT, "z80", "next")
SOURCE = os.path.join(NEXT, "test_tape.asm")
BINARY = os.path.join(NEXT, "tape.bin")
LISTING = os.path.join(NEXT, "tape.lst")
TAPE = os.path.join(NEXT, "save.tap")

BLOCK_LEN = 64
WINDOW_PAGE = 32                # what the build leaves in the window
SAVING, LOADING = 0, 1

# The ROM wants the machine it was written for.  A Next that has booted its
# own operating system has one -- which is how a .nex is ever started -- but a
# cold TBBlue in the emulator does not: nothing has set the variables the tape
# routines read, and the one at the end of them sends the machine into BASIC
# instead of back to us.  This is the emulator's way of giving us a machine
# that has been through a boot, with all the Next's features still on.
BOOTED = ("--tbblue-fast-boot-mode",)

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
        for name in ("wanted", "ready_flag", "carry_seen", "mmu0_after",
                     "done_flag", "block", "load_area")
    }


def a_tape(data):
    """A tape with one block of data on it, which is what a saved game is: the
    mark that says data rather than header, the bytes, and the sum of them
    all."""
    body = bytes([0xFF]) + bytes(data)
    check = 0
    for byte in body:
        check ^= byte
    block = body + bytes([check])
    return len(block).to_bytes(2, "little") + block


LOADS_AT = 0x8000


def started(session, where, wanted):
    """Put the build in the machine, say which of the two to do, and start it.

    It is written in rather than loaded as a file, and that is not a detail:
    loading anything over an inserted tape leaves the tape where the ROM can
    no longer read it, which looks exactly like a routine that does not work.
    """
    # Not grown for the company, although everything else is: one of the two
    # tests this serves has a tape inserted and running, and a tape does not
    # wait for a machine that is sharing a processor with three others.
    # Waiting longer leaves the block already gone past, and then the routine
    # looks as though it could not read one.  Measured: scaling it failed both
    # rounds of the suite.
    time.sleep(3.0)
    with open(BINARY, "rb") as f:
        blob = f.read()
    for at in range(0, len(blob), 512):
        session.command(
            f"write-memory-raw {LOADS_AT + at} " + blob[at:at + 512].hex().upper()
        )
    session.command(f"write-memory-raw {where['wanted']} {wanted:02X}")
    session.jump(LOADS_AT)
    time.sleep(emulator.longer(1.0))
    assert session.read(where["ready_flag"], 1)[0] == 1, "the build never started"


def waited(session, where, seconds):
    deadline = time.time() + seconds
    while time.time() < deadline:
        time.sleep(0.5)
        if session.read(where["done_flag"], 1)[0] == 0xFF:
            return True
    return False


def gave_the_window_back(session, where):
    assert session.read(where["mmu0_after"], 1)[0] == WINDOW_PAGE, (
        "the ROM was left where the database's window belongs"
    )


@needs_tools
def test_it_writes_a_block():
    where = build()
    session = emulator.Session(machine="TBBlue", extra=list(BOOTED))
    try:
        started(session, where, SAVING)
        assert waited(session, where, 90), "the ROM never gave it back"
        assert session.read(where["carry_seen"], 1)[0] == 1, "it says it did not write"
        assert session.read(where["block"], BLOCK_LEN) == bytes(range(BLOCK_LEN)), (
            "what it was asked to write came back changed"
        )
        gave_the_window_back(session, where)
    finally:
        session.close()


@needs_tools
def test_it_reads_a_block_off_a_tape():
    where = build()
    wanted = bytes((index * 7 + 3) & 0xFF for index in range(BLOCK_LEN))
    with open(TAPE, "wb") as f:
        f.write(a_tape(wanted))

    session = emulator.Session(machine="TBBlue",
                               extra=["--tape", TAPE] + list(BOOTED))
    try:
        started(session, where, LOADING)
        assert waited(session, where, 90), "nothing ever came off the tape"
        assert session.read(where["carry_seen"], 1)[0] == 1, "it says it did not read"
        assert session.read(where["load_area"], BLOCK_LEN) == wanted
        gave_the_window_back(session, where)
    finally:
        session.close()


if __name__ == "__main__":
    test_it_writes_a_block()
    print("it writes a block")
    test_it_reads_a_block_off_a_tape()
    print("it reads a block off a tape")
