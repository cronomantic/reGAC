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
"""Saving a game on a PCW, which means writing sectors nobody else will.

There is no operating system to ask, so the builder makes the file -- an
ordinary CP/M one, the right size and empty -- and leaves where it starts in
the boot sector.  The interpreter writes those sectors itself and never
touches the directory, so what comes out is still a file the machine's own
tools can copy about.

What is checked here is both halves of that: that the builder and the runtime
agree on where the file is, and that a block written to it comes back the same
on a real machine, off a real disk.
"""

import os
import sys

try:
    import pytest
except ImportError:
    pytest = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import emulator  # noqa: E402
from regac.dsk import Disk  # noqa: E402
from regac.media import (  # noqa: E402
    PCW_CODE_AT,
    PCW_NO_BANK,
    PCW_SAVE,
    PCW_SAVE_SECTORS,
    pcw_disk,
)

PCW = os.path.join(ROOT, "z80", "pcw")
BOOT = os.path.join(PCW, "boot.asm")
SOURCE = os.path.join(PCW, "test_save.asm")
SAVE_WHERE = 0xF1FC  # what the builder left for the runtime to find
BLOCK_AT = 0xD800
HEADER = 0x100  # what a disk image, and each of its tracks, carries in front

if pytest is not None:
    needs_tools = pytest.mark.skipif(
        not emulator.available(), reason="sjasmplus and ZEsarUX must be in tools/"
    )
else:

    def needs_tools(func):
        return func


def a_disk(tmp_path):
    emulator.assemble(BOOT, listing=os.path.join(PCW, "boot.lst"))
    listing = emulator.assemble(SOURCE, listing=os.path.join(PCW, "save.lst"))
    with open(os.path.join(PCW, "boot.bin"), "rb") as f:
        boot = f.read()
    with open(os.path.join(PCW, "save.bin"), "rb") as f:
        blob = f.read()
    path = str(tmp_path / "guarda.dsk")
    with open(path, "wb") as f:
        f.write(pcw_disk(boot, [(PCW_CODE_AT, blob, PCW_NO_BANK)]))
    return path, listing


@needs_tools
def test_a_game_written_to_the_disc_comes_back(tmp_path):
    path, listing = a_disk(tmp_path)
    where = {
        name: emulator.label_address(listing, name)
        for name in ("done_flag", "saved_flag")
    }
    session = emulator.Session(
        machine="PCW8256", extra=["--enable-dsk", "--dsk-file", path]
    )
    try:
        arrived = session.wait_for(where["done_flag"], 0xFF, timeout=60.0, every=0.3)
        flags = session.read(where["saved_flag"], 2)
        told = session.read(SAVE_WHERE, 3)
        block = session.read(BLOCK_AT, 8)
    finally:
        session.close()

    assert flags[0] == 1, "it never got as far as writing"
    assert arrived, f"what came back is not what went down (flag ${flags[1]:02X})"
    assert block == bytes(range(1, 9)), "the block is not the one that was made"

    # And the two ends agree about where that file is: the runtime was told
    # what the disk's own directory says, not something made up.
    assert tuple(told) == where_the_save_went(path) + (PCW_SAVE_SECTORS,)


def where_the_save_went(path):
    """Where the saved game sits, worked out again from the outside.

    The same sum the builder did, done from the disk it wrote: find the file
    in the directory, take the first block it was given, and turn that into a
    track and a record.
    """
    with open(path, "rb") as f:
        image = f.read()
    disk = Disk("pcw")
    shape = disk.format
    # The directory is the first blocks past the reserved track, and both the
    # image and each of its tracks carry a header of their own in front.
    at = (HEADER + shape.reserved * (HEADER + shape.sectors * shape.sector_size)
          + HEADER)
    disk.directory = bytearray(
        image[at:at + shape.dir_blocks * shape.block_size]
    )
    return disk.where(PCW_SAVE)


if __name__ == "__main__":
    import pathlib
    import tempfile

    test_a_game_written_to_the_disc_comes_back(pathlib.Path(tempfile.mkdtemp()))
    print("a game written to the disc comes back")
