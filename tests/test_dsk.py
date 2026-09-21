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
"""Writing a disk image that the machine it is for can actually read.

Two ways of checking, because each catches what the other cannot.  The first
is a round trip through the reader in disk.py, which was written against real
Amstrad disks and so knows what one looks like; that covers the awkward part,
which is a file long enough to need several directory entries.  The second
puts the disk in an emulated 6128 and has AMSDOS itself load a file off it,
which is the only thing that proves the directory is really a directory.
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

import disk as reader  # noqa: E402
import emulator  # noqa: E402
from regac.dsk import FORMATS, Disk, DiskError  # noqa: E402

RECORD = 128
LOADS_AT = 0x4000

if pytest is not None:
    needs_emulator = pytest.mark.skipif(
        not emulator.available(), reason="ZEsarUX must be in tools/"
    )
else:

    def needs_emulator(func):
        return func


def noise(size, seed=1):
    rnd = random.Random(seed)
    return bytes(rnd.randrange(256) for _ in range(size))


def read_back(image, name):
    area = reader.data_area(image)
    listing = reader.directory(area)
    assert name in listing, f"{name} is not in {sorted(listing)}"
    return reader.contents(area, listing[name])


def amsdos(name, load, blob, entry=0):
    """A file with the header AMSDOS puts in front of a binary, which is what
    says where it loads and how long it is."""
    head = bytearray(128)
    stem, _, suffix = name.upper().partition(".")
    head[1:9] = stem.ljust(8).encode("ascii")
    head[9:12] = suffix.ljust(3).encode("ascii")
    head[18] = 2                                # a binary
    head[21:23] = load.to_bytes(2, "little")
    head[24:26] = len(blob).to_bytes(2, "little")
    head[26:28] = entry.to_bytes(2, "little")
    head[64:67] = len(blob).to_bytes(3, "little")
    head[67:69] = (sum(head[:67]) & 0xFFFF).to_bytes(2, "little")
    return bytes(head) + blob


def test_a_file_comes_back_the_way_it_went_on():
    # One of each awkward size: nothing, a record, a block, exactly the
    # sixteen kilobytes one directory entry covers, and well past it.
    for size in (1, RECORD, 1024, 16384, 16385, 40000):
        blob = noise(size)
        disk = Disk("cpc-data")
        disk.add("JUEGO.BIN", blob)
        back = read_back(disk.image(), "JUEGO.BIN")
        # CP/M counts a file in records, so what comes back is rounded up
        assert len(back) == -(-size // RECORD) * RECORD
        assert back[:size] == blob, f"{size} bytes did not survive"


def test_several_files_keep_themselves_to_themselves():
    disk = Disk("cpc-data")
    one, two = noise(3000, 2), noise(5000, 3)
    disk.add("UNO.BIN", one)
    disk.add("DOS.BIN", two)
    image = disk.image()
    assert read_back(image, "UNO.BIN")[:3000] == one
    assert read_back(image, "DOS.BIN")[:5000] == two
    try:
        disk.add("uno.bin", one)
    except DiskError:
        pass
    else:
        raise AssertionError("it let the same name on twice")


def test_the_format_is_told_by_the_sector_numbers():
    """Which is how an Amstrad knows a data disk from a system one: nothing
    else on the disk says so."""
    for name, first in (("cpc-data", 0xC1), ("cpc-system", 0x41),
                        ("cpc-ibm", 0x01)):
        image = Disk(name).image()
        ids = [sector[0] for sector in reader.sectors(reader.tracks(image)[0])]
        assert ids == list(range(first, first + FORMATS[name].sectors))


def test_a_plus3_disk_says_what_it_is_in_its_first_sector():
    """The Spectrum's, unlike the Amstrad's, keeps the specification on the
    disk, which is what its ROM reads before anything else."""
    disk = Disk("plus3")
    image = disk.image()
    area = reader.data_area(image)
    assert bytes(area[:10]) == FORMATS["plus3"].specification()
    # And its own directory sits after the reserved track, not in it, so the
    # first file lands after both.  The reader in disk.py knows only the
    # Amstrad's arrangement, so this one is measured out by hand.
    blob = noise(2000, 4)
    disk.add("JUEGO.BIN", blob)
    shape = FORMATS["plus3"]
    area = reader.data_area(disk.image())
    first = (shape.reserved * shape.sectors * shape.sector_size
             + shape.dir_blocks * shape.block_size)
    assert bytes(area[first:first + 2000]) == blob


@needs_emulator
def test_an_amstrad_loads_what_we_wrote(tmp_path):
    """The real check: AMSDOS reads the directory, finds the file, believes
    its header and puts it in memory where it says."""
    blob = noise(2048, 5)
    disk = Disk("cpc-data")
    disk.add("PRUEBA.BIN", amsdos("PRUEBA.BIN", LOADS_AT, blob))
    path = disk.save(str(tmp_path / "prueba.dsk"))

    session = emulator.Session(
        machine="CPC6128", extra=["--enable-dsk", "--dsk-file", path]
    )
    try:
        time.sleep(emulator.longer(4.0))
        # BASIC owns the memory the file wants, so it is told to keep out of
        # it first; otherwise AMSDOS finds the file and then says it is full.
        session.type_keys("memory &3fff" + chr(13))
        time.sleep(emulator.longer(1.0))
        session.type_keys('load"prueba.bin' + chr(13))
        time.sleep(emulator.longer(4.0))
        loaded = session.read(LOADS_AT, len(blob))
    finally:
        session.close()
    assert loaded == blob, "what AMSDOS loaded is not what we wrote"


if __name__ == "__main__":
    test_an_amstrad_loads_what_we_wrote  # runs under pytest, which gives it a folder
    test_a_file_comes_back_the_way_it_went_on()
    print("a file comes back the way it went on")
    test_several_files_keep_themselves_to_themselves()
    print("several files keep themselves to themselves")
    test_the_format_is_told_by_the_sector_numbers()
    print("the format is told by the sector numbers")
    test_a_plus3_disk_says_what_it_is_in_its_first_sector()
    print("a plus3 disk says what it is in its first sector")
