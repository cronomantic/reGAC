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
"""Saving and loading a game on the Spectrum, through the ROM's tape routines.

This is SAVE and LOAD of the game, not the tape the adventure ships on: that
one is test_tape_z80.py, which loads whole .tap files the way a person does.

These were the two that had no test at all: it had been written down that the
emulator could play a tape and not record one, and that is true of the tape it
plays as sound, but not of the other kind.  ZEsarUX also takes a tape of the
standard sort in and out -- `--tape` and `--outtape` -- and traps the ROM's
own routines at both ends, which is exactly the pair this uses.  So both
directions are watched here, and against the file itself:

  - what SAVE puts out is read back out of the tape it was written to, block,
    mark and checksum;
  - what LOAD reads comes off a tape written here, byte for byte.

A block of the kind these two use has no header: a mark of $FF, the bytes,
and the exclusive or of all of it.
"""

import os
import struct
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
SOURCE = os.path.join(SPECTRUM, "test_tape.asm")
BINARY = os.path.join(SPECTRUM, "tape.bin")
LISTING = os.path.join(SPECTRUM, "tape.lst")
LOADS_AT = 0x8000
BLOCK_LEN = 64
DATA_MARK = 0xFF                # what the ROM calls a block that is not a header
WRITING, READING = 1, 2

if pytest is not None:
    needs_tools = pytest.mark.skipif(
        not emulator.available(), reason="sjasmplus and ZEsarUX must be in tools/"
    )
else:

    def needs_tools(func):
        return func


def build():
    listing = emulator.assemble(SOURCE, listing=LISTING)
    return {
        name: emulator.label_address(listing, name)
        for name in ("wanted", "ready_flag", "carry_seen", "done_flag",
                     "block", "load_area")
    }


def a_block(data, mark=DATA_MARK):
    """One block as a tape file keeps it: how long it is, the mark, the bytes
    and the exclusive or of the lot."""
    body = bytes([mark]) + bytes(data)
    check = 0
    for byte in body:
        check ^= byte
    body += bytes([check])
    return struct.pack("<H", len(body)) + body


def blocks_of(image):
    """The blocks of a tape file, each without its length."""
    found, at = [], 0
    while at + 2 <= len(image):
        length = struct.unpack("<H", image[at:at + 2])[0]
        found.append(image[at + 2:at + 2 + length])
        at += 2 + length
    return found


def started(session):
    """Put the build in the machine and start it.

    Written in rather than loaded as a snapshot, and that is the whole reason
    the reading half of this took a while to work: loading a snapshot takes
    the tape out of the machine, so the ROM was left waiting for a tape that
    was no longer there.
    """
    with open(BINARY, "rb") as f:
        blob = f.read()
    for at in range(0, len(blob), 512):
        session.command(f"write-memory-raw {LOADS_AT + at} "
                        + blob[at:at + 512].hex().upper())
    session.jump(LOADS_AT)
    time.sleep(0.5)


def ran(session, where, wanted, seconds=30.0):
    """Tell the build which of the two to do and wait for it to finish."""
    assert session.read(where["ready_flag"], 1)[0] == 1, "the build never started"
    session.command(f"write-memory {where['wanted']} {wanted}")
    deadline = time.time() + seconds
    while time.time() < deadline:
        time.sleep(0.2)
        if session.read(where["done_flag"], 1)[0] == 0xFF:
            return True
    return False


@needs_tools
def test_it_writes_a_block_to_the_tape(tmp_path):
    """What the interpreter puts on the tape is a headerless block of exactly
    the bytes it was given, with the ROM's own mark and checksum."""
    where = build()
    path = str(tmp_path / "out.tap")
    session = emulator.Session(extra=["--outtape", path])
    try:
        time.sleep(emulator.longer(3.0))
        started(session)
        assert ran(session, where, WRITING), "the ROM never gave it back"
    finally:
        session.close()

    with open(path, "rb") as f:
        image = f.read()
    assert blocks_of(image) == [a_block(range(BLOCK_LEN))[2:]], (
        f"what went on the tape is not the block that was saved: {image.hex()}"
    )


@needs_tools
def test_it_reads_a_block_off_a_tape(tmp_path):
    """And a block written here comes back into the memory it was asked for,
    byte for byte, with the ROM saying it came in whole."""
    where = build()
    path = str(tmp_path / "in.tap")
    wanted = bytes(range(100, 100 + BLOCK_LEN))
    with open(path, "wb") as f:
        f.write(a_block(wanted))

    session = emulator.Session(extra=["--tape", path])
    try:
        # Waited for by looking and not by sleeping, which matters here more
        # than anywhere: a tape starts rolling when the emulator starts and
        # does not wait, so every tenth of a second spent not looking is tape
        # gone past -- and a block that has gone past leaves the ROM waiting
        # for a leader that is never coming back, which reads as a routine
        # that could not load one.  $1200 to $16FF is the 48's command loop,
        # which is where it ends up when it has finished booting.
        assert session.wait_in(0x1200, 0x16FF), "the ROM never finished booting"
        started(session)
        assert ran(session, where, READING), "nothing ever came off the tape"
        assert session.read(where["carry_seen"], 1)[0] == 1, "it says it did not read"
        got = bytes(session.read(where["load_area"], BLOCK_LEN))
    finally:
        session.close()
    assert got == wanted, f"what came in is not what was on the tape: {got.hex()}"


@needs_tools
def test_what_it_saved_is_what_it_loads(tmp_path):
    """The whole round, which is what a person does: a game written to a tape
    and read back off that very tape, with nothing of ours in between.  Each
    half on its own only agrees with what this file believes a block is; the
    two together agree with each other."""
    where = build()
    path = str(tmp_path / "round.tap")
    session = emulator.Session(extra=["--outtape", path])
    try:
        time.sleep(emulator.longer(3.0))
        started(session)
        assert ran(session, where, WRITING), "the ROM never gave it back"
    finally:
        session.close()

    session = emulator.Session(extra=["--tape", path])
    try:
        # Waited for by looking and not by sleeping, which matters here more
        # than anywhere: a tape starts rolling when the emulator starts and
        # does not wait, so every tenth of a second spent not looking is tape
        # gone past -- and a block that has gone past leaves the ROM waiting
        # for a leader that is never coming back, which reads as a routine
        # that could not load one.  $1200 to $16FF is the 48's command loop,
        # which is where it ends up when it has finished booting.
        assert session.wait_in(0x1200, 0x16FF), "the ROM never finished booting"
        started(session)
        assert ran(session, where, READING), "nothing ever came off the tape"
        assert session.read(where["carry_seen"], 1)[0] == 1, "it says it did not read"
        got = bytes(session.read(where["load_area"], BLOCK_LEN))
    finally:
        session.close()
    assert got == bytes(range(BLOCK_LEN)), (
        f"what came back is not what was saved: {got.hex()}"
    )


if __name__ == "__main__":
    import pathlib
    import tempfile

    folder = pathlib.Path(tempfile.mkdtemp())
    test_it_writes_a_block_to_the_tape(folder)
    print("it writes a block to the tape")
    test_it_reads_a_block_off_a_tape(folder)
    print("it reads a block off a tape")
    test_what_it_saved_is_what_it_loads(folder)
    print("what it saved is what it loads")
