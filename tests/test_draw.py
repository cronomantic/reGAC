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
"""DRAW n: a picture in the middle of a turn, a close up of what is looked at.

Not the original's.  What was decided, and what everything here holds every
interpreter to:

- DRAW n draws picture n where the room's goes and the way the room's goes:
  it takes its rows back from the text, and under TEXT nothing is drawn.
- Nothing is kept.  The room's picture comes back when the room is next
  described -- a way out, GOTO, LOOK, DESC -- and costs its drawing, not a
  copy of the screen: on a 464 there is no room for one.
- DRAW 0 is what a room with no picture does: the text has the whole screen.
- It draws in the dark as well, for it is not the room being described.
- It travels only in a build whose adventure has it, -DDRAWS, as DO does; on
  the PC always.
"""

import json
import os
import sys

try:
    import pytest
except ImportError:
    pytest = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from regac.__main__ import uses  # noqa: E402
from regac.binary import Database, Reader  # noqa: E402
from regac.check import problems_of  # noqa: E402
from regac.conds import compile_line  # noqa: E402
from regac.lint import notes_of  # noqa: E402
from regac.srcgen import generate  # noqa: E402
from regac.srcparse import parse  # noqa: E402

VERBS = {"MIRA": 1, "SALIR": 2, "DIBUJA": 3, "VE": 4, "NADA": 5, "TEXTO": 6,
         "APAGA": 7}
LOW = [
    "IF ( VERB 3 ) DRAW 2 WAIT END",            # the close up
    "IF ( VERB 1 ) LOOK WAIT END",              # and the room's again
    "IF ( VERB 4 ) GOTO 2 WAIT END",            # picture 2 as a room shows it
    "IF ( VERB 5 ) DRAW 0 WAIT END",            # no picture: the whole screen
    "IF ( VERB 6 ) TEXT DRAW 1 WAIT END",       # under TEXT, nothing
    "IF ( VERB 7 ) PICT RESE 1 DRAW 1 WAIT END",  # in the dark, drawn
    "IF ( VERB 2 ) EXIT END",                   # and the end, for the PC's
]
PICTURES = {
    "1": [["PAPER", 0], ["INK", 7], ["RECT", 40, 60, 200, 150]],
    "2": [["PAPER", 0], ["INK", 7], ["RECT", 80, 90, 120, 130],
          ["LINE", 0, 50, 255, 170]],
}


def compiled(lines):
    code = []
    for line in lines:
        code += compile_line(line, {})
    return code


def a_small_one():
    """Two rooms, each with its picture, and the orders above."""
    from test_markers_z80 import adventure

    ddb = adventure(rooms={
        "1": {"graphic_id": 1, "exits": [], "desc": "UN CUARTO"},
        "2": {"graphic_id": 2, "exits": [], "desc": "OTRO CUARTO"},
    })
    ddb["verbs"] = dict(VERBS)
    ddb["lpcs"] = compiled(LOW)
    ddb["gfx"] = json.loads(json.dumps(PICTURES))
    return ddb


# -- the language --------------------------------------------------------

SOURCE = """\
.def CARACOLA 20
/CTL
start 1
/VOC
MIRA 1 verb
/MSG
#1
HOLA
/LOC #1 gfx=1
UN CUARTO
/LOW
IF ( VERB 1 ) DRAW CARACOLA MESS 1 WAIT END
/GFX
#1
RECT 40 60 200 150
#20
RECT 80 90 120 130
"""


def test_a_source_draws_a_picture_by_its_name():
    ddb = parse(SOURCE)
    assert ["PUSH", 20] in ddb["lpcs"] and ["DRAW"] in ddb["lpcs"]


def test_it_comes_back_out_of_a_source_the_same():
    ddb = json.loads(json.dumps(parse(SOURCE)))
    again = json.loads(json.dumps(parse(generate(ddb))))
    assert again["lpcs"] == ddb["lpcs"]
    assert "DRAW 20" in generate(ddb)


def test_it_travels_as_opcode_44():
    ddb = a_small_one()
    high, low, _, _ = Reader(Database(ddb).build()).conditions()
    assert ["DRAW"] in low
    assert uses(ddb, ("DRAW",))
    assert not uses(json.loads(json.dumps(ddb)) | {"lpcs": []}, ("DRAW",))


def test_a_draw_of_a_picture_there_is_not_is_said():
    ddb = a_small_one()
    ddb["lpcs"] += compiled(["IF ( VERB 2 ) DRAW 9 END"])
    said = [p.message for p in problems_of(ddb)]
    assert any("DRAW 9" in what and "no picture 9" in what for what in said), said
    assert not any("DRAW 0" in what for what in said), \
        "nought is no picture, as it is for a room"


def test_a_picture_drawn_is_not_unused():
    ddb = a_small_one()
    ddb["gfx"]["3"] = [["RECT", 10, 60, 20, 70]]
    ddb["lpcs"] += compiled(["IF ( VERB 2 ) DRAW 3 END"])
    said = [str(note) for note in notes_of(ddb)]
    assert not any("picture 3" in what for what in said), said
    ddb["lpcs"] = compiled(["IF ( VERB 2 ) DRAW 1 END"])
    ddb["gfx"]["4"] = [["RECT", 10, 60, 20, 70]]
    said = [str(note) for note in notes_of(ddb)]
    assert any("picture 4" in what for what in said), said


# -- the interpreter in Python --------------------------------------------

