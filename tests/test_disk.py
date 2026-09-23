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
"""Taking an adventure off an Amstrad disk without turning anything on.

Three shapes of disk are covered, which are the three there are to hand: a
plain one where the file says where it loads, one where the file loads
somewhere else and then moves itself down, and one laid out so that it cannot
be copied, which keeps nothing in its directory and has to be read track by
track.  The disks themselves are not ours to keep, so these skip when they are
not there.
"""

import os
import sys
import zipfile

try:
    import pytest
except ImportError:
    pytest = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import disk  # noqa: E402

GAMES = os.path.join(ROOT, "juegos")
PUNCTUATION = 0x210C

if pytest is not None:
    needs_games = pytest.mark.skipif(
        not os.path.isdir(GAMES),
        reason="the Amstrad games must be in juegos/",
    )
else:

    def needs_games(func):
        return func


def image(archive, wanted):
    """One disk image out of one of the zips in juegos/, as bytes."""
    path = os.path.join(GAMES, archive)
    if not os.path.exists(path):
        if pytest is not None:
            pytest.skip(f"{archive} is not in juegos/")
        raise SystemExit(f"{archive} is not in juegos/")
    with zipfile.ZipFile(path) as inside:
        for name in inside.namelist():
            if name.lower().endswith(wanted):
                return inside.read(name)
    raise AssertionError(f"no {wanted} in {archive}")


def laid(blob, name, at=None):
    area = disk.data_area(blob)
    return disk.memory(disk.contents(area, disk.directory(area)[name]), at)


@needs_games
def test_a_plain_file_is_laid_where_it_says():
    memory, head = laid(image("carvalho_ams.zip", ".dsk"), "CARVALHO.FAC")
    assert head["laid"] == 0x0040 and not head["moved"]
    assert bytes(memory[PUNCTUATION:PUNCTUATION + 8]) == disk.DATABASE_MARK


@needs_games
def test_a_file_that_moves_itself_is_followed():
    """Megacorp loads at $0428 and its last fourteen bytes take it to $0040.
    Read without following that, the database is nowhere the machine has it."""
    blob = image("megacorp_ams.zip", ".dsk")
    memory, head = laid(blob, "MEGACOR2.BIN")
    assert head["load"] == 0x0428
    assert head["laid"] == 0x0040 and head["moved"]
    assert bytes(memory[PUNCTUATION:PUNCTUATION + 8]) == disk.DATABASE_MARK

    told, head = laid(blob, "MEGACOR2.BIN", at=0x0428)
    assert head["laid"] == 0x0428 and not head["moved"]
    assert bytes(told[PUNCTUATION:PUNCTUATION + 8]) != disk.DATABASE_MARK


@needs_games
def test_a_disk_that_cannot_be_copied_is_read_track_by_track():
    blob = image("vajillas_ams.zip", ".dsk")
    area = disk.data_area(blob)
    assert not disk.directory(area), "that disk is supposed to have an empty directory"

    stream = disk.raw_stream(blob)
    where = disk.adventures(stream)
    assert len(where) == 2, "both parts of the adventure are on it"
    for base in where:
        memory = disk.raw_memory(stream, base)
        assert bytes(memory[PUNCTUATION:PUNCTUATION + 8]) == disk.DATABASE_MARK
        # and the tables where the Amstrad keeps them, climbing
        pointers = [memory[0x4000 + n * 2] | memory[0x4001 + n * 2] << 8
                    for n in range(10)]
        assert pointers == sorted(pointers) and pointers[0] > PUNCTUATION


@needs_games
def test_an_amstrad_adventure_says_nothing_in_its_own_word():
    """Read off the disk the way deGAC reads it: the three Amstrad adventures
    never translated the word, and it is "nothing", as it is printed at $05A4."""
    from deGAC import word_for_nothing

    memory, _ = laid(image("carvalho_ams.zip", ".dsk"), "CARVALHO.FAC")
    assert word_for_nothing(list(memory)) == "nothing"


if __name__ == "__main__":
    test_a_plain_file_is_laid_where_it_says()
    print("a plain file is laid where it says")
    test_a_file_that_moves_itself_is_followed()
    print("a file that moves itself is followed")
    test_a_disk_that_cannot_be_copied_is_read_track_by_track()
    print("a disk that cannot be copied is read track by track")
