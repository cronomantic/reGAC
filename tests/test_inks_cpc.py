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
"""The colours an Amstrad shows, looked at as colours.

Every other test of this machine reads the screen as pens, which is what the
drawing is, and none of them ever looked at what colour a pen was.  So for as
long as the machine existed the interpreter chose its pens with the wrong
command to the gate array, set none of them, and showed the firmware's four
whatever it asked for; and nothing failed.  These look at the screen the
emulator paints, as a picture, and ask it what colours are on it.

What they hold an adventure off an Amstrad to is the original, read at $0538
of its interpreter: the picture of a room sets its own inks, the border from
the first pair and then each pen; a picture called from another steps over
its own, at $1C64; and a pen whose pair is two colours flashes between them,
the second of the pair first.  An adventure off a Spectrum is drawn with the
Spectrum's rules, and each of its pictures is shown in the four inks chosen
for it.
"""

import os
import struct
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
from regac.binary import Database  # noqa: E402
from regac.devices import CPC_HARDWARE_PALETTE, cpc_picture_colours  # noqa: E402
from test_markers_z80 import adventure  # noqa: E402

CPC = os.path.join(ROOT, "z80", "cpc")
SOURCE = os.path.join(CPC, "game.asm")
DATABASE = os.path.join(CPC, "game.rgac")
BINARY = os.path.join(CPC, "game.bin")
LISTING = os.path.join(CPC, "game.lst")
LOADS_AT = 0x4000
START_INKS = {1, 24, 20, 6}     # the firmware's, and what a Spectrum one keeps

if pytest is not None:
    needs_tools = pytest.mark.skipif(
        not emulator.available(), reason="sjasmplus and ZEsarUX must be in tools/"
    )
else:

    def needs_tools(func):
        return func


# Every pen on the screen: an outline in the pen a picture starts in, and a
# fill in each of the other two.  The paper is pen nought.
ALL_FOUR = [
    ["RECT", 20, 60, 100, 120], ["PENS", 2, 2], ["FILL", 60, 90],
    ["PENS", 3, 3], ["FILL", 150, 100],
]


def one_room(gfx, inks=None, model="CPC"):
    ddb = adventure(rooms={"1": {"graphic_id": 1, "exits": [], "desc": "UN CUARTO"}})
    ddb["model"] = model
    ddb["gfx"] = gfx
    if inks is not None:
        ddb["gfx_inks"] = inks
    return ddb


# The firmware's number of every colour the machine can make, which is how a
# colour the emulator painted is named.
INK_OF = {colour: n for n, colour in enumerate(CPC_HARDWARE_PALETTE)}


def looked_at(session, folder, name):
    """The screen as the emulator paints it, border and all: which inks are
    on it, and which the border is."""
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
    corner = (red, green, blue)
    for colour in seen | {corner}:
        assert (colour[0] << 16) | (colour[1] << 8) | colour[2] in INK_OF, (
            f"the emulator painted {colour}, which is none of the Amstrad's colours"
        )
    def ink(colour):
        return INK_OF[(colour[0] << 16) | (colour[1] << 8) | colour[2]]
    return {ink(colour) for colour in seen}, ink(corner)


def playing(ddb, looks=1, every=0.0):
    """Build the adventure, start it, wait for its room, and look at the
    screen `looks` times, `every` seconds apart."""
    with open(DATABASE, "wb") as f:
        f.write(Database(ddb, machine="cpc").build())
    amstrad = ddb.get("model") == "CPC"
    listing = emulator.assemble(SOURCE, listing=LISTING,
                                defines=("AMSTRAD_PICTURES",) if amstrad else ())
    ready = emulator.label_address(listing, "vm_location")
    with open(BINARY, "rb") as f:
        blob = f.read()

    out = []
    folder = tempfile.mkdtemp(prefix="regac-inks-")
    session = emulator.Session(machine="CPC6128")
    try:
        time.sleep(emulator.longer(3.0))
        assert session.put(blob, LOADS_AT, then=lambda: session.command(
            f"set-register PC={LOADS_AT:04X}H")), "the game never landed whole"
        deadline = time.time() + emulator.longer(30.0)
        while time.time() < deadline and session.read(ready, 1)[0] != 1:
            time.sleep(0.2)
        time.sleep(emulator.longer(4.0))    # the picture, and the prompt
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
    assert seen == {3, 26, 18, 2}, f"the screen shows inks {sorted(seen)}"
    assert border == 3, f"the border is ink {border}, not the first of the picture's"