def python_shows(ddb, orders):
    """What each order asked of the screen: ("draw", n) and ("clear",)."""
    from test_interpreter import interpreter

    shown = []

    class Watched(interpreter()):
        def draw_picture(self, graphic_id):
            shown.append(("draw", graphic_id))

        def clear_picture(self):
            shown.append(("clear",))

    game = Watched(json.loads(json.dumps(ddb)))
    assert game.start_adventure(), "it would not start"
    game.print = lambda *_: None
    out = {}
    typed = iter(orders)
    order = [None]

    def asked():
        if order[0] is not None:
            out[order[0]] = list(shown)
        shown.clear()
        order[0] = next(typed, None)
        return order[0]

    game.input = asked
    while not game.main_loop():
        pass
    return out


def test_on_the_interpreter_in_python():
    said = python_shows(a_small_one(),
                        ["DIBUJA", "MIRA", "NADA", "TEXTO", "APAGA"])
    assert said["DIBUJA"] == [("draw", 2)]
    assert said["MIRA"] == [("draw", 1)], "the room's picture comes back"
    assert said["NADA"] == [("clear",)], "DRAW 0 gives the text the screen"
    assert ("draw", 1) not in said["TEXTO"], "under TEXT nothing is drawn"
    assert said["APAGA"] == [("draw", 1)], "and in the dark it draws"


# -- the Z80's -------------------------------------------------------------

def picture_rows(session, rows):
    """The Spectrum's bitmap, the top `rows` rows of it, in order."""
    bitmap = session.read(0x4000, 6144)
    out = []
    for y in range(rows):
        at = ((y & 0xC0) << 5) | ((y & 7) << 8) | ((y & 0x38) << 2)
        out.append(bytes(bitmap[at:at + 32]))
    return out


def z80_sees(ddb, orders):
    """After the start and after every order: how far up the text may go,
    and the rows above that, on a Spectrum 48 built with DRAW."""
    import emulator
    from test_game_z80 import glyph_table
    from test_markers_z80 import (DATABASE, ENTER, LISTING, SOURCE,
                                  asked_again, got_going)

    database = Database(ddb)
    with open(DATABASE, "wb") as f:
        f.write(database.build())
    emulator.assemble(SOURCE, listing=LISTING, defines=("DRAWS",))
    top = emulator.label_address(LISTING, "text_top")
    glyphs = glyph_table(database)
    session = emulator.Session()
    seen = []
    try:
        got_going(session, glyphs)
        first = session.read(top, 1)[0]
        seen.append((first, picture_rows(session, first * 8)))
        for asked, order in enumerate(orders, start=2):
            session.type(order + ENTER)
            asked_again(session, glyphs, asked)
            seen.append((session.read(top, 1)[0],
                         picture_rows(session, first * 8)))
    finally:
        session.close()
    return seen


def needs_z80(func):
    import emulator

    if pytest is None:
        return func
    return pytest.mark.skipif(not emulator.available(),
                              reason="sjasmplus and ZEsarUX must be in tools/")(func)


@needs_z80
def test_on_the_z80():
    (top, room), (_, close), (_, back), (_, as_a_room), (none, _), \
        (text, _), (dark, in_the_dark) = z80_sees(
            a_small_one(), ["DIBUJA", "MIRA", "VE", "NADA", "TEXTO", "APAGA"])
    assert top > 0, "the room's picture keeps the text under it"
    assert close != room, "DRAW 2 drew nothing"
    assert close == as_a_room, "and not picture 2 the way a room shows it"
    assert back == room, "LOOK did not bring the room's picture back"
    assert none == 0, "DRAW 0 did not give the text the whole screen"
    assert text == 0, "under TEXT, DRAW drew a picture"
    assert dark == top and in_the_dark == room, "in the dark it did not draw"


@needs_z80
def test_an_adventure_without_it_is_built_without_it():
    import emulator
    from test_markers_z80 import DATABASE, LISTING, SOURCE, adventure

    with open(DATABASE, "wb") as f:
        f.write(Database(adventure()).build())
    emulator.assemble(SOURCE, listing=LISTING)
    # the listing keeps what an IFDEF passed over, marked with a ~
    with open(LISTING, encoding="latin-1") as f:
        assembled = [line for line in f if "op_draw" in line and "~" not in line]
    assert not assembled, assembled


# -- the PC's --------------------------------------------------------------

def needs_pc(func):
    import dosbox

    if pytest is None:
        return func
    return pytest.mark.skipif(not dosbox.available(),
                              reason="NASM and DOSBox-X must be there")(func)


@needs_pc
def test_on_the_pc(tmp_path):
    """The screen at the end, after DRAW 2, against picture 2 as the
    reference draws it."""
    import pc_game
    from regac.devices import cga_screen, device_for
    from regac.gfx import Renderer

    ddb = a_small_one()
    pc_game.build(ddb, str(tmp_path))
    _, screen = pc_game.play(str(tmp_path), "DIBUJA" + pc_game.ENTER + "SALIR"
                             + pc_game.ENTER, stop=True)
    assert screen, "the game never got to the end"
    gfx = ddb["gfx"]
    drawn = cga_screen(Renderer(gfx, device_for("cga", gfx, 2, ddb)).run(2))
    picture = [pc_game.pixel(screen, x, y) for y in range(128)
               for x in range(32, 288)]
    reference = [pc_game.pixel(drawn, x, y) for y in range(128)
                 for x in range(32, 288)]
    apart = sum(1 for a, b in zip(picture, reference) if a != b)
    assert apart == 0, f"{apart} points of picture 2 differ"
