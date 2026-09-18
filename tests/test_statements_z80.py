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
"""More than one order on a line.

The original parts them at a mark of punctuation: typing "XYZY.SUR" at
MegaCorp makes it say it does not know the first word and then walk south.
It parts them at two words as well, THEN and AND, measured the same way.
Those two live in the original's interpreter; here they live in the
database, which is what the decompiler puts there, so the tests below name
them the way a decompiled adventure does.  Ours knows no word by itself: a
Spanish Y parts nothing unless the adventure says it does, and neither does
THEN.  Each piece is a turn of its own, and the line is only asked for
again when it runs out.

The way to see that both orders ran, without reading the screen, is to make
the first one take time and the second one end the game.  Then the game ends
after about as long as the first order asked for: at once would mean the first
was skipped, and never would mean the second was.
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

WAIT_VERB, QUIT_VERB = 1, 2
FRAMES = 100                                    # the wait, two seconds of it

if pytest is not None:
    needs_tools = pytest.mark.skipif(
        not emulator.available(), reason="sjasmplus and ZEsarUX must be in tools/"
    )
else:

    def needs_tools(func):
        return func


def adventure(separators):
    """One room and two verbs: one that waits, one that stops."""
    rules = [["PUSH", WAIT_VERB], ["VERB"], ["IF"],
             ["PUSH", FRAMES], ["HOLD"], ["WAIT"], ["END"]]
    rules += [["PUSH", QUIT_VERB], ["VERB"], ["IF"], ["EXIT"], ["END"]]
    return {
        "font": [0] * 1024,
        "verbs": {"ESPERA": WAIT_VERB, "SALIR": QUIT_VERB},
        "nouns": {},
        "adverbs": {},
        "pronouns": [],
        "messages": {
            "1": "Y",                           # so the charset has the letter
            "240": ">",
            "241": "NO PUEDES.",
            "242": "COMO DICES?",
            "244": "ESTAS SEGURO?",
            "254": "MUY BIEN.",
        },
        "objects": {"1": {"weight": 1, "initial_loc": 1, "name": "NADA"}},
        "locations": {"1": {"graphic_id": 0, "exits": [], "desc": "UN CUARTO"}},
        "hpcs": [],
        "lpcs": rules,
        "lcs": {},
        "model": "SPECTRUM",
        "punctuation": list("\0 .,-!?:"),
        "separators": separators,
        "init_loc": 1,
        "no_objs_msg": "NADA",
        "gfx": {},
    }


def how_long(order, separators=(), tries=3):
    """Type one line and say how many of the Z80's own seconds it took to
    reach the end of the game, or None if it never did.

    What was typed is read back out of the machine before anything is
    believed about it.  A key held down repeats, as it does on the original,
    so a machine that stalls for a second while this holds one down -- which
    a busy afternoon of the whole suite does -- types that letter twice; the
    verb is then not a verb, the order it was in never runs, and the game
    ends at once.  That looked like a HOLD that did not hold, and the run is
    simply done again."""
    built = Database(adventure(list(separators)))
    chars = built.store.charset.chars
    for attempt in range(tries):
        took, codes = once(built, order)
        # back into letters, and whatever the adventure has no character of
        # its own for is the code itself, which is this machine's ASCII
        typed = "".join(chars.get(code, chr(code)) for code in codes)
        if typed == order:
            return took
    raise AssertionError(
        f"three times over, what reached the interpreter was {typed!r} "
        f"and not {order!r}: the keys did not arrive as they were sent"
    )


def once(built, order):
    """One run: type the order and give back how long it took and the codes
    the interpreter read."""
    with open(DATABASE, "wb") as f:
        f.write(built.build())
    listing = emulator.assemble(SOURCE, listing=LISTING)
    over = emulator.label_address(listing, "done_flag")
    buffer = emulator.label_address(listing, "input_buffer")
    session = emulator.Session()
    try:
        session.load(SNAPSHOT)
        time.sleep(2.0)
        session.type(order + ENTER)
        typed = bytes(session.read(buffer, len(order)))
        session.command("reset-tstates-partial")
        deadline = time.time() + 20.0
        while time.time() < deadline:
            time.sleep(0.05)
            if session.read(over, 1)[0] == 0xFF:
                reply = session.command("get-tstates-partial")
                return int(reply.split("\n")[0].strip()) / SPECTRUM_HZ, typed
        return None, typed
    finally:
        session.close()


@needs_tools
def test_one_order_on_its_own():
    took = how_long("SALIR")
    assert took is not None, "the game never ended"
    assert took < 0.5, f"stopping should be instant, and took {took:.2f}s"


@needs_tools
def test_a_full_stop_parts_two_orders():
    took = how_long("ESPERA.SALIR")
    wanted = FRAMES / 50
    assert took is not None, "the second order never ran"
    assert wanted * 0.8 < took < wanted * 1.4, (
        f"both orders should have run, taking about {wanted}s, and it took {took:.2f}s"
    )


@needs_tools
def test_a_comma_parts_them_and_the_other_marks_do_not():
    """Measured on the original: of the marks its own table of punctuation
    holds, the comma and the full stop part two orders, and the -, the ?
    and the : do not -- those only part words.  COGE-MATA at MegaCorp was
    one order and did what COGE alone does."""
    wanted = FRAMES / 50
    took = how_long("ESPERA,SALIR")
    assert took is not None, "a comma did not part the two orders"
    assert wanted * 0.8 < took < wanted * 1.4, (
        f"both orders should have run, taking about {wanted}s, and it took {took:.2f}s"
    )
    assert how_long("ESPERA-SALIR") is None, "a dash parts no order"
    assert how_long("ESPERA?SALIR") is None, "nor does a question mark"


@needs_tools
def test_a_word_parts_them_when_the_adventure_names_one():
    took = how_long("ESPERA Y SALIR", separators=["Y"])
    wanted = FRAMES / 50
    assert took is not None, "the second order never ran"
    assert wanted * 0.8 < took < wanted * 1.4, (
        f"the word should have parted them, taking about {wanted}s, and it took {took:.2f}s"
    )


ORIGINALS = ["THEN", "AND"]                     # what the decompiler writes


@needs_tools
def test_then_parts_them_as_it_did_in_the_original():
    took = how_long("ESPERA THEN SALIR", separators=ORIGINALS)
    wanted = FRAMES / 50
    assert took is not None, "THEN did not part the two orders"
    assert wanted * 0.8 < took < wanted * 1.4, (
        f"both orders should have run, taking about {wanted}s, and it took {took:.2f}s"
    )


@needs_tools
def test_and_parts_them_too():
    took = how_long("ESPERA AND SALIR", separators=ORIGINALS)
    wanted = FRAMES / 50
    assert took is not None, "AND did not part the two orders"
    assert wanted * 0.8 < took < wanted * 1.4, (
        f"both orders should have run, taking about {wanted}s, and it took {took:.2f}s"
    )


@needs_tools
def test_a_word_that_only_starts_one_parts_nothing():
    """ANDAR is not AND with a tail: the words are matched whole."""
    assert how_long("ESPERA ANDAR SALIR", separators=ORIGINALS) is None


@needs_tools
def test_the_interpreter_names_none_by_itself():
    """THEN is the original interpreter's word, not ours.  An adventure that
    does not ask for it does not get it, which is the whole point of the words
    living in the database."""
    assert how_long("ESPERA THEN SALIR") is None


@needs_tools
def test_a_word_no_adventure_names_parts_nothing():
    """With no separator named, the same line is one order and means nothing,
    so the game carries on waiting for another.  The original does the same:
    XYZZY Y SUR walks south without complaining, exactly as XYZZY SUR does."""
    assert how_long("ESPERA Y SALIR") is None


if __name__ == "__main__":
    print("one order:", how_long("SALIR"))
    print("parted by a stop:", how_long("ESPERA.SALIR"))
    print("parted by a word:", how_long("ESPERA Y SALIR", separators=["Y"]))
