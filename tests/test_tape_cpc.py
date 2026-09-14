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
"""Saving and loading on the Amstrad, through the firmware's own cassette.

The emulator can play a tape but not record one, so the two directions are
watched apart.  Writing is watched going out: the block is handed to the
firmware and what is checked is that it comes back saying it wrote it, with
the machine still ours.  Reading is watched coming in, off a real tape: the
first block of data on the Megacorp cassette is read into memory and compared
against the same bytes taken out of the tape image here, which proves the
whole path and not just that something happened.
"""

import os
import shutil
import sys
import tempfile
import time
import zipfile

try:
    import pytest
except ImportError:
    pytest = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import emulator  # noqa: E402

CPC = os.path.join(ROOT, "z80", "cpc")
SOURCE = os.path.join(CPC, "test_tape.asm")
BINARY = os.path.join(CPC, "tape.bin")
LISTING = os.path.join(CPC, "tape.lst")
DATABASE = os.path.join(CPC, "text.rgac")
TAPE = os.path.join(ROOT, "juegos", "megacorp_ams.zip")
LOADS_AT = 0x4000
LOAD_LEN = 256

if pytest is not None:
    needs_tools = pytest.mark.skipif(
        not emulator.available() or not os.path.exists(DATABASE),
        reason="sjasmplus and ZEsarUX must be in tools/, with a database built",
    )
    needs_tape = pytest.mark.skipif(
        not emulator.available() or not os.path.exists(DATABASE)
        or not os.path.exists(TAPE),
        reason="the Amstrad tape of Megacorp must be in juegos/",
    )
else:

    def needs_tools(func):
        return func

    needs_tape = needs_tools


def build():
    listing = emulator.assemble(SOURCE, listing=LISTING)
    return {
        name: emulator.label_address(listing, name)
        for name in ("wanted", "ready_flag", "carry_seen", "done_flag",
                     "block", "load_area")
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
    session.command(f"write-memory {where['wanted']} {wanted}")
    session.command(f"set-register PC={LOADS_AT:04X}H")
    time.sleep(1.0)
    assert session.read(where["ready_flag"], 1)[0] == 1, "the build never started"


def waited(session, where, seconds):
    """Let the tape take its time, and say whether it finished."""
    deadline = time.time() + seconds
    while time.time() < deadline:
        time.sleep(1.0)
        if session.read(where["done_flag"], 1)[0] == 0xFF:
            return True
    return False


def blocks_of(tape):
    """The blocks of a tape image, as the bytes that were on the tape."""
    with open(tape, "rb") as f:
        data = f.read()
    assert data[:7] == b"ZXTape!", "not a tape image"
    at, found = 10, []
    while at < len(data):
        kind, at = data[at], at + 1
        if kind == 0x11:                        # a block written at its own speed
            head, at = data[at:at + 0x12], at + 0x12
            length = head[0x0F] | head[0x10] << 8 | head[0x11] << 16
            found.append(data[at:at + length])
            at += length
        elif kind == 0x20:                      # a silence
            at += 2
        elif kind == 0x30:                      # something written for a person
            at += 1 + data[at]
        else:
            break
    return found


@needs_tools
def test_it_writes_a_block():
    where = build()
    session = emulator.Session(machine="CPC6128")
    try:
        time.sleep(3.5)
        started(session, where, 0)
        assert waited(session, where, 45), "the firmware never gave it back"
        assert session.read(where["carry_seen"], 1)[0] == 1, "it says it did not write"
        # and the machine is ours again: interrupts off, as the runtime needs
        assert "IFF--" in session.command("get-registers")
    finally:
        session.close()


@needs_tape
def test_it_reads_a_block_off_a_real_tape():
    where = build()
    folder = tempfile.mkdtemp()
    try:
        with zipfile.ZipFile(TAPE) as archive:
            inside = [n for n in archive.namelist() if n.lower().endswith(".cdt")][0]
            image = os.path.join(folder, "tape.cdt")
            with open(image, "wb") as f:
                f.write(archive.read(inside))
        # The first block of the tape is the file's header and the second is
        # its data, which is the one the firmware is asked for.
        wanted = [b for b in blocks_of(image) if b[:1] == b"\x16"][0][1:1 + LOAD_LEN]

        session = emulator.Session(
            machine="CPC464",
            extra=["--realtape", image, "--fastautoload", "--simulaterealloadfast"],
        )
        try:
            time.sleep(3.5)
            started(session, where, 1)
            assert waited(session, where, 75), "nothing ever came off the tape"
            assert session.read(where["carry_seen"], 1)[0] == 1, "it says it did not read"
            assert session.read(where["load_area"], LOAD_LEN) == wanted
        finally:
            session.close()
    finally:
        shutil.rmtree(folder, ignore_errors=True)


if __name__ == "__main__":
    test_it_writes_a_block()
    print("it writes a block")
    test_it_reads_a_block_off_a_real_tape()
    print("it reads a block off a real tape")
