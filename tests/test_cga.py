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
"""The PC's CGA, before there is an interpreter to draw on it.

Every machine got its device first and its interpreter after, and this is
that step for the PC: what a picture looks like there and where every point of
it goes in the card's memory, so that the interpreter, when it comes, has
something to be compared with -- a dump of B800 against cga_screen.

The drawing is not the CGA's: it is the Spectrum's for an adventure off a
Spectrum and the Amstrad's for one off an Amstrad, the same devices every
other machine is held to.  What is the CGA's is the four colours -- a
background of sixteen and a trio of six -- and the memory.
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from regac.binary import Database, Reader  # noqa: E402
from regac.devices import (CGA_BANK, CGA_PALETTE, CGA_SCREEN_BYTES, CGA_TRIOS,  # noqa: E402
                           CPC_HARDWARE_PALETTE, SPECTRUM_PALETTE,
                           AmstradDevice, PixelDevice, cga_amstrad_colours,
                           cga_amstrad_flash, cga_colours, cga_picture_colours,
                           cga_screen, device_for, nearest)
from regac.gfx import Renderer  # noqa: E402


class Points:
    """A picture with a handful of points in it, a byte a pixel."""

    def __init__(self, points):
        self.values = bytearray(256 * 128)
        for (x, row), value in points.items():
            self.values[row * 256 + x] = value

    def vram(self):
        return bytes(self.values)


def test_a_point_goes_where_the_card_shows_it():
    """Four pixels to a byte, the first in the top two bits; the even rows in
    the first bank and the odd ones in the second; the picture eight bytes in,
    which is the middle of the 320."""
    screen = cga_screen(Points({(0, 0): 1, (1, 0): 2, (0, 1): 3, (255, 127): 3,
                                (4, 2): 2}))
    assert len(screen) == CGA_SCREEN_BYTES
    assert screen[8] == 0b01100000              # row 0: pixels 0 and 1
    assert screen[CGA_BANK + 8] == 0b11000000   # row 1, in the second bank
    assert screen[80 + 9] == 0b10000000         # row 2: x=4 is the next byte
    assert screen[CGA_BANK + 63 * 80 + 8 + 63] == 0b00000011   # the last one
    assert sum(1 for byte in screen if byte) == 4


def test_the_ports_say_which_four():
    """Port 3D9h carries the background, the brightness and which of the two
    colour sets; the third set is port 3D8h taking the colour off."""
    names = {trio.name: trio for trio in CGA_TRIOS}
    assert names["paleta 1 brillante"].select(0) == 0x30
    assert names["paleta 0"].select(9) == 0x09
    assert names["modo 5 brillante"].mode() == 0x0E
    assert names["paleta 0"].mode() == 0x0A
    assert len(CGA_TRIOS) == 6


def test_a_picture_off_a_spectrum_is_the_spectrums_in_four_cga_colours():
    gfx = {"1": [["INK", 2], ["RECT", 20, 60, 100, 120], ["FILL", 60, 90]]}
    device = device_for("cga", gfx, 1)
    assert isinstance(device, PixelDevice)
    assert set(device.palette) <= set(CGA_PALETTE)
    Renderer(gfx, device).run(1)
    # the red of the picture is shown in the card's red, and the white
    # around it in its white or grey
    shown = {device.palette[v] for v in device.vram()}
    assert 0xAA0000 in shown or 0xFF5555 in shown, shown


def test_the_pens_of_an_amstrad_picture_are_dealt_to_suit_the_colours():
    """Black, bright yellow and bright white, most of it white: the white goes
    to the background, which can be any colour, rather than to the place of
    its pen in a trio that has none.  The dealing is one to one, so what tells
    two pens apart still does."""
    gfx = {"1": [["PENS", 2, 2], ["FILL", 100, 100], ["INK", 1],
                 ["RECT", 20, 60, 100, 120], ["PENS", 1, 1], ["FILL", 60, 90],
                 ["INK", 0], ["LINE", 30, 70, 90, 110]]}
    header = [0, 0, 24, 24, 26, 26, 6, 6]
    background, trio, values = cga_amstrad_colours(gfx, 1, header)
    assert sorted(values) == [0, 1, 2, 3]
    assert values[2] == 0 and CGA_PALETTE[background] == 0xFFFFFF, (background, values)
    ddb = {"model": "CPC", "gfx": gfx, "gfx_inks": {"1": header}}
    device = device_for("cga", gfx, 1, ddb)
    assert isinstance(device, AmstradDevice)
    Renderer(gfx, device).run(1)
    screen = cga_screen(device)
    # the white of the picture, pen two, is written as value nought
    assert device.pens[0] == 2 and (screen[8] >> 6) == 0


def test_an_amstrad_picture_keeps_its_pens_on_the_card():
    """Dealt out or not, the points that share a pen share a value, and the
    ones that do not, do not: the Amstrad's rules hold."""
    gfx = {"1": [["RECT", 20, 60, 100, 120], ["PENS", 2, 3], ["FILL", 60, 90]]}
    header = [1, 1, 24, 24, 20, 20, 6, 6]
    device = device_for("cga", gfx, 1, {"model": "CPC", "gfx": gfx,
                                         "gfx_inks": {"1": header}})
    Renderer(gfx, device).run(1)
    screen = cga_screen(device)
    pens = device.vram()
    seen = {}
    for row in range(128):
        base = (row & 1) * CGA_BANK + (row >> 1) * 80 + 8
        for x in range(256):
            value = (screen[base + (x >> 2)] >> (6 - 2 * (x & 3))) & 3
            assert seen.setdefault(pens[row * 256 + x], value) == value
    assert len(set(seen.values())) == len(seen)


