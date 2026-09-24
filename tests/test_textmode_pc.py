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
"""TEXT on a PC, as on every other machine: see test_textmode_z80.py.

A long message three times over, in the nine rows under the picture, scrolls
inside them and never reaches it, until TEXT says the window is the whole
screen and then it does; and with TEXT on, a new room draws no picture.  The
screens are the ones the game wrote each time it asked for an order.
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
from test_textmode_z80 import a_room_and_a_verb  # noqa: E402

STOP = 99                       # a verb of our own, so that the game ends

if pytest is not None:
    needs_tools = pytest.mark.skipif(
        not dosbox.available(), reason="NASM and DOSBox-X must be on the path"
    )
else:

    def needs_tools(func):
        return func


def picture_area(screen):
    """The sixteen character rows at the top: the first 128 scan lines, which
    are the first sixty four lines of each of the two banks."""
    return screen[:64 * 80] + screen[0x2000:0x2000 + 64 * 80]


def picture_area_after(tmp_path, orders):
    """What the picture's rows held when the game first asked, and when it
    asked again after each of the orders."""
    ddb = a_room_and_a_verb()
    ddb["verbs"]["FIN"] = STOP
    ddb["lpcs"] += [["PUSH", STOP], ["VERB"], ["IF"], ["EXIT"], ["END"]]
    os.makedirs(tmp_path, exist_ok=True)
    folder = str(tmp_path)
    pc_game.build(ddb, folder)
    said, screen = pc_game.play(folder, "".join(order + ENTER for order in orders)
                                + "FIN" + ENTER + "X")
    assert screen is not None, f"the game never ended: {said}"
    out = []
    for asked in range(len(orders) + 1):
        with open(os.path.join(folder, f"S{asked:02X}.BIN"), "rb") as f:
            out.append(picture_area(f.read()))
    return out


@needs_tools
def test_a_long_message_keeps_to_its_window_until_text_says_otherwise(tmp_path):
    drawn, after_plain, after_text = picture_area_after(tmp_path,
                                                        ["LARGO", "TEXTO"])
    assert any(drawn), "the picture was never drawn"
    assert after_plain == drawn, (
        "a long message reached above the picture without TEXT")
    assert after_text != after_plain, (
        "TEXT did not give the text the whole screen")


@needs_tools
def test_with_text_on_a_room_draws_no_picture(tmp_path):
    drawn, with_pictures = picture_area_after(tmp_path / "a", ["ANDA"])
    first, with_text = picture_area_after(tmp_path / "b", ["CALLA"])
    assert with_pictures != drawn, "the other room drew no picture"
    assert with_text == first, (
        "the room drew its picture although TEXT had asked for none")
