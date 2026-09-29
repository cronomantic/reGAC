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
"""What regac make says a build takes of each machine and leaves: see
regac/memory.py.

Decided by the user: after every machine, how much room is left and where --
in the stretches the interpreter and the resident database share, and in
every bank -- so an author knows before the adventure stops fitting."""

import os
import shutil
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from regac import i18n, memory  # noqa: E402
from regac.binary import Database  # noqa: E402
from regac.srcparse import parse  # noqa: E402

EXAMPLE = os.path.join(ROOT, "ejemplo")


@pytest.fixture(autouse=True)
def in_english():
    i18n.speak(i18n.ENGLISH)
    yield
    i18n._chosen = None


def the_example(machine="spectrum128", page_bits=14):
    with open(os.path.join(EXAMPLE, "faro.gac"), encoding="utf-8") as f:
        ddb = parse(f.read(), "faro.gac", EXAMPLE, machine=machine)
    database = Database(ddb, machine=machine, page_bits=page_bits)
    database.build()
    return database


def test_the_labels_are_read_out_of_the_symbol_file(tmp_path):
    path = tmp_path / "game.sym"
    path.write_text("start: EQU 0x00008000\n"
                    "start.stop: EQU 0x00008033\n"
                    "DB_WINDOW: EQU 0x0000C000\n"
                    "; not a label\n", encoding="utf-8")
    assert memory.symbols(str(path)) == {
        "start": 0x8000, "start.stop": 0x8033, "DB_WINDOW": 0xC000}
    assert memory.symbols(str(tmp_path / "none.sym")) == {}


def test_a_128_says_what_is_left_under_the_window_and_in_every_bank():
    database = the_example()
    sym = {"start": 0x8000, "database": 0xA100,
           "last": 0xA100 + database.resident_size, "DB_WINDOW": 0xC000}
    lines, over = memory.report("spectrum128", sym, database, most_banks=6)
    assert not over
    free = 0xC000 - sym["last"]
    assert lines[0].startswith("    $8000-$BFFF")
    assert f"{free} free of 16384" in lines[0]
    assert "interpreter 8448" in lines[0]
    assert f"database {database.resident_size}" in lines[0]
    assert "1 of 6, 16384 bytes each" in lines[1]
    used = len(database.banks[0])
    assert f"{16384 - used} free of 16384" in lines[2]
    assert "text" in lines[2] and "graphics" in lines[2]
    assert "banks 1-5" in lines[3] and str(5 * 16384) in lines[3]


def test_what_does_not_fit_is_said_and_by_how_much():
    database = the_example("spectrum48", 0)
    sym = {"start": 0x8000, "database": 0xF000, "last": 0x10000 + 300}
    lines, over = memory.report("spectrum48", sym, database)
    assert "300 too many, of 32768" in lines[0]
    assert over == ["$8000-$FFFF by 300 bytes"]


def test_the_msx_database_is_held_to_what_is_under_the_interpreter():
    # nothing in the assembler sees it: the interpreter reads it in itself
    database = the_example("msx", 0)
    sym = {"database": 0, "from_tape": 0x8000, "last": 0xA000,
           "SHADOW": 0xC000}
    database.resident_size = 0x8000 + 1
    lines, over = memory.report("msx", sym, database)
    assert over == ["$0000-$7FFF by 1 bytes"]
    assert "8192 free of 16384" in lines[1]


def test_the_bar_is_never_wider_than_itself():
    for share in (0, 0.001, 0.5, 1, 3.5):
        assert len(memory.bar(share)) == memory.BAR + 2
    assert memory.bar(0.001).count("#") == 1
    assert memory.bar(3.5).count("-") == 0


def test_a_pc_says_what_dos_has_to_give_it():
    database = the_example("pc", 16)
    lines = memory.pc_report(15000, database, 2048)
    image = database.resident_size + sum(len(b) for b in database.banks)
    assert f"{15000 + image + 2048} bytes" in lines[0]
    assert "free of 65520" in lines[1]


def tools():
    """sjasmplus and NASM, in tools/ or on the path, which is all make needs."""
    def found(name):
        return (os.path.isfile(os.path.join(ROOT, "tools", name + ".exe"))
                or shutil.which(name))
    return found("sjasmplus") and found("nasm")


@pytest.mark.skipif(not tools(), reason="sjasmplus and nasm are needed")
def test_make_says_it_for_every_machine(tmp_path):
    done = subprocess.run(
        [sys.executable, "-m", "regac", "make",
         os.path.join(EXAMPLE, "faro.toml"), "-o", str(tmp_path)],
        cwd=ROOT, capture_output=True, text=True,
        env=dict(os.environ, REGAC_LANG="en"))
    assert done.returncode == 0, done.stdout + done.stderr
    said = done.stdout
    for stretch in ("$8000-$FFFF", "$4000-$B0FF", "$0300-$3FFF",
                    "$0000-$7FFF", "$5D00-$7FFF", "$0100-$3FFF",
                    "$8000-$BFFF"):
        assert stretch in said, f"no {stretch} in:\n{said}"
    assert said.count("bank 0 ") == 5, said        # the five with banks
    assert "the largest section" in said            # and the PC
    assert "too many" not in said
