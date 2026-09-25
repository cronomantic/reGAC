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
"""DO n: a table of conditions of its own, run where it is named.

Not the original's.  What was decided, and what everything here holds every
interpreter to:

- The tables are written in blocks of their own, /PROC #n, and not borrowed
  from rooms.
- A table run by DO runs as if it were written where DO is: what comes out
  true in it has taken the order, and what ends the turn in it -- WAIT, OKAY,
  EXIT, a refusal of GET -- ends the turn, so the table that ran it goes no
  further.
- What the table that ran it had on the stack is still there when it comes
  back.
- DO of a table there is not does nothing, and so does DO more than eight
  deep, which is as deep as a picture may call another.

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

from regac.binary import Database, Reader  # noqa: E402
from regac.check import problems_of  # noqa: E402
from regac.conds import compile_line  # noqa: E402
from regac.srcgen import generate  # noqa: E402
from regac.srcparse import SourceError, parse  # noqa: E402

DEEPEST = 8

# The verbs, one for each thing to be asked.
VERBS = {"MIRA": 1, "SALIR": 2, "SALTA": 3, "GRITA": 4, "VUELA": 5,
         "CAE": 6, "NADA": 7, "PILA": 8}
PROCS = {
    1: ["IF ( AT 1 ) MESS 1 END"],
    2: ["IF ( AT 1 ) MESS 2 WAIT END"],
    3: ["IF ( AT 2 ) MESS 2 END"],
    4: ["IF ( AT 1 ) MESS 4 DO 4 END"],
    5: ["IF ( AT 1 ) CTR 9 END"],
}
LOW = [
    "IF ( VERB 3 ) DO 1 MESS 3 END",        # runs, and comes back
    "IF ( VERB 4 ) DO 2 MESS 3 END",        # a WAIT in it ends the turn
    "IF ( VERB 5 ) DO 3 MESS 3 END",        # nothing true in it
    "IF ( VERB 6 ) DO 4 END",               # calls itself, eight deep
    "IF ( VERB 7 ) DO 99 MESS 3 END",       # there is no table 99
    "IF ( VERB 3 ) MESS 5 END",             # the same table goes on
    "IF ( VERB 4 ) MESS 5 END",             # and after a WAIT it does not
]
SAYS = {"1": "UNO.", "2": "DOS.", "3": "TRES.", "4": "CUATRO.", "5": "SIGUE."}

# What each order has to leave on the screen, and what it must not.
WANTED = {
    "SALTA": ("UNO.TRES.SIGUE.", ()),
    "GRITA": ("DOS.", ("TRES.", "SIGUE.", "NO PUEDES.")),
    "VUELA": ("TRES.", ("DOS.",)),
    "CAE": ("CUATRO." * DEEPEST, ("CUATRO." * (DEEPEST + 1),)),
    "NADA": ("TRES.", ()),
}


def compiled(lines):
    code = []
    for line in lines:
        code += compile_line(line, {})
    return code


def with_procs(ddb):
    """The adventure a test builds, with the verbs, the tables and the
    messages of this one."""
    ddb["verbs"] = dict(VERBS)
    ddb["messages"].update(SAYS)
    ddb["lpcs"] = compiled(LOW)
    ddb["procs"] = {str(n): compiled(lines) for n, lines in PROCS.items()}
    return ddb


def a_small_one():
    """The adventure, without anything a machine needs to show it."""
    from test_markers_z80 import adventure

    return with_procs(adventure())


# -- the language --------------------------------------------------------

SOURCE = """\
.def SALUDO 7
/CTL
start 1
/VOC
MIRA 1 verb
/MSG
#1
HOLA
/LOC #1
UN CUARTO
/LOW
IF ( VERB 1 ) DO SALUDO END
/PROC #SALUDO
IF ( AT 1 ) MESS 1 END
/PROC #3
IF ( AT 1 ) WAIT END
"""


def test_a_source_names_its_tables_and_calls_them():
    ddb = parse(SOURCE)
    assert set(ddb["procs"]) == {7, 3}
    assert ["PUSH", 7] in ddb["lpcs"] and ["DO"] in ddb["lpcs"]
    assert ["MESS"] in ddb["procs"][7]


def test_they_come_back_out_of_a_source_the_same():
    ddb = json.loads(json.dumps(parse(SOURCE)))
    again = json.loads(json.dumps(parse(generate(ddb))))
    assert again["procs"] == ddb["procs"]
    assert again["lpcs"] == ddb["lpcs"]


def test_an_adventure_without_them_is_written_as_it_was():
    ddb = parse(SOURCE.split("/PROC")[0].replace("DO SALUDO", "MESS 1"))
    assert "procs" not in ddb
    assert "/PROC" not in generate(json.loads(json.dumps(ddb)))


def test_a_table_is_named_once():
    try:
        parse(SOURCE + "/PROC #3\nIF ( AT 1 ) WAIT END\n")
    except SourceError as e:
        assert "already" in str(e)
    else:
        raise AssertionError("two tables 3 went through")


def test_they_travel_in_the_list_of_the_rooms_tables_apart():
    """In the binary, with the top bit set, so that a room never finds one;
    and read back apart from the rooms'."""
    ddb = a_small_one()
    ddb["lcs"] = {"1": compiled(["IF ( VERB 1 ) MESS 1 END"])}
    reader = Reader(Database(ddb).build())
    _, _, locals_, procs = reader.conditions()
    assert set(locals_) == {"1"}
    assert {int(k): v for k, v in procs.items()} == \
        {int(k): v for k, v in ddb["procs"].items()}


