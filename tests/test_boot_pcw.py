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
code reads what follows it off the disc and runs it, and what it runs leaves
its mark.  The mark is looked for in memory and not on the screen, because the
emulator does not give the PCW's screen back.
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
from regac.dsk import Disk  # noqa: E402

PCW = os.path.join(ROOT, "z80", "pcw")
BOOT = os.path.join(PCW, "boot.asm")
PAYLOAD = os.path.join(PCW, "test_payload.asm")
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
    boot = assembled(BOOT, "boot.bin")
    payload = assembled(PAYLOAD, "test_payload.bin")

    disk = Disk("pcw")
    disk.boot(boot)
    for number, at in enumerate(range(0, len(payload), 512)):
        disk.put(0, 2 + number, payload[at:at + 512])
    path = disk.save(str(tmp_path / "arranca.dsk"))

    session = emulator.Session(
        machine="PCW8256", extra=["--enable-dsk", "--dsk-file", path]
    )
    try:
        time.sleep(10.0)
        seen = session.read(MARK_AT, len(MARK))
        where = session.pc()
    finally:
        session.close()
    assert seen == MARK, (
        f"what the disk carried never ran: {seen.hex()} where {MARK.hex()} was due"
    )
    assert 0x0100 <= where < 0x0200, f"it ran but ended up at ${where:04X}"


if __name__ == "__main__":
    test_the_machine_starts_our_disk_by_itself  # pytest gives it a folder
