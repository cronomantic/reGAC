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
"""Drawing on a Spectrum Next, compared against the reference renderer.

The same trade as every other machine: each primitive is drawn twice, once by
the reference the project is built against and once by our own Z80 code
running on a real one, and the two are compared.  Here they are compared in
layer 2 itself, read out of the machine's memory where the video reads it,
because that is where the picture is drawn -- there is no copy of it anywhere.

What this checks, besides the drawing, is the two things that are this
machine's own: that the sixteen kilobyte window onto layer 2 is moved to
whichever half of the picture a row falls in, and that the mask kept beside it
holds what a Spectrum's screen would hold, since that and not the picture is
what tells a fill where to stop.
"""

import json
import os
import subprocess
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
from regac.devices import SPECTRUM_PALETTE, next_device  # noqa: E402
from regac.gfx import Renderer  # noqa: E402

NEXT = os.path.join(ROOT, "z80", "next")
SOURCE = os.path.join(NEXT, "test_picture.asm")
DATABASE = os.path.join(NEXT, "picture.rgac")
IMAGE = os.path.join(NEXT, "picture.nex")
LISTING = os.path.join(NEXT, "picture.lst")
SCREEN = os.path.join(NEXT, "screen.asm")
ADVENTURE = os.path.join(ROOT, "snapshots", "megacorp2.json")

WINDOW = 0xC000                 # where the build shows a piece of layer 2
WINDOW_BYTES = 0x4000
PICTURE_BYTES = 256 * 128       # what a picture takes, a byte to a pixel

