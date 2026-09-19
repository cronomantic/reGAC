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
"""TEXT on a PCW, the half that was missing: the window.

What TEXT and PICT do was measured on the original and is told in
test_textmode_z80.py and doc/pendiente.md.  The half that stops the pictures
this machine has had all along; the half that gives the text the whole screen
waited because the two halves of this screen are in different banks.  So this
is that test again on a PCW: a long message scrolls inside the sixteen rows
under the picture and never reaches it, until TEXT says the window is the
whole screen and then it does; and with TEXT on, a new room draws no picture.

The window is sixteen rows of sixty four here, so the message is longer than
on the others, to be sure of running off the top.
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
from regac.binary import Database  # noqa: E402
from regac.media import PCW_HALF, banks_of, pcw_release  # noqa: E402
from test_keyboard_pcw import type_them  # noqa: E402
from test_text_pcw import ROW_BYTES, WINDOW_ROWS, decode_screen, glyph_table  # noqa: E402
from test_textmode_z80 import a_room_and_a_verb  # noqa: E402

PCW = os.path.join(ROOT, "z80", "pcw")
SOURCE = os.path.join(PCW, "game.asm")
DATABASE = os.path.join(PCW, "game.rgac")
BINARY = os.path.join(PCW, "game_code.bin")
LISTING = os.path.join(PCW, "game.lst")
BOOT = os.path.join(PCW, "boot.asm")
DEFS = os.path.join(PCW, "banks.inc")

SCREEN = 0x8000
SCREEN_SLOT = 0xF2              # the port that says which half the map shows
BANK_MARK = 0x80
PICTURE_BANK = 2
TEXT_BANK = 4
ENTER = chr(13)
WITH_PICT = 5                   # a verb the Spectrum's adventure does not use
PICTURE_MARGIN_NARROW = 29      # columns each side of a picture a point wide
PICTURE_COLS_NARROW = 32

if pytest is not None:
    needs_tools = pytest.mark.skipif(
        not emulator.available(), reason="sjasmplus and ZEsarUX must be in tools/"
    )
else:

    def needs_tools(func):
        return func


def the_adventure():
    """The Spectrum's, with a message long enough that the three of them
    fill a window of sixteen rows of sixty four twice over."""
    ddb = a_room_and_a_verb()
    ddb["messages"]["1"] = ("UN CUARTO MUY LARGO DE DESCRIBIR " * 22)[:700]
    # and PICT, with a walk behind it so that a picture is drawn again
    ddb["lpcs"] += [["PUSH", WITH_PICT], ["VERB"], ["IF"], ["PICT"],
                    ["PUSH", 2], ["GOTO"], ["END"]]
    ddb["verbs"]["LAMINA"] = WITH_PICT
    return ddb


def build(folder, scale=2):
    adventure = os.path.join(folder, "textmode.json")
    with open(adventure, "w", encoding="utf-8") as f:
        json.dump(the_adventure(), f)
    subprocess.run(
        [sys.executable, "-m", "regac", "build", adventure, DATABASE,
         "-m", "pcw", "-b", "16k", "--defs", DEFS],
        cwd=ROOT, check=True, capture_output=True,
    )
    emulator.assemble(BOOT, listing=os.path.join(PCW, "boot.lst"))
    emulator.assemble(SOURCE, listing=LISTING,
                      defines=[f"PICTURE_SCALE={scale}"])
    with open(os.path.join(PCW, "boot.bin"), "rb") as f:
        boot = f.read()
    with open(BINARY, "rb") as f:
        code = f.read()
    with open(DATABASE, "rb") as f:
        banks = banks_of(f.read())
    path = os.path.join(folder, "textmode.dsk")
    with open(path, "wb") as f:
        f.write(pcw_release(boot, code, banks))
    return path


def picture_half(session):
    """The half of the screen the picture is in, which is not the half in the
    map while there is text to print: it is brought in with the machine held,
    read, and the text's half put back."""
    with session.held():
        session.command(f"write-port {SCREEN_SLOT} {BANK_MARK | PICTURE_BANK}")
        half = bytes(session.read(SCREEN, PCW_HALF))
        session.command(f"write-port {SCREEN_SLOT} {BANK_MARK | TEXT_BANK}")
    # A key sent straight after a long read with the machine held is lost:
    # tried order by order, it is the read that does it and not the stop or
    # the ports, and half a second of the machine running cures it.  The first
    # letter of every order went, which made every order a word nobody knew.
    time.sleep(0.5)
    return half


def waited_for_the_prompt(session, glyphs, timeout=90.0):
    """Until the last line written is the prompt and nothing after it.

    A key pressed before the machine is asking is a key lost, and the order
    it began is then a word nobody knows: a fixed wait was sometimes that."""
    deadline = time.time() + emulator.longer(timeout)
    while time.time() < deadline:
        # a blank cell is paper, which is no glyph, so it reads as a "?"
        lines = [line.rstrip("?") for line in decode_screen(
            session.read(SCREEN, WINDOW_ROWS * ROW_BYTES), glyphs)]
        lines = [line for line in lines if line]
        if lines and lines[-1] == ">":
            return
        time.sleep(1.0)
    raise AssertionError(f"the machine never asked for an order: {lines}")


def picture_half_after(orders, scale=2):
    """What the picture's half held after the game started and after each of
    the orders."""
    glyphs = glyph_table(Database(the_adventure(), machine="pcw"))
    out = []
    with tempfile.TemporaryDirectory() as folder:
        path = build(folder, scale)
        session = emulator.Session(
            machine="PCW8256", extra=["--enable-dsk", "--dsk-file", path]
        )
        try:
            waited_for_the_prompt(session, glyphs)
            out.append(picture_half(session))
            for order in orders:
                type_them(session, order + ENTER)
                time.sleep(2.0)         # for the prompt that is up to go
                waited_for_the_prompt(session, glyphs)
                out.append(picture_half(session))
        finally:
            session.close()
    return out


@needs_tools
def test_a_long_message_keeps_to_its_window_until_text_says_otherwise():
    """A long message over and over, in a sixteen row window, scrolls inside
    it and never reaches the picture.  With TEXT the window is the whole
    screen, and it does."""
    drawn, after_plain, after_text = picture_half_after(["LARGO", "TEXTO"])
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
    with_pictures = picture_half_after(["ANDA"])[-1]
    with_text = picture_half_after(["CALLA"])[-1]
    assert with_pictures != with_text, (
        "the room drew its picture although TEXT had asked for none"
    )


@needs_tools
def test_a_narrow_picture_leaves_nothing_of_the_text_beside_it():
    """A picture drawn a point wide is half as wide as the text.  What TEXT
    scrolled up into its half is beside it as well as under it, and the next
    picture has to take all of it away, not only the part it covers."""
    def beside(half):
        columns = (list(range(PICTURE_MARGIN_NARROW))
                   + list(range(PICTURE_MARGIN_NARROW + PICTURE_COLS_NARROW, 90)))
        return sum(1 for row in range(16) for column in columns
                   for line in range(8) if half[row * ROW_BYTES + 8 * column + line])

    scrolled, drawn = picture_half_after(["TEXTO", "LAMINA"], scale=1)[1:]
    assert beside(scrolled), "TEXT did not bring the text up beside the picture"
    assert not beside(drawn), (
        "the picture was drawn with the text still to either side of it"
    )


if __name__ == "__main__":
    test_a_long_message_keeps_to_its_window_until_text_says_otherwise()
    test_with_text_on_a_room_draws_no_picture()
    test_a_narrow_picture_leaves_nothing_of_the_text_beside_it()
    print("TEXT gives the text of a PCW the whole screen")
