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
"""Drawing on an MSX1, compared against the reference renderer.

The same trade as every other machine: each primitive is drawn twice, once by
the reference the project is built against and once by our own Z80 code
running on a real one, and the two are compared.  Here they are compared in
the video chip's own memory, which is where the picture actually ends up:
screen 2 keeps a table of patterns and a table of colours, and both are read
straight out of the chip.

That is also the point of the design.  The picture is drawn into a copy in the
processor's memory and sent across when it is finished, because the fill reads
the screen constantly and reading this one costs two writes and a read.  What
this checks is that the copy, the sum that addresses it and the sending are
all right at once: if any of the three were wrong the tables would not match.
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
from regac.devices import MSX_COLOURS, MSX_PATTERNS, MSX_PICTURE_BYTES  # noqa: E402
from regac.devices import MsxDevice  # noqa: E402
from regac.gfx import Renderer  # noqa: E402

MSX = os.path.join(ROOT, "z80", "msx")
SOURCE = os.path.join(MSX, "test_picture.asm")
DATABASE = os.path.join(MSX, "picture.rgac")
BINARY = os.path.join(MSX, "picture.bin")
LISTING = os.path.join(MSX, "picture.lst")

LOADS_AT = 0x8000
VRAM = 24  # the emulator's name for the video chip's own memory

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
                "a fill in a colour of its own",
                [["RECT", 20, 60, 100, 120], ["PAPER", 4], ["BGFILL", 60, 90]],
            ),
            ("a half tone", [["RECT", 20, 60, 100, 120], ["SHADE", 60, 90]]),
            (
                "a run that ends inside a byte",
                [["RECT", 21, 60, 101, 120], ["INK", 5], ["FILL", 61, 90]],
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


def draw_on_both(commands):
    ddb = adventure(commands)
    with open(DATABASE, "wb") as f:
        f.write(Database(ddb).build())
    listing = emulator.assemble(SOURCE, listing=LISTING)
    done = emulator.label_address(listing, "done_flag")
    with open(BINARY, "rb") as f:
        blob = f.read()

    session = emulator.Session(machine="MSX1")
    try:
        time.sleep(7.0)  # this one takes its time coming up
        finished = session.start_code(blob, LOADS_AT, done, timeout=30.0)
        patterns = bytes(session.read(MSX_PATTERNS, MSX_PICTURE_BYTES, zone=VRAM))
        colours = bytes(session.read(MSX_COLOURS, MSX_PICTURE_BYTES, zone=VRAM))
    finally:
        session.close()

    return finished, (patterns, colours), Renderer(ddb["gfx"], MsxDevice()).run(1).vram()


@needs_tools
@drawings
def test_the_msx_draws_what_the_reference_draws(name, commands):
    finished, theirs, ours = draw_on_both(commands)
    assert finished, f"{name}: the MSX never finished drawing"
    for which, mine, yours in zip(("patterns", "colours"), ours, theirs):
        wrong = [n for n in range(MSX_PICTURE_BYTES) if mine[n] != yours[n]]
        assert not wrong, (
            f"{name}: {len(wrong)} bytes of the {which} differ, the first at "
            f"{wrong[0]}: ours ${mine[wrong[0]]:02X}, theirs ${yours[wrong[0]]:02X}"
        )


if __name__ == "__main__":
    for case in (
        ("a rectangle", [["RECT", 20, 60, 100, 120]]),
        ("a half tone", [["RECT", 20, 60, 100, 120], ["SHADE", 60, 90]]),
    ):
        test_the_msx_draws_what_the_reference_draws(*case)
        print(f"{case[0]}: matches the reference")
