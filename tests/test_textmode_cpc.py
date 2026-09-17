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
"""TEXT on an Amstrad, the half that was missing: the window.

What TEXT and PICT do was measured on the original and is told in
test_textmode_z80.py and doc/pendiente.md.  The half that stops the pictures
this machine has had all along; the half that gives the text the whole screen
waited for room, and has it now.  So this is that test again on an Amstrad: a
long message scrolls inside the nine rows under the picture and never reaches
it, until TEXT says the window is the whole screen and then it does; and with
TEXT on, a new room draws no picture.
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
from test_textmode_z80 import a_room_and_a_verb  # noqa: E402

CPC = os.path.join(ROOT, "z80", "cpc")
SOURCE = os.path.join(CPC, "game.asm")
DATABASE = os.path.join(CPC, "game.rgac")
BINARY = os.path.join(CPC, "game.bin")
LISTING = os.path.join(CPC, "game.lst")
LOADS_AT = 0x4000
SCREEN = 0xC000
PICTURE_ROWS = 16               # character rows the picture lives in
LINE_BYTES = 80                 # a character row, along one pixel line
ENTER = chr(13)

if pytest is not None:
    needs_tools = pytest.mark.skipif(
        not emulator.available(), reason="sjasmplus and ZEsarUX must be in tools/"
    )
else:

    def needs_tools(func):
        return func


def picture_area(session):
    """The sixteen character rows at the top, out of the machine's own RAM:
    each of the eight pixel lines of a row is its own two kilobytes."""
    screen = bytes(session.read(SCREEN, 0x4000, zone=session.RAM))
    return b"".join(screen[line * 2048:line * 2048 + PICTURE_ROWS * LINE_BYTES]
                    for line in range(8))


def picture_area_after(orders, settle=6.0):
    """What the picture's rows held after the game started and after each of
    the orders."""
    with open(DATABASE, "wb") as f:
        f.write(Database(a_room_and_a_verb(), machine="cpc").build())
    listing = emulator.assemble(SOURCE, listing=LISTING)
    ready = emulator.label_address(listing, "vm_location")
    with open(BINARY, "rb") as f:
        blob = f.read()

    out = []
    session = emulator.Session(machine="CPC6128")
    try:
        time.sleep(3.0)
        for at in range(0, len(blob), 512):
            session.command(f"write-memory-raw {LOADS_AT + at} "
                            + blob[at:at + 512].hex().upper())
        session.command(f"set-register PC={LOADS_AT:04X}H")
        # the first room is described once the location is set, and its
        # picture takes a moment on this machine
        deadline = time.time() + 30.0
        while time.time() < deadline and session.read(ready, 1)[0] != 1:
            time.sleep(0.2)
        time.sleep(settle + 4.0)
        out.append(picture_area(session))
        for order in orders:
            session.type_keys(order + ENTER)
            time.sleep(settle)
            out.append(picture_area(session))
    finally:
        session.close()
    return out


@needs_tools
def test_a_long_message_keeps_to_its_window_until_text_says_otherwise():
    """A long message three times over, in a nine row window, scrolls inside
    it and never reaches the picture.  With TEXT the window is the whole
    screen, and it does."""
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
    print("TEXT gives the text of an Amstrad the whole screen")
