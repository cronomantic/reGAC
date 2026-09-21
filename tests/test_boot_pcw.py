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
"""A disk a PCW starts by itself, which is how that machine's games came.

There is no ROM in a PCW: at the switch it fetches a loader from the keyboard
controller, reads one sector into $F000 and, if the 512 bytes add up to $FF,
jumps into it.  From there nothing is given -- no firmware, no operating
system -- so the sector has to drive the disc controller itself.

What this checks is the whole of that: the machine accepts our sector, our
code reads what follows it off the disc -- across three tracks, moving the
head itself -- and runs it, and what it runs leaves its mark.  The mark is
looked for in memory and not on the screen, because the emulator does not give
the PCW's screen back.
"""

import os
import random
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
from regac.media import PCW_NO_BANK, pcw_disk  # noqa: E402

PCW = os.path.join(ROOT, "z80", "pcw")
BOOT = os.path.join(PCW, "boot.asm")
PAYLOAD = os.path.join(PCW, "test_payload.asm")
PAYLOAD_AT = 0x0100
MARK_AT = 0x8000
MARK = bytes([0x40, 0x50, 0xCB])

if pytest is not None:
    needs_tools = pytest.mark.skipif(
        not emulator.available(), reason="sjasmplus and ZEsarUX must be in tools/"
    )
else:

    def needs_tools(func):
        return func


def assembled(source, binary):
    emulator.assemble(source, listing=os.path.splitext(source)[0] + ".lst")
    with open(os.path.join(PCW, binary), "rb") as f:
        return f.read()


@needs_tools
def test_the_machine_starts_our_disk_by_itself(tmp_path):
    """And reads more than one track of it.

    The payload here is twelve kilobytes, which is twenty four sectors: it
    starts after the directory, runs off the end of its track twice and so
    makes the loader move the head, which is the part that is easy to get
    wrong.  What is checked is that every byte of it arrived and that what
    came first is running.
    """
    boot = assembled(BOOT, "boot.bin")
    stub = assembled(PAYLOAD, "test_payload.bin")
    filler = bytes(random.Random(23).randrange(256) for _ in range(12000))
    payload = stub + filler

    path = str(tmp_path / "arranca.dsk")
    with open(path, "wb") as f:
        f.write(pcw_disk(boot, [(PAYLOAD_AT, payload, PCW_NO_BANK)]))

    session = emulator.Session(
        machine="PCW8256", extra=["--enable-dsk", "--dsk-file", path]
    )
    try:
        time.sleep(emulator.longer(12.0))
        seen = session.read(MARK_AT, len(MARK))
        arrived = bytes(session.read(PAYLOAD_AT + len(stub), len(filler)))
        where = session.pc()
    finally:
        session.close()
    assert seen == MARK, (
        f"what the disk carried never ran: {seen.hex()} where {MARK.hex()} was due"
    )
    assert arrived == filler, "what came off the disk is not what went on it"
    assert PAYLOAD_AT <= where < PAYLOAD_AT + 0x100, f"it ended up at ${where:04X}"


if __name__ == "__main__":
    test_the_machine_starts_our_disk_by_itself  # pytest gives it a folder
