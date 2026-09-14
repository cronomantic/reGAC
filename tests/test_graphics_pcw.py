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
"""Drawing on an Amstrad PCW, compared against the reference renderer.

The same trade as the Spectrum's and the Amstrad's: every primitive is drawn
twice, once by the reference the project is built against and once by our own
Z80 code running on a real machine, and the two screens are compared.

Here they are compared as the screen's own bytes, and there is no other way to
do it: the emulator does not give the PCW's screen back, it comes out black
whatever is in memory.  So the memory is what is read, which is no loss --
those bytes are the picture, and the table that tells the video where to find
them is checked by the same reading.

There is no snapshot to load either.  A PCW with no disk in it sits in the
loader its keyboard gave it, with the four banks mapped nought to three, which
is exactly the state its own boot sector would leave; so the build is written
straight into memory and the processor pointed at the front of it, which is
what the disk would have done.
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
from regac.binary import Database  # noqa: E402
from regac.devices import PCW_MARGIN, PcwDevice, pcw_address  # noqa: E402
from regac.gfx import Renderer  # noqa: E402

PCW = os.path.join(ROOT, "z80", "pcw")
SOURCE = os.path.join(PCW, "test_picture.asm")
DATABASE = os.path.join(PCW, "picture.rgac")
BINARY = os.path.join(PCW, "picture.bin")
LISTING = os.path.join(PCW, "picture.lst")

LOADS_AT = 0x0100
SCREEN = 0x8000
SCREEN_BYTES = 16 * 720  # the sixteen rows the picture takes
PICTURE_ROWS = 128

if pytest is not None:
    needs_tools = pytest.mark.skipif(
        not emulator.available(), reason="sjasmplus and ZEsarUX must be in tools/"
    )
    drawings = pytest.mark.parametrize(
        "name,commands",
        [
            ("a line across", [["LINE", 10, 100, 60, 100]]),
            ("a line down", [["LINE", 10, 60, 10, 120]]),
            ("a line at an angle", [["LINE", 10, 60, 60, 120]]),
            ("a rectangle", [["RECT", 20, 60, 100, 120]]),
            ("a single point", [["INK", 5], ["PLOT", 40, 100]]),
            ("a larger ellipse", [["ELLIPSE", 128, 100, 168, 130]]),
            ("a fill", [["RECT", 20, 60, 100, 120], ["FILL", 60, 90]]),
            (
                "a fill of a colour that dithers",
                [["RECT", 20, 60, 100, 120], ["PAPER", 4], ["BGFILL", 60, 90]],
            ),
            ("a half tone", [["RECT", 20, 60, 100, 120], ["SHADE", 60, 90]]),
            (
                "a run that ends inside a byte",
                [["RECT", 21, 60, 101, 120], ["INK", 2], ["FILL", 61, 90]],
            ),
            (
                "an ink that reads against the paper",
                [
                    ["PAPER", 1],
                    ["INK", 9],
                    ["RECT", 20, 60, 100, 120],
                    ["BGFILL", 60, 90],
                    ["LINE", 20, 60, 100, 120],
                ],
            ),
            ("one picture calling another", [["INK", 2], ["CALL", 2]]),
        ],
    )
else:

    def needs_tools(func):
        return func

    def drawings(func):
        return func


def adventure(commands):
    """The smallest adventure that can hold one picture."""
    return {
        "font": [0] * 1024,
        "verbs": {"N": 1},
        "nouns": {},
        "adverbs": {},
        "pronouns": [],
        "messages": {"1": "x"},
        "objects": {"1": {"weight": 1, "initial_loc": 1, "name": "x"}},
        "locations": {"1": {"graphic_id": 1, "exits": [], "desc": "x"}},
        "hpcs": [],
        "lpcs": [],
        "lcs": {},
        "model": "48K",
        "punctuation": list("\0 .,-!?:"),
        "separators": [],
        "init_loc": 1,
        "no_objs_msg": "x",
        "gfx": {"1": commands, "2": [["PLOT", 10, 100]]},
    }


def point_at(screen, x, y):
    """Whether point (x, y) of the picture is lit, out of the screen's bytes.
    A point is two pixels across, and the picture sits in the middle of the
    ninety columns, so this is also a check on where it was put."""
    across = PCW_MARGIN * 8 + x * 2
    return (screen[pcw_address(across, y)] >> (7 - (across & 7))) & 1


def draw_on_both(commands):
    ddb = adventure(commands)
    with open(DATABASE, "wb") as f:
        f.write(Database(ddb).build())
    listing = emulator.assemble(SOURCE, listing=LISTING)
    done = emulator.label_address(listing, "done_flag")
    with open(BINARY, "rb") as f:
        blob = f.read()

    session = emulator.Session(machine="PCW8256")
    try:
        time.sleep(4.0)  # let the machine ask for a disk
        finished = session.start_code(blob, LOADS_AT, done)
        screen = session.read(SCREEN, SCREEN_BYTES)
    finally:
        session.close()

    reference = Renderer(ddb["gfx"], PcwDevice()).run(1)
    return finished, screen, reference.screen()


@needs_tools
@drawings
def test_the_pcw_draws_what_the_reference_draws(name, commands):
    finished, theirs, ours = draw_on_both(commands)
    assert finished, f"{name}: the PCW never finished drawing"
    wrong = [
        (row, x)
        for row in range(PICTURE_ROWS)
        for x in range(256)
        if point_at(theirs, x, row) != point_at(ours, x, row)
    ]
    assert not wrong, f"{name}: {len(wrong)} points differ, first at {wrong[0]}"
    # and nothing outside the picture, margins included, was touched
    assert theirs == ours, "the screen differs somewhere off the picture"


if __name__ == "__main__":
    for case in (
        ("a rectangle", [["RECT", 20, 60, 100, 120]]),
        ("a half tone", [["RECT", 20, 60, 100, 120], ["SHADE", 60, 90]]),
    ):
        test_the_pcw_draws_what_the_reference_draws(*case)
        print(f"{case[0]}: matches the reference")
