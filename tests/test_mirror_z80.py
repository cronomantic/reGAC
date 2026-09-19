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
"""The same adventure played twice at once: the original's and ours.

Every difference found until now turned up because somebody tripped over it
-- SWAP that did not swap, WAIT that did not cut the table, CARR and AVAIL
the wrong way round.  This one goes looking: MegaCorp on the original
interpreter and MegaCorp decompiled and built with ours, side by side in two
emulators, the same orders typed into both, and the text window read after
every turn with the adventure's own font.  They share a screen and a font, so
one reader does for both.

It found the wrapping on its first proper walk: a word that ends exactly at
the last column goes on the next line in the original, and this kept it.  Its
street in Nyhmir says "Paseantes de varias razas" and the razas is what gave
it away.

Three things about the harness, each of which cost a run to learn:

  - **The machines take turns.**  Two emulators at once make a busy host, a
    busy host drops letters, and a dropped letter is a different order rather
    than a difference between the interpreters.  While one is being typed at
    the other is held.
  - **A still screen does not mean the turn is over.**  While a room's
    picture is drawn -- seconds of it -- the window sits there with the order
    still echoed.  What says the turn is done is the last line being the
    prompt with nothing typed after it.
  - **The echo is looked at before the line is sent**, because once the turn
    runs a description lands on top of that very line: their DESC goes back
    to the left of it and writes over.

The two windows are lined up at the bottom.  Where a line falls inside the
window is the machine's history and not the interpreter's doing: the
original's snapshot was taken with its title already scrolled past.
"""

import json
import os
import subprocess
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
from test_game_z80 import glyph_table, screen  # noqa: E402

SPECTRUM = os.path.join(ROOT, "z80", "spectrum")
SNAPSHOTS = os.path.join(ROOT, "snapshots")
OURS = os.path.join(SPECTRUM, "game.sna")
ENTER = chr(13)
SCREEN_COLS = 32
THEIR_PORT = emulator.PORT + 100        # its own machine, clear of the rest

# One walk for each adventure we have both halves of: its own snapshot and
# its own decompiled database.  The orders are its own vocabulary, so each
# walk belongs to its adventure -- and each covers the same ground: walking
# and walls, having and not having, what it cannot do and what it cannot
# parse, and whatever that adventure has of its own.
WALKS = {
    # Its own code first: room 5000 takes verb 29, which is REBECA.
    "megacorp2": [
        "REBECA",
        "MIRAR", "N", "E", "S", "O",                # walking, and a wall or two
        "COGE DISCO", "COGE DISCO", "DEJA DISCO",   # having, twice, losing
        "COGE PISTOLA", "COGE JARRO",               # what is not here
        "INVENTARIO", "DETALLA DISCO",
        "XYZZY", "DISCO", "ABRE PUERTA", "CANTA",   # what it cannot do or parse
        "N", "N", "E", "COGE ESCOBA", "INVENTARIO",
        "SUBE", "BAJA", "MIRAR",
        "N", "O", "S", "E", "MIRAR",                # four more rooms
        "COGE TODO", "DEJA ESCOBA", "INVENTARIO",
    ],
    # No code, but a title to get past, and the only one of the four with
    # pronouns: LO and ESO, which is what a two noun order is for here.
    "Bangkok2": [
        "REDESCRIBIR", "INVENTARIO",
        "NORTE", "SUR", "ESTE", "OESTE",
        "COGER AGUA", "COGER AGUA BAR", "COGER LO", "COGER ESO",
        "REBUSCAR", "TIRAR AGUA",
        "XYZZY", "AGUA", "ENTRAR",
        "SUBIR", "BAJATE", "REDESCRIBIR",
    ],
}

def both_halves(name):
    """The original's own snapshot and the same adventure decompiled."""
    return (os.path.join(SNAPSHOTS, name + ".sna"),
            os.path.join(SNAPSHOTS, name + ".json"))


if pytest is not None:
    needs_them = pytest.mark.skipif(
        not emulator.available()
        or not all(os.path.exists(half)
                   for name in WALKS for half in both_halves(name)),
        reason="sjasmplus and ZEsarUX must be in tools/, with the originals' "
               "snapshots and the same adventures decompiled",
    )
    adventures = pytest.mark.parametrize("name,walk", sorted(WALKS.items()))
else:

    def needs_them(func):
        return func

    def adventures(func):
        return func


def said(lines):
    """What is on the window, without the blank rows."""
    return [line for line in lines if line.strip()]


def lined_up(mine, yours):
    """The two windows at the bottom, where the turn just played is."""
    a, b = said(mine), said(yours)
    keep = min(len(a), len(b))
    return a[len(a) - keep:], b[len(b) - keep:]


def settled(session, glyphs, prompt, timeout=40.0):
    """The window once the turn is over and it is asking again.

    The prompt is the adventure's own message 240, which is not the same in
    all of them: MegaCorp asks with ">>>" and Los pajaros de Bangkok with a
    space in front of it, which is why the line is stripped at both ends
    before it is compared.  Getting that wrong does not fail anything -- it
    makes every turn wait out its whole timeout, and the walk takes half an
    hour instead of five minutes.
    """
    deadline = time.time() + emulator.longer(timeout)
    last = None
    while time.time() < deadline:
        now = screen(session, glyphs)
        written = said(now)
        if written and written[-1].strip() == prompt and now == last:
            return now
        last = now
        time.sleep(0.4)
    return last or []