if __name__ == "__main__":
    test_a_point_goes_where_the_card_shows_it()
    test_the_ports_say_which_four()
    test_a_picture_off_a_spectrum_is_the_spectrums_in_four_cga_colours()
    test_the_pens_of_an_amstrad_picture_are_dealt_to_suit_the_colours()
    test_an_amstrad_picture_keeps_its_pens_on_the_card()
    print("the CGA shows what the reference draws")


def unpacked(head):
    """The two port bytes and the sixteen values out of a picture's head."""
    values = [(head[2 + n // 4] >> (2 * (n % 4))) & 3 for n in range(16)]
    return head[0], head[1], values


def smallest(gfx, model="48K", inks=None):
    ddb = {
        "font": [0] * 1024, "verbs": {"N": 1}, "nouns": {}, "adverbs": {},
        "pronouns": [], "messages": {"1": "x"},
        "objects": {"1": {"weight": 1, "initial_loc": 1, "name": "x"}},
        "locations": {"1": {"graphic_id": 1, "exits": [], "desc": "x"}},
        "hpcs": [], "lpcs": [], "lcs": {}, "model": model,
        "punctuation": list("\0 .,-!?:"), "separators": [], "init_loc": 1,
        "no_objs_msg": "x", "gfx": gfx,
    }
    if inks:
        ddb["gfx_inks"] = inks
    return ddb


def test_a_picture_carries_its_palette_to_the_pc():
    """What the interpreter puts up for a picture is what the reference drew
    it in: the two port bytes of its background and trio, and the value each
    of the sixteen colours comes to."""
    gfx = {"1": [["PAPER", 1], ["INK", 6], ["RECT", 20, 60, 100, 120],
                 ["BGFILL", 60, 90]]}
    reader = Reader(Database(smallest(gfx), machine="pc").build())
    assert reader.picture_head() == 8
    head = reader.picture_inks()["1"]
    select, mode, values = unpacked(head)
    background, trio, wanted = cga_picture_colours(gfx, 1)
    assert (select, mode) == (trio.select(background), trio.mode())
    assert values == list(wanted)
    assert head[6:] == [select, mode], "a picture off a Spectrum never flashes"


def test_an_amstrad_picture_carries_its_pens_to_the_pc_four_times_over():
    """Off an Amstrad the sixteen are the four pens, dealt out as the
    reference deals them, over and over: an ink's low two bits are its pen,
    so the interpreter looks an ink up as it comes."""
    gfx = {"1": [["INK", 2], ["RECT", 20, 60, 100, 120]]}
    header = [0, 0, 24, 24, 26, 26, 6, 6]
    ddb = smallest(gfx, model="CPC", inks={"1": header})
    reader = Reader(Database(ddb, machine="pc").build())
    select, mode, values = unpacked(reader.picture_inks()["1"])
    background, trio, pens = cga_amstrad_colours(gfx, 1, header)
    assert (select, mode) == (trio.select(background), trio.mode())
    assert values == [pens[n & 3] for n in range(16)]


def the_trio(select, mode):
    """Which background and trio two port bytes put up."""
    for trio in CGA_TRIOS:
        for background in range(16):
            if (trio.select(background), trio.mode()) == (select, mode):
                return background, trio
    raise AssertionError(f"no palette is {select:02X} {mode:02X}")


def test_a_flashing_pen_on_the_background_flashes_and_nothing_else_moves():
    """A CGA can change its background or its whole trio and nothing
    between, so a pen flashes where it can and a pen that does not flash is
    never moved to make room for one that does.  Here the flashing pen is the
    one dealt to the background, which can be any of the sixteen, and it
    goes to the nearest of them to its other ink."""
    gfx = {"1": [["INK", 1], ["RECT", 20, 60, 100, 120],
                 ["PENS", 1, 1], ["FILL", 60, 90]]}
    # pen nought flashes black and bright white; one, two and three are still
    header = [26, 0, 6, 6, 18, 18, 2, 2]
    chosen = cga_amstrad_colours(gfx, 1, header)
    background, trio, values = chosen
    alt_background, alt_trio = the_trio(*cga_amstrad_flash(gfx, 1, header, chosen))
    before = cga_colours(background, trio)
    after = cga_colours(alt_background, alt_trio)
    for pen in (1, 2, 3):
        assert before[values[pen]] == after[values[pen]], f"pen {pen} moved"
    if values[0] == 0:
        assert after[0] == CGA_PALETTE[nearest(CPC_HARDWARE_PALETTE[26],
                                               CGA_PALETTE)]


def test_a_pen_that_cannot_flash_alone_does_not_flash():
    """When the flashing pen is in the trio, and no other trio keeps the
    still pens where they are, the second palette is the first."""
    gfx = {"1": [["INK", 1], ["RECT", 20, 60, 100, 120]]}
    header = [0, 0, 24, 24, 20, 20, 17, 0]
    chosen = cga_amstrad_colours(gfx, 1, header)
    background, trio, values = chosen
    flashed = cga_amstrad_flash(gfx, 1, header, chosen)
    alt_background, alt_trio = the_trio(*flashed)
    before = cga_colours(background, trio)
    after = cga_colours(alt_background, alt_trio)
    for pen in (0, 1, 2):
        assert before[values[pen]] == after[values[pen]], f"pen {pen} moved"


def test_the_colours_a_screen_starts_in_are_the_references():
    """Before any picture the interpreter shows the reference's own screen
    without a picture: cyan, magenta and white on black.  x86/cga.asm holds
    what each colour comes to in that, which is checked here against it."""
    four = cga_colours(0, CGA_TRIOS[3])
    wanted = [nearest(c, four) for c in SPECTRUM_PALETTE]
    source = open(os.path.join(ROOT, "x86", "cga.asm"), encoding="utf-8").read()
    table = source[source.index("%else"):].split("colour_value:")[1]
    found = [int(n) for n in table.split(chr(10))[0].replace("db", "").split(",")]
    assert found == wanted
    assert "START_SELECT    equ 30h" in source and CGA_TRIOS[3].select(0) == 0x30
    assert "START_MODE      equ 0Ah" in source and CGA_TRIOS[3].mode() == 0x0A
