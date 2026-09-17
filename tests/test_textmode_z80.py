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
"""TEXT and PICT, which were written down and never read.

What they do was measured on the original, by writing two conditions of our
own over the start of MegaCorp's low priority table in the machine's memory:

  - TEXT does not clear anything and does not move the cursor.  What it does
    is give the text the whole screen, which shows the moment something is
    printed: the picture is dragged up with everything else.
  - With TEXT on, a new room does not draw its picture.
  - PICT does nothing at the moment it runs.  The window comes back when a
    picture is next drawn, which with PICT on is the next room described.

So there is no order that says "back to pictures": TEXT puts the top of the
window at nought, and drawing a picture puts it back.  See doc/pendiente.md.

This is the Spectrum's, where all of it is done.  The Amstrad has all of it
too, and its own test in test_textmode_cpc.py, and so have the Next and the
PCW, in test_textmode_next.py and test_textmode_pcw.py.
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
from test_markers_z80 import adventure, build  # noqa: E402

SPECTRUM = os.path.join(ROOT, "z80", "spectrum")
SNAPSHOT = os.path.join(SPECTRUM, "game.sna")
ENTER = chr(13)

PICTURE_AREA = 0x4000           # the top sixteen rows, which is two thirds
PICTURE_BYTES = 0x1000
PLAIN, WITH_TEXT, GO, GO_QUIETLY = 1, 2, 3, 4
# Two hundred and forty characters, which is seven lines and a half, said
# three times.  It could be one message of seven hundred now that a message
# is printed a word at a time; three of these is simply what this test has
# always said, and the Amstrad's says the same.
LONG = ("UN CUARTO MUY LARGO DE DESCRIBIR " * 8)[:240]

if pytest is not None:
    needs_tools = pytest.mark.skipif(
        not emulator.available(), reason="sjasmplus and ZEsarUX must be in tools/"
    )
else:

    def needs_tools(func):
        return func


def a_room_and_a_verb():
    """Two rooms with a picture each, and four ways of asking for things:
    a long message, the same with TEXT first, a walk to the other room, and
    a walk to it with TEXT on."""
    def when(verb, *does):
        return [["PUSH", verb], ["VERB"], ["IF"]] + list(does) + [["END"]]

    rules = when(PLAIN, ["PUSH", 1], ["MESS"], ["PUSH", 1], ["MESS"],
                 ["PUSH", 1], ["MESS"], ["WAIT"])
    rules += when(WITH_TEXT, ["TEXT"], ["PUSH", 1], ["MESS"], ["PUSH", 1],
                  ["MESS"], ["PUSH", 1], ["MESS"], ["WAIT"])
    rules += when(GO, ["PUSH", 2], ["GOTO"])
    rules += when(GO_QUIETLY, ["TEXT"], ["PUSH", 2], ["GOTO"])
    ddb = adventure(lpcs=rules, messages={"1": LONG}, rooms={
        "1": {"graphic_id": 1, "exits": [], "desc": "UN CUARTO"},
        "2": {"graphic_id": 2, "exits": [], "desc": "OTRO CUARTO"},
    })
    ddb["verbs"] = {"LARGO": PLAIN, "TEXTO": WITH_TEXT,
                    "ANDA": GO, "CALLA": GO_QUIETLY}
    ddb["gfx"] = {
        "1": [["PAPER", 0], ["RECT", 40, 60, 200, 150], ["FILL", 120, 100]],
        "2": [["PAPER", 0], ["ELLIPSE", 128, 110, 60, 40], ["FILL", 128, 110]],
    }
    return ddb


def picture_area_after(orders, settle=5.0):
    """What the sixteen rows the picture lives in held after each order."""
    build(a_room_and_a_verb())
    out = []
    session = emulator.Session()
    try:
        session.load(SNAPSHOT)
        time.sleep(settle + 3.0)        # the first picture takes a while
        out.append(bytes(session.read(PICTURE_AREA, PICTURE_BYTES)))
        for order in orders:
            session.type(order + ENTER)
            time.sleep(settle)
            out.append(bytes(session.read(PICTURE_AREA, PICTURE_BYTES)))
    finally:
        session.close()
    return out


@needs_tools
def test_a_long_message_keeps_to_its_window_until_text_says_otherwise():
    """Twelve lines in an eight line window scroll inside it and never reach
    the picture.  With TEXT the window is the whole screen, and they do."""
    drawn, after_plain, after_text = picture_area_after(["LARGO", "TEXTO"])
    assert any(drawn), "the picture was never drawn"
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
    print("TEXT gives the text the screen and PICT gives it back")
