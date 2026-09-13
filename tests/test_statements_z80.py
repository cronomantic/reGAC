"""More than one order on a line.

The original parts them at a mark of punctuation: typing "XYZY.SUR" at
MegaCorp makes it say it does not know the first word and then walk south.
Each piece is a turn of its own, and the line is only asked for again when it
runs out.

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


def how_long(order, separators=()):
    """Type one line and say how many of the Z80's own seconds it took to
    reach the end of the game, or None if it never did."""
    with open(DATABASE, "wb") as f:
        f.write(Database(adventure(list(separators))).build())
    listing = emulator.assemble(SOURCE, listing=LISTING)
    over = emulator.label_address(listing, "done_flag")
    session = emulator.Session()
    try:
        session.load(SNAPSHOT)
        time.sleep(2.0)
        session.type(order + ENTER)
        session.command("reset-tstates-partial")
        deadline = time.time() + 20.0
        while time.time() < deadline:
            time.sleep(0.05)
            if session.read(over, 1)[0] == 0xFF:
                reply = session.command("get-tstates-partial")
                return int(reply.split("\n")[0].strip()) / SPECTRUM_HZ
        return None
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
def test_a_word_parts_them_when_the_adventure_names_one():
    took = how_long("ESPERA Y SALIR", separators=["Y"])
    wanted = FRAMES / 50
    assert took is not None, "the second order never ran"
    assert wanted * 0.8 < took < wanted * 1.4, (
        f"the word should have parted them, taking about {wanted}s, and it took {took:.2f}s"
    )


@needs_tools
def test_a_word_no_adventure_names_parts_nothing():
    """With no separator named, the same line is one order and means nothing,
    so the game carries on waiting for another."""
    assert how_long("ESPERA Y SALIR") is None


if __name__ == "__main__":
    print("one order:", how_long("SALIR"))
    print("parted by a stop:", how_long("ESPERA.SALIR"))
    print("parted by a word:", how_long("ESPERA Y SALIR", separators=["Y"]))
