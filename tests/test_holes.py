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
r"""Holes in the text: \ctr n, \obj n and \turns, filled in as it is printed.

Not the original's.  What was decided: the three of them, in every text a
change of ink may go in -- messages, rooms and the names of objects -- save
that a name may not hold a name, which could be its own.  A hole is text: it
is part of the word it stands in, so `(\ctr 5)` is one word and `\obj 1.`
keeps its full stop, and the spaces after it are kept.

The same small adventure is played on the interpreter in Python, the Z80's
and the PC's, and has to say the same on all three.
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

from regac.binary import BuildError, Database  # noqa: E402
from regac.check import problems_of  # noqa: E402
from regac.conds import compile_line  # noqa: E402
from regac.text import (INK_CHAR, expand, filled, plain,  # noqa: E402
                        written)
from test_proc import needs_pc, needs_z80, turn_said  # noqa: E402

VERBS = {"MIRA": 1, "SALIR": 2, "CUENTA": 3, "COGE": 4, "TURNOS": 5,
         "JUNTO": 6}
LOW = [
    "IF ( VERB 3 ) 42 CSET 5 MESS 1 END",
    "IF ( VERB 4 ) 7 CSET 6 MESS 2 END",
    "IF ( VERB 5 ) 1 CSET 127 3 CSET 126 MESS 3 END",
    "IF ( VERB 6 ) MESS 4 END",
]
SAYS = {
    "1": r"LLEVAS \ctr 5 PUNTOS.",
    "2": r"COGES \obj 1.",
    "3": r"VAS POR \turns.",
    "4": r"(\ctr 5)\ink 2 ROJO",
}
OBJECTS = {"1": {"weight": 1, "initial_loc": 0, "name": r"MONEDA DE \ctr 6"}}
ROOM = r"UN CUARTO CON \ctr 5 PUERTAS"

# What each order has to leave on the screen; the room is described first,
# with nothing yet in counter five.
WANTED = {
    "CUENTA": "LLEVAS 42 PUNTOS.",
    "COGE": "COGES MONEDA DE 7.",
    "TURNOS": "VAS POR 259.",
    "JUNTO": "(42)ROJO",
}


def a_small_one():
    from test_markers_z80 import adventure

    ddb = adventure(objects=json.loads(json.dumps(OBJECTS)), rooms={
        "1": {"graphic_id": 0, "exits": [], "desc": ROOM}})
    ddb["verbs"] = dict(VERBS)
    ddb["messages"].update(SAYS)
    code = []
    for line in LOW:
        code += compile_line(line, {})
    ddb["lpcs"] = code
    return ddb


# -- the language --------------------------------------------------------

def test_they_travel_behind_the_code_an_ink_does():
    codes = expand(r"A \ctr 5 B \obj 12. \turns C")
    assert codes == f"A {INK_CHAR}C05 B {INK_CHAR}O0<. {INK_CHAR}T C"


def test_they_are_written_back_as_they_were_written():
    for text in (r"LLEVAS \ctr 5 PUNTOS.", r"COGES \obj 1.", r"VAS POR \turns.",
                 r"(\ctr 127)\ink 2 ROJO"):
        assert expand(written(expand(text))) == expand(text)


def test_the_spaces_after_a_hole_are_kept_and_after_an_ink_eaten():
    assert plain(expand(r"A \ctr 5 B")) == "A  B"
    assert plain(expand(r"A \ink 5 B")) == "A B"


def test_what_they_are_filled_with():
    counters = {5: 42, 6: 7, 126: 3, 127: 1}
    names = {1: r"MONEDA DE \ctr 6"}
    text = filled(expand(r"\ctr 5, \obj 1, \turns"), counters.get, names.get)
    assert text == "42, MONEDA DE 7, 259"


def test_a_hole_there_cannot_be_is_refused():
    for text in (r"\ctr 128", r"\obj 0", r"\obj 256"):
        try:
            expand(text)
        except ValueError:
            continue
        raise AssertionError(f"{text} went through")


def test_a_name_may_not_hold_a_name():
    ddb = a_small_one()
    ddb["objects"]["1"]["name"] = r"LA DE \obj 1"
    said = [str(p) for p in problems_of(ddb)]
    assert any("may not name one" in one for one in said), said
    try:
        Database(ddb).build()
    except BuildError:
        return
    raise AssertionError("a name that names itself was built")


def test_a_name_that_is_not_there_is_said():
    ddb = a_small_one()
    ddb["messages"]["5"] = r"\obj 9"
    said = [str(p) for p in problems_of(ddb)]
    assert any("no object 9" in one for one in said), said


# -- the interpreter in Python --------------------------------------------

def test_on_the_interpreter_in_python():
    from test_interpreter import interpreter

    game = interpreter()(json.loads(json.dumps(a_small_one())))
    assert game.start_adventure()
    out = []
    game.print = lambda text: out.append(game.shown(text))
    orders = iter(list(WANTED))
    game.input = lambda: next(orders, None)
    while not game.main_loop():
        pass
    said = plain("".join(out)).replace("\n", "")
    assert "UN CUARTO CON 0 PUERTAS" in said, said
    for wanted in WANTED.values():
        assert wanted in said, f"{wanted!r} is not in {said!r}"


# -- the Z80's and the PC's -----------------------------------------------

def z80_says(ddb, orders):
    import emulator
    from test_game_z80 import glyph_table
    from test_markers_z80 import (DATABASE, ENTER, LISTING, SOURCE,
                                  asked_again, got_going)

    database = Database(ddb)
    with open(DATABASE, "wb") as f:
        f.write(database.build())
    emulator.assemble(SOURCE, listing=LISTING, defines=("HOLES",))
    glyphs = glyph_table(database)
    said = {}
    session = emulator.Session()
    try:
        first = got_going(session, glyphs)
        said[""] = "".join(line.replace("?", " ").strip() for line in first)
        for asked, order in enumerate(orders, start=2):
            session.type(order + ENTER)
            said[order] = turn_said(asked_again(session, glyphs, asked), order)
    finally:
        session.close()
    return said


@needs_z80
def test_on_the_z80():
    said = z80_says(a_small_one(), list(WANTED))
    assert "UN CUARTO CON 0 PUERTAS" in said[""], said[""]
    for order, wanted in WANTED.items():
        assert wanted in said[order], f"{order}: {said[order]!r}"


@needs_pc
def test_on_the_pc(tmp_path):
    import pc_game

    folder = str(tmp_path)
    pc_game.build(a_small_one(), folder)
    printed, _ = pc_game.play(folder, "".join(o + chr(13) for o in WANTED),
                              stop=True)
    lines = printed.replace(chr(13), "").split(chr(10))
    assert "UN CUARTO CON 0 PUERTAS" in "".join(lines), printed
    for order, wanted in WANTED.items():
        said = turn_said(lines, order)
        assert wanted in said, f"{order}: {said!r}"


# -- a hole is part of its word -----------------------------------------------

def breaking():
    """An adventure whose message puts "(42)" where it does not fit: twenty
    eight letters, a space, and the hole in brackets from column twenty
    nine, four characters where three are left."""
    ddb = a_small_one()
    ddb["verbs"]["CORTA"] = 7
    ddb["messages"]["5"] = "X" * 28 + r" (\ctr 5)"
    ddb["lpcs"] += compile_line("IF ( VERB 7 ) 42 CSET 5 MESS 5 END", {})
    return ddb


def goes_down_whole(lines):
    lines = [line.replace("?", " ").rstrip() for line in lines]
    at = max(n for n, line in enumerate(lines) if line.startswith("X" * 28))
    assert lines[at] == "X" * 28, f"the line was not broken before it: {lines}"
    assert lines[at + 1].startswith("(42)"), (
        f"the hole did not go down with its bracket: {lines[at:at + 2]}")


@needs_z80
def test_a_hole_goes_down_with_its_word_on_the_z80():
    import emulator
    from test_game_z80 import glyph_table
    from test_markers_z80 import (DATABASE, ENTER, LISTING, SOURCE,
                                  asked_again, got_going)

    database = Database(breaking())
    with open(DATABASE, "wb") as f:
        f.write(database.build())
    emulator.assemble(SOURCE, listing=LISTING, defines=("HOLES",))
    glyphs = glyph_table(database)
    session = emulator.Session()
    try:
        got_going(session, glyphs)
        session.type("CORTA" + ENTER)
        goes_down_whole(asked_again(session, glyphs, 2))
    finally:
        session.close()


@needs_pc
def test_a_hole_goes_down_with_its_word_on_the_pc(tmp_path):
    import pc_game

    folder = str(tmp_path)
    ddb = breaking()
    # forty columns here: the same shape, twelve letters further on
    ddb["messages"]["5"] = "X" * 36 + r" (\ctr 5)"
    pc_game.build(ddb, folder)
    printed, _ = pc_game.play(folder, "CORTA" + chr(13), stop=True)
    lines = [line.rstrip() for line in printed.replace(chr(13), "").split(chr(10))]
    at = max(n for n, line in enumerate(lines) if line.startswith("X" * 36))
    assert lines[at].endswith("X" * 36), lines[at:at + 2]
    assert lines[at + 1].startswith("(42)"), lines[at:at + 2]