if pytest is not None:
    needs_tools = pytest.mark.skipif(
        not emulator.available(), reason="sjasmplus and ZEsarUX must be in tools/"
    )
    needs_adventure = pytest.mark.skipif(
        not emulator.available() or not os.path.exists(ADVENTURE),
        reason="the tools must be in tools/, with a decompiled adventure",
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

    needs_adventure = needs_tools

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


def layer2(session, wanted):
    """The picture, out of layer 2 itself.

    Only sixteen kilobytes of it are in the map at a time and nothing outside
    the machine can move that window, so the build is asked: once it has
    finished drawing it sits showing whichever piece a byte tells it to, and
    the two halves are read one after the other.
    """
    out = b""
    for piece in (0, 1):
        session.command(f"write-memory-raw {wanted} {piece:02X}")
        time.sleep(0.1)
        out += bytes(session.read(WINDOW, WINDOW_BYTES))
    return out


def draw_on_both(commands):
    ddb = adventure(commands)
    with open(DATABASE, "wb") as f:
        f.write(Database(ddb).build())
    listing = emulator.assemble(SOURCE, listing=LISTING)
    where = {name: emulator.label_address(listing, name)
             for name in ("done_flag", "piece_wanted")}

    session = emulator.Session(machine="TBBlue")
    try:
        session.load(IMAGE)
        finished = session.wait_for(where["done_flag"], 0xFF, timeout=30.0,
                                    every=0.2)
        drawn = layer2(session, where["piece_wanted"])
    finally:
        session.close()

    return finished, drawn, Renderer(ddb["gfx"], next_device()).run(1).vram()


@needs_tools
@drawings
def test_the_next_draws_what_the_reference_draws(name, commands):
    finished, theirs, ours = draw_on_both(commands)
    assert finished, f"{name}: the Next never finished drawing"
    wrong = [n for n in range(PICTURE_BYTES) if ours[n] != theirs[n]]
    assert not wrong, (
        f"{name}: {len(wrong)} pixels differ, the first at "
        f"({wrong[0] % 256}, {wrong[0] // 256}): ours ${ours[wrong[0]]:02X}, "
        f"theirs ${theirs[wrong[0]]:02X}"
    )


@needs_adventure
def test_every_picture_of_an_adventure_comes_out_the_same():
    """The primitives one at a time prove the sums; a real adventure proves
    they hold together.  Every picture of Megacorp is drawn on the machine and
    compared with the reference, in one sitting: the build is asked for a
    picture, draws it, and waits to be asked for the next.
    """
    subprocess.run(
        [sys.executable, "-m", "regac", "build", ADVENTURE, DATABASE, "-m", "next"],
        cwd=ROOT, check=True, capture_output=True,
    )
    listing = emulator.assemble(SOURCE, listing=LISTING)
    where = {name: emulator.label_address(listing, name)
             for name in ("done_flag", "picture_wanted", "piece_wanted", "redraw")}
    with open(ADVENTURE, encoding="utf-8") as f:
        gfx = json.load(f)["gfx"]

    wrong = {}
    session = emulator.Session(machine="TBBlue")
    try:
        session.load(IMAGE)
        assert session.wait_for(where["done_flag"], 0xFF, timeout=30.0, every=0.2), (
            "the Next never got going"
        )
        for key in sorted(gfx, key=int):
            number = int(key)
            # Asked up to three times.  A program counter written into a
            # processor that is running does not always take, and when it does
            # not the machine is still going round its parking loop with
            # nothing drawn, so the flag can never come and the wait is a
            # minute thrown away: one run in five died that way, on a
            # different picture each time.  Stopping the processor to write it
            # cures it and leaves the emulator running nine times slower --
            # two minutes a round became nineteen -- so it is asked again
            # instead, which costs nothing at all on a round that goes well.
            drew = False
            for _ in range(3):
                session.command(
                    f"write-memory {where['picture_wanted']} "
                    f"{number & 255} {number >> 8}"
                )
                session.command(f"write-memory {where['done_flag']} 0")
                session.command(f"set-register PC={where['redraw']:04X}H")
                if session.wait_for(where["done_flag"], 0xFF, timeout=60.0,
                                    every=0.1):
                    drew = True
                    break
            if not drew:
                # Once a picture does not finish, the machine is still in the
                # middle of it and nothing read afterwards means anything: the
                # run that found this reported twenty six pictures wrong when
                # only one thing had happened.  So it stops here, and says
                # where the processor was, sampled, which tells a picture that
                # is merely slow from one that is going round in a circle.
                seen = []
                for _ in range(5):
                    seen.append(session.pc())
                    time.sleep(0.2)
                wrong[number] = ("never finished, PC at "
                                 + " ".join(f"${at:04X}" for at in seen if at))
                break
            drawn = layer2(session, where["piece_wanted"])
            reference = Renderer(gfx, next_device()).run(number).vram()
            differ = sum(1 for n in range(PICTURE_BYTES) if drawn[n] != reference[n])
            if differ:
                wrong[number] = f"{differ} pixels"
    finally:
        session.close()

    assert not wrong, f"{len(wrong)} of {len(gfx)} pictures differ: {wrong}"


def test_the_palette_is_the_one_the_reference_paints_with():
    """The sixteen colours are written into layer two's palette by the build,
    three bits a channel, and they are the reference's own sixteen scaled down
    to that.  Both ends of the comparison show the same picture only if these
    agree, and nothing else would notice if they did not."""
    wanted = []
    for colour in SPECTRUM_PALETTE:
        parts = [round(((colour >> shift) & 0xFF) * 7 / 255) for shift in (16, 8, 0)]
        red, green, blue = parts
        wanted.append(((red << 5) | (green << 2) | (blue >> 1), blue & 1))
    with open(SCREEN, encoding="utf-8") as f:
        source = f.read()
    table = source[source.index(chr(10) + "palette:"):]
    found = []
    for line in table.splitlines():
        parts = line.split(";")[0].strip()
        if parts.startswith("db"):
            high, low = parts[2:].split(",")
            found.append((int(high.strip().lstrip("$"), 16), int(low)))
        elif found:
            break
    assert found == wanted, "the build's palette is not the reference's colours"


if __name__ == "__main__":
    test_the_palette_is_the_one_the_reference_paints_with()
    print("the palette is the reference's")
    for case in (
        ("a rectangle", [["RECT", 20, 60, 100, 120]]),
        ("a half tone", [["RECT", 20, 60, 100, 120], ["SHADE", 60, 90]]),
    ):
        test_the_next_draws_what_the_reference_draws(*case)
        print(f"{case[0]}: matches the reference")