@needs_tools
def test_a_pen_of_two_colours_flashes_while_the_game_waits():
    """Pen one is 26 and 9: the screen shows the one and then the other
    while the game waits for an order, and nothing else of it moves."""
    inks = {"1": [3, 3, 26, 9, 18, 18, 2, 2]}
    looks = playing(one_room({"1": ALL_FOUR}, inks), looks=12, every=0.15)
    shown = {frozenset(seen) for seen, _ in looks}
    assert frozenset({3, 9, 18, 2}) in shown, "the second of the pair never showed"
    assert frozenset({3, 26, 18, 2}) in shown, "the first of the pair never showed"
    assert shown <= {frozenset({3, 9, 18, 2}), frozenset({3, 26, 18, 2})}, (
        f"something else changed: {sorted(sorted(s) for s in shown)}"
    )
    assert {border for _, border in looks} == {3}, "the border flashed with pen one"


@needs_tools
def test_a_picture_off_a_spectrum_is_shown_in_the_inks_chosen_for_it():
    """Red on white, drawn with the Spectrum's rules: what is on the screen is
    the inks chosen for this picture and nothing else, red and white among
    them where the picture has them.  And BORDER, which only a Spectrum
    picture has, gives the border the ink its colour came to."""
    gfx = {"1": [["INK", 2], ["RECT", 20, 60, 100, 120], ["FILL", 60, 90],
                 ["BORDER", 6]]}
    inks, pens = cpc_picture_colours(gfx, 1)
    [(seen, border)] = playing(one_room(gfx, model="SPECTRUM"))
    assert seen <= set(inks), f"the screen shows inks {sorted(seen)}, chosen {inks}"
    assert inks[pens[2]] in seen, "the red of the picture is not on the screen"
    assert inks[pens[7]] in seen, "the white of the picture is not on the screen"
    assert border == inks[pens[6]], (
        f"BORDER 6 is ink {inks[pens[6]]} for this picture, and the border is {border}"
    )


# A change of ink inside a text, as it travels: the code that says the ink
# changes, and the colour as a character.
def ink(colour):
    return "" + chr(ord("0") + colour)


@needs_tools
def test_the_text_of_an_amstrad_adventure_is_in_pen_one_and_ink_names_a_pen():
    """The original prints in pen one on pen nought and never changes them; a
    change of ink in a message is ours, and on this machine it names a pen.
    The picture is empty, so what is on the screen is the text: the paper,
    the letter in pen one, and the words after the change in pen three.  Pen
    one and not two is the point of it: the two were crossed once, and with a
    change to two the screen shows the same three inks either way."""
    inks = {"1": [3, 3, 26, 26, 18, 18, 2, 2]}
    ddb = one_room({"1": []}, inks)
    ddb["locations"]["1"]["desc"] = "UN CUARTO " + ink(3) + "AZUL"
    [(seen, _)] = playing(ddb)
    assert seen == {3, 26, 2}, f"the screen shows inks {sorted(seen)}"


@needs_tools
def test_the_text_of_a_spectrum_adventure_takes_the_pictures_pens():
    """White on black, as on the Spectrum, in the inks of the picture closest
    to them -- which are pens one and nought -- and a change of ink in a
    message is a colour, in the pen that colour comes to in this picture."""
    gfx = {"1": [["INK", 2], ["RECT", 20, 60, 100, 120], ["FILL", 60, 90]]}
    inks, pens = cpc_picture_colours(gfx, 1)
    ddb = one_room(gfx, model="SPECTRUM")
    ddb["locations"]["1"]["desc"] = "UN CUARTO " + ink(6) + "AMARILLO"
    [(seen, _)] = playing(ddb)
    assert pens[0] == 0 and pens[7] == 1, "the text's paper and letter are not pens 0 and 1"
    wanted = {inks[pens[0]], inks[pens[7]], inks[pens[2]], inks[pens[6]]}
    assert seen == wanted, f"the screen shows inks {sorted(seen)}, and it should be {sorted(wanted)}"


if __name__ == "__main__":
    test_a_picture_off_an_amstrad_puts_up_its_own_inks()
    test_a_pen_of_two_colours_flashes_while_the_game_waits()
    test_a_picture_off_a_spectrum_is_shown_in_the_inks_chosen_for_it()
    test_the_text_of_an_amstrad_adventure_is_in_pen_one_and_ink_names_a_pen()
    test_the_text_of_a_spectrum_adventure_takes_the_pictures_pens()
    print("the Amstrad shows the inks it is given")
