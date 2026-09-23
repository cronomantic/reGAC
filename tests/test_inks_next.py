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
"""The colours a Spectrum Next shows, looked at as colours.

An adventure off an Amstrad is drawn here with the Amstrad's rules, and what
it is held to is what the Amstrad's own GAC does, read at $0538 of it and
done on the Amstrad already -- tests/test_inks_cpc.py: the picture of a room
puts up its own inks, the border in the first; a picture called from another
does not; a pen of two colours flashes; and the text is in pen one on pen
nought.  Here a pen is a byte of layer 2 and its ink an entry of layer 2's
palette, so the colours come out as close as nine bits get to the Amstrad's.

And one that is not the Amstrad's at all: the Spectrum's bright magenta is
$E3 in nine bits, which is the colour layer 2 treats as not there, so every
point of it showed what was under the picture instead.  Nothing looked at a
colour on this machine either, so nothing said.
"""

import json
import os
import struct
import subprocess
import sys
import tempfile
import time

try:
    import pytest
except ImportError:
    pytest = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import emulator  # noqa: E402
from regac.devices import CPC_HARDWARE_PALETTE, SPECTRUM_PALETTE  # noqa: E402
from test_inks_cpc import ALL_FOUR, ink, one_room  # noqa: E402

NEXT = os.path.join(ROOT, "z80", "next")
SOURCE = os.path.join(NEXT, "game.asm")
DATABASE = os.path.join(NEXT, "game.rgac")
DEFS = os.path.join(NEXT, "banks.inc")
IMAGE = os.path.join(NEXT, "game.nex")
LISTING = os.path.join(NEXT, "game.lst")

if pytest is not None:
    needs_tools = pytest.mark.skipif(
        not emulator.available(), reason="sjasmplus and ZEsarUX must be in tools/"
    )
else:

    def needs_tools(func):
        return func


def level(value):
    """One of the eight levels a channel has on this machine."""
    return min(range(8), key=lambda n: abs(n * 255 / 7 - value))


def shown(colour):
    """What the screen paints for a colour, once it has been through the nine
    bits of the palette: every channel to the nearest of its eight levels."""
    return tuple(round(level((colour >> shift) & 0xFF) * 255 / 7)
                 for shift in (16, 8, 0))


def amstrad(ink_number):
    return shown(CPC_HARDWARE_PALETTE[ink_number])


def build(ddb):
    with tempfile.TemporaryDirectory() as folder:
        adventure = os.path.join(folder, "inks.json")
        with open(adventure, "w", encoding="utf-8") as f:
            json.dump(ddb, f)
        subprocess.run(
            [sys.executable, "-m", "regac", "build", adventure, DATABASE,
             "-m", "next", "-b", "16k", "--defs", DEFS],
            cwd=ROOT, check=True, capture_output=True,
        )
    defines = ("AMSTRAD_PICTURES",) if ddb.get("model") == "CPC" else ()
    emulator.assemble(SOURCE, listing=LISTING, defines=defines)


def looked_at(session, folder, name):
    """The colours on the screen the emulator paints, and the border's."""
    path = os.path.join(folder, name + ".bmp")
    session.command(f"save-screen {path}")
    with open(path, "rb") as f:
        data = f.read()
    start = struct.unpack_from("<I", data, 10)[0]
    width, height = struct.unpack_from("<ii", data, 18)
    row = (width * 3 + 3) & ~3
    seen = set()
    for y in range(0, abs(height), 2):
        at = start + y * row
        for x in range(0, width, 2):
            blue, green, red = data[at + 3 * x:at + 3 * x + 3]
            seen.add((red, green, blue))
    blue, green, red = data[start + 4 * row + 12:start + 4 * row + 15]
    return seen, (red, green, blue)


def playing(ddb, looks=1, every=0.0):
    """Build the adventure, start it, and look at the screen once its room is
    up, `looks` times, `every` seconds apart."""
    build(ddb)
    out = []
    folder = tempfile.mkdtemp(prefix="regac-next-inks-")
    session = emulator.Session(machine="TBBlue")
    try:
        session.load(IMAGE)
        time.sleep(emulator.longer(10.0))       # loading, and the first picture
        for n in range(looks):
            out.append(looked_at(session, folder, f"look{n}"))
            time.sleep(every)
    finally:
        session.close()
    return out


@needs_tools
def test_a_picture_off_an_amstrad_puts_up_its_own_inks():
    """Its four pens in its own inks, the border in the first of them; and
    the picture it calls, which has inks of its own, changes none of them."""
    gfx = {"1": ALL_FOUR + [["CALL", 2]], "2": [["PLOT", 10, 100]]}
    inks = {"1": [3, 3, 26, 26, 18, 18, 2, 2], "2": [0, 0, 9, 9, 15, 15, 12, 12]}
    [(seen, border)] = playing(one_room(gfx, inks))
    wanted = {amstrad(n) for n in (3, 26, 18, 2)}
    assert seen == wanted, f"the screen shows {sorted(seen)}, and should {sorted(wanted)}"
    assert border == amstrad(3), f"the border is {border}, not the first ink"


@needs_tools
def test_a_pen_of_two_colours_flashes_while_the_game_waits():
    inks = {"1": [3, 3, 26, 9, 18, 18, 2, 2]}
    looks = playing(one_room({"1": ALL_FOUR}, inks), looks=12, every=0.15)
    shown_sets = {frozenset(seen) for seen, _ in looks}
    one = frozenset(amstrad(n) for n in (3, 9, 18, 2))
    other = frozenset(amstrad(n) for n in (3, 26, 18, 2))
    assert one in shown_sets, "the second of the pair never showed"
    assert other in shown_sets, "the first of the pair never showed"
    assert shown_sets <= {one, other}, f"something else changed: {shown_sets}"


@needs_tools
def test_the_text_of_an_amstrad_adventure_is_in_pen_one():
    """The picture is empty, so what is on the screen is the text: the paper,
    the letter in pen one, and the words after a change to three in pen
    three."""
    inks = {"1": [3, 3, 26, 26, 18, 18, 2, 2]}
    ddb = one_room({"1": []}, inks)
    ddb["locations"]["1"]["desc"] = "UN CUARTO " + ink(3) + "AZUL"
    [(seen, _)] = playing(ddb)
    wanted = {amstrad(n) for n in (3, 26, 2)}
    assert seen == wanted, f"the screen shows {sorted(seen)}, and should {sorted(wanted)}"


@needs_tools
def test_bright_magenta_is_not_the_colour_that_is_not_there():
    """A picture off a Spectrum filled in bright magenta shows bright magenta,
    and not what is under layer 2."""
    gfx = {"1": [["BRIGHT", 1], ["INK", 3], ["RECT", 20, 60, 100, 120],
                 ["FILL", 60, 90]]}
    [(seen, _)] = playing(one_room(gfx, model="SPECTRUM"))
    magenta = shown(SPECTRUM_PALETTE[11])
    assert magenta in seen, f"no bright magenta on the screen: {sorted(seen)}"


if __name__ == "__main__":
    test_bright_magenta_is_not_the_colour_that_is_not_there()
    test_a_picture_off_an_amstrad_puts_up_its_own_inks()
    test_a_pen_of_two_colours_flashes_while_the_game_waits()
    test_the_text_of_an_amstrad_adventure_is_in_pen_one()
    print("the Next shows the inks it is given")
