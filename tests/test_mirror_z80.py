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
ADVENTURE = os.path.join(ROOT, "snapshots", "megacorp2.json")
THEIRS = os.path.join(ROOT, "snapshots", "megacorp2.sna")
OURS = os.path.join(SPECTRUM, "game.sna")
ENTER = chr(13)
PROMPT = ">>>"
THEIR_PORT = emulator.PORT + 100        # its own machine, clear of the rest

# Its own code, which is in its own vocabulary: room 5000 takes verb 29, and
# verb 29 of MegaCorp is REBECA.
WALK = [
    "REBECA",
    "MIRAR", "N", "E", "S", "O",                # walking, and a wall or two
    "COGE DISCO", "COGE DISCO", "DEJA DISCO",   # having, having twice, losing
    "COGE PISTOLA", "COGE JARRO",               # what is not here
    "INVENTARIO", "DETALLA DISCO",
    "XYZZY", "DISCO", "ABRE PUERTA", "CANTA",   # what it cannot do or parse
    "N", "N", "E", "COGE ESCOBA", "INVENTARIO",
    "SUBE", "BAJA", "MIRAR",
]

if pytest is not None:
    needs_them = pytest.mark.skipif(
        not emulator.available() or not os.path.exists(THEIRS)
        or not os.path.exists(ADVENTURE),
        reason="sjasmplus and ZEsarUX must be in tools/, with the original's "
               "snapshot and the same adventure decompiled",
    )
else:

    def needs_them(func):
        return func


def said(lines):
    """What is on the window, without the blank rows."""
    return [line for line in lines if line.strip()]


def lined_up(mine, yours):
    """The two windows at the bottom, where the turn just played is."""
    a, b = said(mine), said(yours)
    keep = min(len(a), len(b))
    return a[len(a) - keep:], b[len(b) - keep:]


def settled(session, glyphs, timeout=40.0):
    """The window once the turn is over and it is asking again."""
    deadline = time.time() + emulator.longer(timeout)
    last = None
    while time.time() < deadline:
        now = screen(session, glyphs)
        written = said(now)
        if written and written[-1].rstrip() == PROMPT and now == last:
            return now
        last = now
        time.sleep(0.4)
    return last or []


def play(session, glyphs, order, other):
    """Type the order into one machine, with the other held, and give back
    the window once the turn has been played."""
    other.command("enter-cpu-step")
    try:
        session.type(order, hold_for=0.2)
        now = screen(session, glyphs)
        assert any(order in line for line in now), (
            f"{order!r} never reached the keyboard: {said(now)}"
        )
        session.type(ENTER, hold_for=0.2)
        return settled(session, glyphs)
    finally:
        other.command("exit-cpu-step")


def build_ours():
    with open(ADVENTURE, encoding="utf-8") as f:
        ddb = json.load(f)
    subprocess.run(
        [sys.executable, "-m", "regac", "build", ADVENTURE,
         os.path.join(SPECTRUM, "game.rgac"), "-m", "spectrum48"],
        cwd=ROOT, check=True, capture_output=True,
    )
    emulator.assemble(os.path.join(SPECTRUM, "game.asm"),
                      listing=os.path.join(SPECTRUM, "game.lst"))
    return ddb


@needs_them
def test_it_plays_the_adventure_as_the_original_does():
    ddb = build_ours()
    glyphs = glyph_table(Database(ddb))
    ours = emulator.Session()
    theirs = emulator.Session(port=THEIR_PORT)
    try:
        ours.load(OURS)
        theirs.load(THEIRS)
        mine, yours = settled(ours, glyphs, 60.0), settled(theirs, glyphs, 60.0)
        a, b = lined_up(mine, yours)
        assert a == b, f"they open differently:\n  ours  {a}\n  theirs {b}"
        for turn, order in enumerate(WALK, start=1):
            mine = play(ours, glyphs, order, other=theirs)
            yours = play(theirs, glyphs, order, other=ours)
            a, b = lined_up(mine, yours)
            assert a == b, (
                f"turn {turn}, {order!r}, they part company:\n"
                + "\n".join(f"  {'>>' if x != y else '  '} ours  |{x}\n"
                            f"  {'>>' if x != y else '  '} theirs |{y}"
                            for x, y in zip(a, b))
            )
    finally:
        ours.close()
        theirs.close()


if __name__ == "__main__":
    test_it_plays_the_adventure_as_the_original_does()
    print("it plays the adventure as the original does")
