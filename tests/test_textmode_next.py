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
"""TEXT on a Spectrum Next, the half that was missing: the window.

What TEXT and PICT do was measured on the original and is told in
test_textmode_z80.py and doc/pendiente.md.  The half that stops the pictures
this machine has had all along; the half that gives the text the whole screen
was put off for a wall at $A000 that turned out to be the fill's mask.  So
this is that test again on a Next: a long message scrolls inside the eight
rows under the picture and never reaches it, until TEXT says the window is the
whole screen and then it does; and with TEXT on, a new room draws no picture.

The screen here is three pieces of layer 2 and only one is ever seen, so
scrolling all of it is a different walk from scrolling the text: the picture
is read straight out of the machine's pages, whichever one is mapped.
"""

import json
import os
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
from test_textmode_z80 import a_room_and_a_verb  # noqa: E402

NEXT = os.path.join(ROOT, "z80", "next")
SOURCE = os.path.join(NEXT, "game.asm")
DATABASE = os.path.join(NEXT, "game.rgac")
DEFS = os.path.join(NEXT, "banks.inc")
IMAGE = os.path.join(NEXT, "game.nex")
LISTING = os.path.join(NEXT, "game.lst")

L2_AT = emulator.Session.NEXT_PAGE_0 + 16 * 8192
PICTURE_BYTES = 256 * 128       # the two pieces a picture is drawn in
ENTER = chr(13)

if pytest is not None:
    needs_tools = pytest.mark.skipif(
        not emulator.available(), reason="sjasmplus and ZEsarUX must be in tools/"
    )
else:

    def needs_tools(func):
        return func


def build():
    with tempfile.TemporaryDirectory() as folder:
        adventure = os.path.join(folder, "textmode.json")
        with open(adventure, "w", encoding="utf-8") as f:
            json.dump(a_room_and_a_verb(), f)
        subprocess.run(
            [sys.executable, "-m", "regac", "build", adventure, DATABASE,
             "-m", "next", "-b", "16k", "--defs", DEFS],
            cwd=ROOT, check=True, capture_output=True,
        )
    emulator.assemble(SOURCE, listing=LISTING)


def picture_area_after(orders, settle=5.0):
    """What the picture's lines held after the game started and after each of
    the orders."""
    build()
    out = []
    session = emulator.Session(machine="TBBlue")
    try:
        session.load(IMAGE)
        time.sleep(settle + 5.0)        # loading, and the first picture
        out.append(bytes(session.read(L2_AT, PICTURE_BYTES, zone=session.RAM)))
        for order in orders:
            session.type(order + ENTER)
            time.sleep(settle)
            out.append(bytes(session.read(L2_AT, PICTURE_BYTES,
                                          zone=session.RAM)))
    finally:
        session.close()
    return out


@needs_tools
def test_a_long_message_keeps_to_its_window_until_text_says_otherwise():
    """A long message three times over, in an eight row window, scrolls
    inside it and never reaches the picture.  With TEXT the window is the
    whole screen, and it does."""
    drawn, after_plain, after_text = picture_area_after(["LARGO", "TEXTO"])
    assert len(set(drawn)) > 1, "the picture was never drawn"
    assert after_plain == drawn, (
        "a long message reached above the picture without TEXT"
    )
    assert after_text != after_plain, (
        "TEXT did not give the text the whole screen"
    )


@needs_tools
def test_with_text_on_a_room_draws_no_picture():
    """The same walk to the same room, once with pictures and once with TEXT
    on: with TEXT the other room's picture is never drawn."""
    with_pictures = picture_area_after(["ANDA"])[-1]
    with_text = picture_area_after(["CALLA"])[-1]
    assert with_pictures != with_text, (
        "the room drew its picture although TEXT had asked for none"
    )


if __name__ == "__main__":
    test_a_long_message_keeps_to_its_window_until_text_says_otherwise()
    test_with_text_on_a_room_draws_no_picture()
    print("TEXT gives the text of a Next the whole screen")
