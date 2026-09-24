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
# The interpreters in z80/ and x86/ are not part of this program and are given
# under the MIT licence instead: see z80/LICENSE and x86/LICENSE.
#
"""The colours on a PC: the palette each picture puts up, the one a
flashing pen changes it to while the game waits, and the text in the values
its colours come to.  What test_inks_cpc.py asks of the Amstrad.

The palette is two ports that cannot be read back, so the test build writes
down every palette it puts up, in PALETTE.BIN; the text is on the card, in
the screen the game wrote when it asked for its first order.
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

import dosbox  # noqa: E402
import pc_game  # noqa: E402
from pc_game import ENTER  # noqa: E402
from regac.devices import (cga_amstrad_colours, cga_amstrad_flash,  # noqa: E402
                           cga_picture_colours)
from test_inks_cpc import ink, one_room  # noqa: E402
from test_markers_z80 import QUIT_VERB  # noqa: E402

START = (0x30, 0x0A)            # the palette of a screen with no picture

if pytest is not None:
    needs_tools = pytest.mark.skipif(
        not dosbox.available(), reason="NASM and DOSBox-X must be on the path"
    )
else:

    def needs_tools(func):
        return func


def playing(tmp_path, ddb, wait_first=0):
    """Play one room: look at it for a while, then leave.  What comes back is
    every palette put up and the screen at the first question."""
    ddb["lpcs"] = [["PUSH", QUIT_VERB], ["VERB"], ["IF"], ["EXIT"], ["END"]]
    folder = str(tmp_path)
    pc_game.build(ddb, folder)
    # the first key comes that many seconds of asking later
    said, screen = pc_game.play(folder, "SALIR" + ENTER + "X",
                                start=pc_game.START_FRAMES + 50 * wait_first)
    assert screen is not None, f"the game never ended: {said}"
    with open(os.path.join(folder, "PALETTE.BIN"), "rb") as f:
        raw = f.read()
    palettes = [(raw[at], raw[at + 1]) for at in range(0, len(raw), 2)]
    with open(os.path.join(folder, "S00.BIN"), "rb") as f:
        asked = f.read()
    return palettes, asked


def text_values(screen):
    """The values in the nine rows under the picture."""
    return {pc_game.pixel(screen, x, y) for y in range(128, 200)
            for x in range(320)}


@needs_tools
def test_a_pen_that_flashes_changes_the_palette_while_the_game_waits(tmp_path):
    """Pen nought is black and white in turn, and it is dealt to the
    background, which can be any colour: so the palette goes from the one to
    the other while the game waits for an order, and nothing else of it
    moves.  Black first: the Amstrad shows the second of a pair first."""
    gfx = {"1": [["RECT", 20, 60, 100, 120]]}
    inks = {"1": [26, 0, 6, 6, 18, 18, 2, 2]}
    chosen = cga_amstrad_colours(gfx, 1, inks["1"])
    background, trio, _ = chosen
    shown = (trio.select(background), trio.mode())
    other = cga_amstrad_flash(gfx, 1, inks["1"], chosen)
    assert other != shown, "this picture was meant to be one that can flash"
    palettes, _ = playing(tmp_path, one_room(gfx, inks), wait_first=4)
    assert palettes[0] == START, palettes
    assert palettes[1] == shown, f"the picture put up {palettes[1]}, not {shown}"
    flashing = palettes[2:]
    assert len(flashing) >= 4, f"it flashed {len(flashing)} times in the wait"
    assert flashing[0::2] == [other] * len(flashing[0::2]), flashing
    assert flashing[1::2] == [shown] * len(flashing[1::2]), flashing


@needs_tools
def test_a_picture_that_cannot_flash_leaves_the_palette_alone(tmp_path):
    gfx = {"1": [["RECT", 20, 60, 100, 120]]}
    inks = {"1": [0, 0, 6, 6, 18, 18, 2, 2]}
    palettes, _ = playing(tmp_path, one_room(gfx, inks), wait_first=2)
    assert len(palettes) == 2, palettes


@needs_tools
def test_the_text_of_an_amstrad_adventure_is_in_pen_one_and_ink_names_a_pen(
        tmp_path):
    """The original prints in pen one on pen nought, and a change of ink in a
    message names a pen: here the words after it are in pen three.  Each in
    the value that pen was dealt."""
    gfx = {"1": [["RECT", 20, 60, 100, 120]]}
    inks = {"1": [3, 3, 26, 26, 18, 18, 2, 2]}
    ddb = one_room(gfx, inks)
    ddb["locations"]["1"]["desc"] = "UN CUARTO " + ink(3) + "AZUL"
    _, values = cga_amstrad_colours(gfx, 1, inks["1"])[1:]
    _, asked = playing(tmp_path, ddb)
    wanted = {values[0], values[1], values[3]}
    assert text_values(asked) == wanted, (
        f"the text is in values {text_values(asked)}, not {wanted}")


@needs_tools
def test_the_text_of_a_spectrum_adventure_is_in_its_colours_values(tmp_path):
    """White on black, and a change of ink is a colour: each in the value it
    comes to in the picture on the screen."""
    gfx = {"1": [["INK", 2], ["RECT", 20, 60, 100, 120], ["FILL", 60, 90]]}
    ddb = one_room(gfx, model="SPECTRUM")
    ddb["locations"]["1"]["desc"] = "UN CUARTO " + ink(6) + "AMARILLO"
    _, _, values = cga_picture_colours(gfx, 1)
    _, asked = playing(tmp_path, ddb)
    wanted = {values[0], values[7], values[6]}
    assert text_values(asked) == wanted, (
        f"the text is in values {text_values(asked)}, not {wanted}")