def test_a_do_of_a_table_there_is_not_is_said():
    ddb = a_small_one()
    said = [p.message for p in problems_of(ddb)]
    assert any("DO 99" in what and "no /PROC 99" in what for what in said), said


# -- the interpreter in Python --------------------------------------------

def python_says(ddb, order):
    from test_interpreter import interpreter

    game = interpreter()(json.loads(json.dumps(ddb)))
    assert game.start_adventure(), "it would not start"
    out = []
    game.print = out.append
    orders = iter([order])
    game.input = lambda: next(orders, None)
    while not game.main_loop():
        pass
    return "".join(out).replace("\n", "")


def test_on_the_interpreter_in_python():
    ddb = a_small_one()
    for order, (wanted, unwanted) in WANTED.items():
        said = python_says(ddb, order)
        assert wanted in said, f"{order}: {said!r}"
        for one in unwanted:
            assert one not in said, f"{order} said {one!r}: {said!r}"


def test_the_stack_of_the_table_that_ran_it_is_kept():
    """A table that leaves something on the stack before DO finds it there
    after: here the 5 is PRIN's."""
    ddb = a_small_one()
    ddb["lpcs"] = [["PUSH", 8], ["VERB"], ["IF"], ["PUSH", 5], ["PUSH", 5],
                   ["DO"], ["PRIN"], ["END"]]
    assert "5" in python_says(ddb, "PILA")


def test_the_example_plays_on_it():
    """Which it did not: the interpreter in Python asked for exactly the keys
    a decompiled adventure has, and the example has its noises besides."""
    from test_interpreter import interpreter
    from regac.viewer import read_adventure

    ddb = read_adventure(os.path.join(ROOT, "ejemplo", "faro.gac"), "spectrum")
    assert interpreter()(ddb).start_adventure()


# -- the Z80's -------------------------------------------------------------

def turn_said(lines, order):
    """What the turn of an order said: from the order, typed after the
    question, to the question that asks for the next one.  The question is a
    ">" and none of the messages has one.  A cell of the screen nobody has
    written on reads back as no letter at all, a question mark, and is taken
    off."""
    text = "".join(line.replace("?", " ").strip() for line in lines)
    at = text.rindex(">" + order) + 1 + len(order)
    end = text.find(">", at)
    return text[at:] if end < 0 else text[at:end]


def z80_says(ddb, orders):
    """Every order typed in turn on a Spectrum 48 built with DO, and what the
    turn of each said."""
    import emulator
    from test_game_z80 import glyph_table
    from test_markers_z80 import (DATABASE, ENTER, LISTING, SOURCE,
                                  asked_again, got_going)

    database = Database(ddb)
    with open(DATABASE, "wb") as f:
        f.write(database.build())
    emulator.assemble(SOURCE, listing=LISTING, defines=("PROCS",))
    glyphs = glyph_table(database)
    said = {}
    session = emulator.Session()
    try:
        got_going(session, glyphs)
        for asked, order in enumerate(orders, start=2):
            session.type(order + ENTER)
            said[order] = turn_said(asked_again(session, glyphs, asked), order)
    finally:
        session.close()
    return said


def needs_z80(func):
    import emulator

    if pytest is None:
        return func
    return pytest.mark.skipif(not emulator.available(),
                              reason="sjasmplus and ZEsarUX must be in tools/")(func)


@needs_z80
def test_on_the_z80():
    ddb = a_small_one()
    said = z80_says(ddb, list(WANTED))
    for order, (wanted, unwanted) in WANTED.items():
        assert wanted in said[order], f"{order}: {said[order]!r}"
        for one in unwanted:
            assert one not in said[order], f"{order} said {one!r}: {said[order]!r}"


@needs_z80
def test_the_stack_of_the_table_that_ran_it_is_kept_on_the_z80():
    ddb = a_small_one()
    ddb["lpcs"] = [["PUSH", 8], ["VERB"], ["IF"], ["PUSH", 5], ["PUSH", 5],
                   ["DO"], ["PRIN"], ["END"]]
    assert "5" in z80_says(ddb, ["PILA"])["PILA"]


# -- the PC's --------------------------------------------------------------

def pc_says(ddb, orders, folder):
    """Every order typed in turn on the PC, and what the turn of each said,
    out of what the game printed."""
    import pc_game

    pc_game.build(ddb, folder)
    printed, _ = pc_game.play(folder, "".join(o + chr(13) for o in orders),
                              stop=True)
    lines = printed.replace(chr(13), "").split(chr(10))
    return {order: turn_said(lines, order) for order in orders}


def needs_pc(func):
    import dosbox

    if pytest is None:
        return func
    return pytest.mark.skipif(not dosbox.available(),
                              reason="NASM and DOSBox-X must be there")(func)


@needs_pc
def test_on_the_pc(tmp_path):
    ddb = a_small_one()
    said = pc_says(ddb, list(WANTED), str(tmp_path))
    for order, (wanted, unwanted) in WANTED.items():
        assert wanted in said[order], f"{order}: {said[order]!r}"
        for one in unwanted:
            assert one not in said[order], f"{order} said {one!r}: {said[order]!r}"


@needs_pc
def test_the_stack_of_the_table_that_ran_it_is_kept_on_the_pc(tmp_path):
    ddb = a_small_one()
    ddb["lpcs"] = [["PUSH", 8], ["VERB"], ["IF"], ["PUSH", 5], ["PUSH", 5],
                   ["DO"], ["PRIN"], ["END"]]
    assert "5" in pc_says(ddb, ["PILA"], str(tmp_path))["PILA"]
