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
"""The four conditions that needed the world around them: holding, asking
before quitting, and the tape.

They are the ones that could not be written until there was a keyboard, a
screen and a turn to hang them off.  Each is checked on a real Z80 through a
small adventure written for the purpose, one verb per thing being tested.

Saving and loading are not here.  They hand a block to the ROM's own tape
routines, and this harness cannot record what goes out or play anything back,
so what there is to check about them is checked by eye and by the size of the
block they cover.
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

SPECTRUM = os.path.join(ROOT, "z80", "spectrum")
SOURCE = os.path.join(SPECTRUM, "game.asm")
DATABASE = os.path.join(SPECTRUM, "game.rgac")
SNAPSHOT = os.path.join(SPECTRUM, "game.sna")
LISTING = os.path.join(SPECTRUM, "game.lst")
SPECTRUM_HZ = 3_500_000
ENTER = chr(13)

# what the three verbs of the test adventure do
QUIT_VERB, SHORT_HOLD, LONG_HOLD = 1, 2, 3
SHORT_FRAMES, LONG_FRAMES = 100, 250       # two seconds and five

if pytest is not None:
    needs_tools = pytest.mark.skipif(
        not emulator.available(), reason="sjasmplus and ZEsarUX must be in tools/"
    )
else:

    def needs_tools(func):
        return func


def adventure():
    """One room, three verbs, and a rule for each of them."""
    messages = {
        "1": "SI NO",                           # so the charset has the letters
        "240": ">",
        "241": "NO PUEDES.",
        "242": "COMO DICES?",
        "244": "ESTAS SEGURO?",
        "246": "NO LO TIENES.",
        "247": "NO LO VEO.",
        "248": "LLEVAS DEMASIADO.",
        "254": "MUY BIEN.",
    }
    rules = []
    rules += [["PUSH", QUIT_VERB], ["VERB"], ["IF"], ["QUIT"], ["END"]]
    rules += [["PUSH", SHORT_HOLD], ["VERB"], ["IF"],
              ["PUSH", SHORT_FRAMES], ["HOLD"], ["EXIT"], ["END"]]
    rules += [["PUSH", LONG_HOLD], ["VERB"], ["IF"],
              ["PUSH", LONG_FRAMES], ["HOLD"], ["EXIT"], ["END"]]
    return {
        "font": [0] * 1024,
        "verbs": {"SALIR": QUIT_VERB, "ESPERA": SHORT_HOLD, "AGUARDA": LONG_HOLD},
        "nouns": {},
        "adverbs": {},
        "pronouns": [],
        "messages": messages,
        "objects": {"1": {"weight": 1, "initial_loc": 1, "name": "NADA"}},
        "locations": {"1": {"graphic_id": 0, "exits": [], "desc": "UN CUARTO"}},
        "hpcs": [],
        "lpcs": rules,
        "lcs": {},
        "model": "SPECTRUM",
        "punctuation": list("\0 .,-!?:"),
        "separators": ["then"],
        "init_loc": 1,
        "no_objs_msg": "NADA",
        "gfx": {},
    }


def playing():
    """Build the little adventure, start it, and wait for its first prompt."""
    with open(DATABASE, "wb") as f:
        f.write(Database(adventure()).build())
    listing = emulator.assemble(SOURCE, listing=LISTING)
    over = emulator.label_address(listing, "done_flag")
    session = emulator.Session()
    session.load(SNAPSHOT)
    time.sleep(emulator.longer(2.0))
    return session, over


def seconds_until_over(session, over, limit=20.0):
    """How long the Z80 itself took to reach the end, in its own seconds.
    Nothing is measured on the wall clock: this emulator does not run at the
    speed of a Spectrum."""
    session.command("reset-tstates-partial")
    deadline = time.time() + limit
    while time.time() < deadline:
        time.sleep(0.05)
        if session.read(over, 1)[0] == 0xFF:
            reply = session.command("get-tstates-partial")
            return int(reply.split("\n")[0].strip()) / SPECTRUM_HZ
    return None


@needs_tools
def test_quit_asks_before_it_goes():
    session, over = playing()
    try:
        session.type("SALIR" + ENTER)
        time.sleep(emulator.longer(1.5))
        assert session.read(over, 1)[0] != 0xFF, "it went without asking"

        session.type("NO" + ENTER)
        time.sleep(emulator.longer(1.5))
        assert session.read(over, 1)[0] != 0xFF, "no should have kept it going"

        session.type("SALIR" + ENTER)
        time.sleep(emulator.longer(1.5))
        session.type("SI" + ENTER)
        time.sleep(emulator.longer(2.0))
        assert session.read(over, 1)[0] == 0xFF, "yes should have ended it"
    finally:
        session.close()


@needs_tools
def test_hold_waits_about_as_long_as_it_is_told():
    session, over = playing()
    try:
        session.type("ESPERA" + ENTER)
        took = seconds_until_over(session, over)
    finally:
        session.close()
    wanted = SHORT_FRAMES / 50
    assert took is not None, "the hold never ended"
    assert wanted * 0.85 < took < wanted * 1.25, (
        f"asked to hold {wanted}s and held {took:.2f}s"
    )


@needs_tools
def test_a_key_cuts_a_hold_short():
    session, over = playing()
    try:
        session.type("AGUARDA" + ENTER)
        session.command("reset-tstates-partial")
        time.sleep(0.6)
        session.hold(*session.KEY_MATRIX["A"])
        time.sleep(0.2)
        session.hold()
        deadline = time.time() + 20.0
        took = None
        while time.time() < deadline:
            time.sleep(0.05)
            if session.read(over, 1)[0] == 0xFF:
                reply = session.command("get-tstates-partial")
                took = int(reply.split("\n")[0].strip()) / SPECTRUM_HZ
                break
    finally:
        session.close()
    assert took is not None, "the hold never ended"
    assert took < LONG_FRAMES / 50 * 0.7, (
        f"the key should have cut it short, but it held {took:.2f}s"
    )


if __name__ == "__main__":
    test_quit_asks_before_it_goes()
    print("quit asks first")
    test_hold_waits_about_as_long_as_it_is_told()
    print("hold holds")
    test_a_key_cuts_a_hold_short()
    print("a key cuts it short")
