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
"""TEXT on an MSX, which was the one machine of the five without this test.

What TEXT and PICT do was measured on the original and is told in
test_textmode_z80.py and doc/pendiente.md.  The Spectrum, the Amstrad, the
Next and the PCW have each had this pair of tests for a while; this machine
had the code -- two bytes, the first row and how many move -- and nothing
watching it, which is the same as not knowing.

So it is that test again here: a long message scrolls inside the eight rows
under the picture and never reaches it, until TEXT says the window is the
whole screen and then it does; and with TEXT on, a new room draws no picture.

What is looked at is the video chip's own memory and not the processor's: the
picture is the first two blocks of the pattern table with their two of the
colour table, and the text is the third of each.  A message that has reached
above the picture shows in the first two.
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
from test_game_msx import SOURCE, VRAM, start_playing  # noqa: E402
# This machine is not typed at with session.type: its keyboard is read
# through the same chip as the sound, and what works is its own helper.
from test_keyboard_msx import type_them  # noqa: E402
from test_textmode_z80 import a_room_and_a_verb  # noqa: E402

MSX = os.path.join(ROOT, "z80", "msx")
DATABASE = os.path.join(MSX, "game.rgac")
LISTING = os.path.join(MSX, "game.lst")
ENTER = chr(13)

if pytest is not None:
    needs_tools = pytest.mark.skipif(
        not emulator.available(), reason="sjasmplus and ZEsarUX must be in tools/"
    )
else:

    def needs_tools(func):
        return func


def picture_area(session):
    """The sixteen rows the picture lives in, shapes and colours both: a
    message that has climbed above the picture changes one or the other."""
    return (bytes(session.read(MSX_PATTERNS, MSX_PICTURE_BYTES, zone=VRAM))
            + bytes(session.read(MSX_COLOURS, MSX_PICTURE_BYTES, zone=VRAM)))


def picture_area_after(orders, settle=6.0):
    """What those rows held once the game was going, and after each order."""
    database = Database(a_room_and_a_verb(), machine="msx")
    with open(DATABASE, "wb") as f:
        f.write(database.build())
    listing = emulator.assemble(SOURCE, listing=LISTING)
    where = {name: emulator.label_address(listing, name)
             for name in ("start", "database_ready", "vm_location")}

    out = []
    session = emulator.Session(machine="MSX1")
    try:
        time.sleep(emulator.longer(7.0))        # this one takes its time
        # Put in, and then made sure it took.  A machine still busy coming up
        # keeps the screen, and then every comparison below is between two
        # screenfuls of MSX BASIC saying how many bytes are free -- which is
        # exactly what this test did on its first run in company, and it read
        # as though TEXT had not worked.  The first room is described once
        # its location is set, and drawing its picture takes seconds here.
        image = database.build()
        for attempt in range(2):
            start_playing(session, where, image)
            at = emulator.until(
                lambda: session.read(where["vm_location"], 1)[0],
                lambda seen: seen == 1, timeout=40.0, every=0.2)
            if at == 1:
                break
        else:
            raise AssertionError(
                "the adventure never got going: the machine is still the one "
                "that came up, and nothing below would be about our own"
            )
        time.sleep(emulator.longer(settle + 4.0))
        out.append(picture_area(session))
        for order in orders:
            type_them(session, order + ENTER)
            time.sleep(emulator.longer(settle))
            out.append(picture_area(session))
    finally:
        session.close()
    return out


@needs_tools
def test_a_long_message_keeps_to_its_window_until_text_says_otherwise():
    """A long message three times over, in the window under the picture,
    scrolls inside it and never reaches the picture.  With TEXT the window is
    the whole screen, and it does."""
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
