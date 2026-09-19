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
"""Drawing on a real Z80, compared against the reference renderer.

Every primitive is drawn twice: once by the Python renderer, which is the
reference the whole project is built against, and once by the Spectrum code
running in the emulator.  The two screens are then compared byte for byte,
pixels and colours alike.  That is the strongest check available here, and it
is what the device split in regac/gfx.py was for.

Every primitive here follows the original interpreter, read out of the
snapshots the adventures came in: the line is the ROM's, the fill walks a
column rather than flooding, and the ellipse takes its centre, its radii and
its table of sines from GAC itself.  See doc/graficos.md.
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
from regac.binary import Database  # noqa: E402
from regac.devices import SpectrumDevice  # noqa: E402
from regac.gfx import Renderer  # noqa: E402

SPECTRUM = os.path.join(ROOT, "z80", "spectrum")
SOURCE = os.path.join(SPECTRUM, "test_picture.asm")
DATABASE = os.path.join(SPECTRUM, "picture.rgac")
SNAPSHOT = os.path.join(SPECTRUM, "picture.sna")
LISTING = os.path.join(SPECTRUM, "picture.lst")
CHOICE = os.path.join(SPECTRUM, "picture_choice.inc")

PICTURE_ROWS = 128
BYTES_ACROSS = 32

if pytest is not None:
    needs_tools = pytest.mark.skipif(
        not emulator.available(), reason="sjasmplus and ZEsarUX must be in tools/"
    )
    drawings = pytest.mark.parametrize(
        "name,commands,called",
        [
            ("a line across", [["LINE", 10, 100, 60, 100]], None),
            ("a line down", [["LINE", 10, 60, 10, 120]], None),
            ("a line at an angle", [["LINE", 10, 60, 60, 120]], None),
            ("a rectangle", [["RECT", 20, 60, 100, 120]], None),
            ("a single point", [["PLOT", 40, 100]], None),
            # A point outside the picture is not drawn at all, and
            # what comes after it still is: asked of the original
            # with pictures of our own written over one of
            # MegaCorp's.  A line's far end is brought to the edge
            # instead, which is the other half of the same answer.
            ("a point outside the picture",
             [["PLOT", 40, 20], ["PLOT", 60, 200], ["PLOT", 80, 100]],
             None),
            ("a small ellipse", [["ELLIPSE", 60, 100, 70, 110]], None),
            ("a larger ellipse", [["ELLIPSE", 128, 100, 168, 130]], None),
            (
                "a background fill",
                [["RECT", 20, 60, 100, 120], ["PAPER", 2], ["BGFILL", 60, 90]],
                None,
            ),
            (
                "an ink fill",
                [["RECT", 20, 60, 100, 120], ["INK", 3], ["FILL", 60, 90]],
                None,
            ),
            ("a half tone", [["RECT", 20, 60, 100, 120], ["SHADE", 60, 90]], None),
            ("one picture calling another", [["CALL", 2]], {"2": [["PLOT", 10, 100]]}),
        ],
    )
else:

    def needs_tools(func):
        return func

    def drawings(func):
        return func


def adventure(commands, called=None):
    """The smallest adventure that can hold one picture."""
    pictures = {"1": commands}
    pictures.update(called or {})
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
        "model": "SPECTRUM",
        "punctuation": list("\0 .,-!?:"),
        "separators": ["then", "and"],
        "init_loc": 1,
        "no_objs_msg": "x",
        "gfx": pictures,
    }


def screen_address(row, column):
    """Where a byte of a row lives in the Spectrum's display, which is not in
    the order you would expect."""
    return ((row & 0xC0) << 5) + ((row & 7) << 8) + ((row & 0x38) << 2) + column


def draw_on_both(commands, called=None):
    ddb = adventure(commands, called)
    with open(DATABASE, "wb") as f:
        f.write(Database(ddb).build())
    with open(CHOICE, "w", encoding="ascii") as f:
        f.write("picture_wanted  equ     1\n")
    listing = emulator.assemble(SOURCE, listing=LISTING)
    finished, (bitmap, attributes) = emulator.run(
        SNAPSHOT, listing, reads=[(0x4000, 6144), (0x5800, 512)]
    )
    assert finished, "the Spectrum never finished drawing"
    reference = Renderer(ddb["gfx"], SpectrumDevice()).run(1)
    return bitmap, attributes, reference


@needs_tools
@drawings
def test_the_spectrum_draws_what_the_reference_draws(name, commands, called):
    bitmap, attributes, reference = draw_on_both(commands, called)

    wrong = [
        (row, column)
        for row in range(PICTURE_ROWS)
        for column in range(BYTES_ACROSS)
        if bitmap[screen_address(row, column)]
        != reference.pixels[row * BYTES_ACROSS + column]
    ]
    assert not wrong, f"{name}: {len(wrong)} bytes differ, first at {wrong[0]}"

    colours = [n for n in range(512) if attributes[n] != reference.attrs[n]]
    assert not colours, f"{name}: {len(colours)} colours differ, first at {colours[0]}"


if __name__ == "__main__":
    cases = [
        ("a line across", [["LINE", 10, 100, 60, 100]], None),
        ("a rectangle", [["RECT", 20, 60, 100, 120]], None),
        ("a small ellipse", [["ELLIPSE", 60, 100, 70, 110]], None),
        ("an ink fill", [["RECT", 20, 60, 100, 120], ["INK", 3], ["FILL", 60, 90]], None),
    ]
    for case in cases:
        test_the_spectrum_draws_what_the_reference_draws(*case)
        print(f"{case[0]}: matches the reference")