# Where the ROM keeps its own flags, and the bit that says caps lock.  What
# the original echoes is in the case the ROM hands it, so its snapshots do not
# agree with each other: MegaCorp's and Las vajillas' were taken with caps
# lock on and Bangkok's and the Quijote's with it off.  That is the state of
# the machine and not the interpreter's doing -- ours has no such thing and
# reads its keys as capitals -- so it is levelled here, like everything else
# that belongs to the machine rather than to the adventure.
FLAGS2 = 0x5C6A
CAPS_LOCK = 0x08


def caps_lock_on(session):
    flags = bytes(session.read(FLAGS2, 1))[0]
    session.command(f"write-memory {FLAGS2} {flags | CAPS_LOCK}")


def get_going(session, glyphs, prompt, keys=8):
    """Past whatever an adventure puts up before it will take an order.

    Bangkok has a title and a page of story, each waiting for a key; MegaCorp
    asks for its code, which is an order like any other and belongs in the
    walk.  Pressing enter until it asks does for both.
    """
    for _ in range(keys):
        now = settled(session, glyphs, prompt, timeout=6.0)
        if said(now) and said(now)[-1].strip() == prompt:
            return now
        session.type(ENTER, hold_for=0.2)
    return settled(session, glyphs, prompt, timeout=40.0)


def rubbed_out(session, how_many, held=0.15):
    """Take that many letters back, which is caps shift and nought."""
    for _ in range(how_many):
        session.hold_both(session.CAPS_SHIFT, session.KEY_MATRIX["0"])
        time.sleep(held)
        session.hold()
        time.sleep(held)


def typed_whole(session, glyphs, order, prompt, tries=3):
    """The order on the machine's own line, letter for letter.

    A busy host drops letters now and then.  While the line is still being
    written nothing has happened yet, so a line that came out wrong is rubbed
    out and typed again -- which is what keeps the two machines in step,
    where typing it a second time after sending it would not.

    The line has to be the prompt and the order and nothing else.  Asking
    only whether the order is somewhere in it lets a stray letter through:
    ISUBIR holds SUBIR.
    """
    wanted = (prompt + order).casefold()
    for attempt in range(tries):
        session.type(order, hold_for=0.2)
        time.sleep(emulator.longer(0.6))        # let the machine catch up
        written = said(screen(session, glyphs))
        if written and written[-1].strip().casefold() == wanted:
            return
        rubbed_out(session, SCREEN_COLS)        # the whole line, and start again
        time.sleep(emulator.longer(0.4))
    raise AssertionError(f"{order!r} never reached the keyboard whole: "
                         f"{said(screen(session, glyphs))}")


def play(session, glyphs, order, prompt, other):
    """Type the order into one machine, with the other held, and give back
    the window once the turn has been played."""
    other.command("enter-cpu-step")
    try:
        typed_whole(session, glyphs, order, prompt)
        session.type(ENTER, hold_for=0.2)
        return settled(session, glyphs, prompt)
    finally:
        other.command("exit-cpu-step")


def build_ours(where):
    with open(where, encoding="utf-8") as f:
        ddb = json.load(f)
    subprocess.run(
        [sys.executable, "-m", "regac", "build", where,
         os.path.join(SPECTRUM, "game.rgac"), "-m", "spectrum48"],
        cwd=ROOT, check=True, capture_output=True,
    )
    emulator.assemble(os.path.join(SPECTRUM, "game.asm"),
                      listing=os.path.join(SPECTRUM, "game.lst"))
    return ddb


@needs_them
@adventures
def test_it_plays_the_adventure_as_the_original_does(name, walk):
    theirs_snapshot, decompiled = both_halves(name)
    ddb = build_ours(decompiled)
    glyphs = glyph_table(Database(ddb))
    prompt = ddb["messages"]["240"].strip()
    ours = emulator.Session()
    theirs = emulator.Session(port=THEIR_PORT)
    try:
        ours.load(OURS)
        theirs.load(theirs_snapshot)
        caps_lock_on(theirs)
        mine = get_going(ours, glyphs, prompt)
        yours = get_going(theirs, glyphs, prompt)
        a, b = lined_up(mine, yours)
        assert a == b, f"{name} opens differently:\n  ours  {a}\n  theirs {b}"
        for turn, order in enumerate(walk, start=1):
            mine = play(ours, glyphs, order, prompt, other=theirs)
            yours = play(theirs, glyphs, order, prompt, other=ours)
            a, b = lined_up(mine, yours)
            assert a == b, (
                f"{name}, turn {turn}, {order!r}, they part company:\n"
                + "\n".join(f"  {'>>' if x != y else '  '} ours  |{x}\n"
                            f"  {'>>' if x != y else '  '} theirs |{y}"
                            for x, y in zip(a, b))
            )
    finally:
        ours.close()
        theirs.close()


if __name__ == "__main__":
    for one, its_walk in sorted(WALKS.items()):
        test_it_plays_the_adventure_as_the_original_does(one, its_walk)
        print(f"{one}: it plays as the original does")
