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
"""The four markers the interpreter owns, and what it does with them.

Markers 0 to 3 are not the adventure's: 0 says a room has just been
described, 1 that the place has light, 2 that the player carries something
alight, and 3 that the score is not to be told at the end.  Counters 0, 126
and 127 are the interpreter's too -- the score and the turns.

None of that was here, and it was not a detail: Los pajaros de Bangkok asks
`SET? 0` fifteen times to write out where the exits are, and none of those
lines could ever run.  What each marker does was read in the manual of the
reference decompiler and then measured on the real games in an emulator,
which is also where the two surprises came from -- that in the dark the
picture goes off the screen as well, and that the turn is counted after the
high priority table and not before it.  The full account is in
doc/pendiente.md.

The tests below do not read pixels where they do not have to: a condition
that ends the game says what the interpreter believed far more exactly than
a screenful of letters.  The ones that must read the screen do it through
the adventure's own font.
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
from test_game_z80 import glyph_table, screen  # noqa: E402

SPECTRUM = os.path.join(ROOT, "z80", "spectrum")
SOURCE = os.path.join(SPECTRUM, "game.asm")
DATABASE = os.path.join(SPECTRUM, "game.rgac")
SNAPSHOT = os.path.join(SPECTRUM, "game.sna")
LISTING = os.path.join(SPECTRUM, "game.lst")
ENTER = chr(13)

LOOK_VERB, QUIT_VERB = 1, 2

if pytest is not None:
    needs_tools = pytest.mark.skipif(
        not emulator.available(), reason="sjasmplus and ZEsarUX must be in tools/"
    )
else:

    def needs_tools(func):
        return func


def readable_font():
    """A font whose every letter is a different eight bytes, so that what is
    on the screen can be read back.  The table is indexed by the character
    itself, which is why this is as long as the last character it draws."""
    font = [0] * (128 * 8)
    for code in range(32, 127):
        font[code * 8:code * 8 + 8] = [code] * 8
    return font


def adventure(hpcs=(), lpcs=(), rooms=None, objects=None, messages=None):
    """A small adventure with whatever conditions a test needs."""
    say = {
        "240": ">",
        "241": "NO PUEDES.",
        "242": "COMO DICES?",
        "244": "SEGURO?",
        "249": "PUNTOS:",
        "250": " EN ",
        "251": "ESTA OSCURO.",
        "253": "VES:",
        "254": "MUY BIEN.",
        "255": " PASOS.",
    }
    say.update(messages or {})
    return {
        "font": readable_font(),
        "verbs": {"MIRA": LOOK_VERB, "SALIR": QUIT_VERB},
        "nouns": {},
        "adverbs": {},
        "pronouns": [],
        "messages": say,
        "objects": objects if objects is not None else {},
        "locations": rooms if rooms is not None else {
            "1": {"graphic_id": 0, "exits": [], "desc": "UN CUARTO"},
        },
        "hpcs": list(hpcs),
        "lpcs": list(lpcs),
        "lcs": {},
        "model": "SPECTRUM",
        "punctuation": list("\0 .,-!?:"),
        "separators": [],
        "init_loc": 1,
        "no_objs_msg": "NADA",
        "gfx": {},
    }


def build(ddb):
    database = Database(ddb)
    with open(DATABASE, "wb") as f:
        f.write(database.build())
    return database, emulator.assemble(SOURCE, listing=LISTING)


def ends(ddb, within=6.0):
    """Whether the adventure stops itself, which is how a condition tells the
    test what the interpreter believed."""
    _, listing = build(ddb)
    over = emulator.label_address(listing, "done_flag")
    session = emulator.Session()
    try:
        session.load(SNAPSHOT)
        # An order is typed first so that the probes in the high priority
        # table get a second pass at the state a turn leaves behind.  The word
        # is one the adventure does not know, so that nothing but the asking
        # happens because of it.
        time.sleep(2.0)
        session.type("X" + ENTER)
        deadline = time.time() + within
        while time.time() < deadline:
            time.sleep(0.1)
            if session.read(over, 1)[0] == 0xFF:
                return True
        return False
    finally:
        session.close()


def asked_again(session, glyphs, times, timeout=30.0):
    """Wait until the interpreter has asked for an order that many times.

    Waiting a fixed while instead is waiting either too little or too long,
    and too little is what a machine shared between several emulators gives:
    the screen comes back empty and the test fails for nothing of its own.
    The prompt is the adventure's own message 240, a ">" here.
    """
    deadline = time.time() + emulator.longer(timeout)
    lines = []
    while time.time() < deadline:
        lines = [line for line in screen(session, glyphs) if line]
        if sum(line.count(">") for line in lines) >= times:
            return lines
        time.sleep(0.2)
    return lines


def played(ddb, orders=()):
    """The lines on the screen after typing whatever was asked for."""
    database, listing = build(ddb)
    glyphs = glyph_table(database)
    session = emulator.Session()
    try:
        session.load(SNAPSHOT)
        asked = 1
        lines = asked_again(session, glyphs, asked)
        for order in orders:
            session.type(order + ENTER)
            asked += 1
            lines = asked_again(session, glyphs, asked)
        return lines
    finally:
        session.close()


# The condition that stops the game the moment marker zero is set, which is
# the interpreter saying it has just described a room.
STOPS_ON_DESCRIBED = [["PUSH", 0], ["SET?"], ["IF"], ["EXIT"], ["END"]]


@needs_tools
def test_a_noun_on_its_own_is_something_it_cannot_do():
    """A word it knows and no verb: that is an order it cannot do, not one it
    did not understand.  Read in the original -- it asks after the verb and
    the noun before choosing which to say -- and then asked of it: JARRO on
    its own at MegaCorp answers "No puedo hacer eso" and XYZZY answers
    "Perdon?"."""
    ddb = adventure()
    ddb["nouns"] = {"PIEDRA": 1}
    known = played(ddb, orders=["PIEDRA"])
    assert any("NO PUEDES." in line for line in known), known
    assert not any("COMO DICES?" in line for line in known), known
    unknown = played(ddb, orders=["XYZZY"])
    assert any("COMO DICES?" in line for line in unknown), unknown


@needs_tools
def test_goto_describes_the_room_it_arrives_in():
    """Their GOTO is their LOOK with a room put in first, so the description
    comes out where the GOTO is and not when the turn comes round again.
    Measured on the original: GOTO 20 with a message after it printed room
    20 and then the message."""
    ddb = adventure(
        lpcs=[["PUSH", LOOK_VERB], ["VERB"], ["IF"],
              ["PUSH", 2], ["GOTO"], ["PUSH", 100], ["MESS"], ["END"]],
        rooms={
            "1": {"graphic_id": 0, "exits": [], "desc": "UN CUARTO"},
            "2": {"graphic_id": 0, "exits": [], "desc": "EL OTRO CUARTO"},
        },
        messages={"100": "Y LUEGO ESTO"},
    )
    said = played(ddb, orders=["MIRA"])
    where = [n for n, line in enumerate(said) if "EL OTRO CUARTO" in line]
    after = [n for n, line in enumerate(said) if "Y LUEGO ESTO" in line]
    assert where and after, said
    assert where[0] <= after[0], "the room is described before the message"


@needs_tools
def test_a_noun_is_either_of_the_two():
    """NOUN n answers for the second noun of a line as well as the first:
    read in the original, which compares both, and asked of it -- COGE DISCO
    AGUJA answers to the aguja."""
    ddb = adventure(
        lpcs=[["PUSH", 2], ["NOUN"], ["IF"], ["PUSH", 100], ["MESS"], ["END"]],
        messages={"100": "EL SEGUNDO"},
    )
    ddb["nouns"] = {"PIEDRA": 1, "PALO": 2}
    said = played(ddb, orders=["MIRA PIEDRA PALO"])
    assert any("EL SEGUNDO" in line for line in said), said


@needs_tools
def test_a_pronoun_stands_for_the_last_noun_named():
    """And the last means the second when an order named two.  Measured on
    Los pajaros de Bangkok, which is the one of the four with pronouns:
    after COGER AGUA BAR, the LO of COGER LO came out as the BAR."""
    ddb = adventure(
        lpcs=[["PUSH", 2], ["NOUN"], ["IF"], ["PUSH", 100], ["MESS"], ["END"]],
        messages={"100": "EL SEGUNDO"},
    )
    ddb["nouns"] = {"PIEDRA": 1, "PALO": 2}
    ddb["pronouns"] = ["LO"]
    said = played(ddb, orders=["MIRA PIEDRA PALO", "MIRA LO"])
    assert sum("EL SEGUNDO" in line for line in said) == 2, said


@needs_tools
def test_an_adventure_that_looks_says_its_first_room_once():
    """A game opens by describing the room it starts in, and MegaCorp
    describes it again from its own high priority table; on the screen it
    comes out once, because describing wipes the text window first.  Measured
    on the original, whose table was replaced by IF ( AT 1 ) LOOK END."""
    lines = played(adventure(hpcs=[["LOOK"], ["END"]]))
    said = sum(line.count("UN CUARTO") for line in lines)
    assert said == 1, f"the room was described {said} times: {lines}"


@needs_tools
def test_a_description_is_written_over_the_line_it_starts_on():
    """Measured on the original in its password room, whose description is
    one line long: with a message printed just before the LOOK, what is left
    on the screen is the description with the tail of the message showing
    past the end of it -- INTRODUZCA LA CLAVEsa... where El tiempo pasa...
    was.  Nothing is wiped and the line is not ended first.  In TEXT mode its
    DESC skips that part, and there the description simply follows the
    message along the same line, measured too."""
    say = {"100": "XXXXXXXXXXXX"}
    probe = [["LF"], ["PUSH", 100], ["MESS"], ["LOOK"], ["END"]]
    over = played(adventure(hpcs=probe, messages=say))
    assert any("UN CUARTOXXX" in line for line in over), (
        f"the description did not start at the left of the line: {over}")
    kept = played(adventure(hpcs=[["TEXT"]] + probe, messages=say))
    assert any("XXXXXXXXXXXXUN CUARTO" in line for line in kept), (
        f"in TEXT mode it follows the message along the line: {kept}")


@needs_tools
def test_a_room_described_sets_the_marker():
    assert ends(adventure(hpcs=STOPS_ON_DESCRIBED)), (
        "marker zero was never set, so an adventure cannot tell that a room "
        "has just been described"
    )


@needs_tools
def test_a_game_starts_in_the_light():
    """Marker one is the interpreter's doing: not one of the eight adventures
    ever sets it for the first room, and all of them are lit."""
    lit = [["PUSH", 1], ["SET?"], ["IF"], ["EXIT"], ["END"]]
    assert ends(adventure(hpcs=lit)), "a new game did not start in the light"


def two_rooms(before_leaving):
    """Room one puts the light out as it leaves for room two, and room two
    stops the game if it was described.  What `before_leaving` does decides
    whether room two is in the dark.

    Marker zero is put out on the way, the way the real adventures do it, so
    that what room one left behind cannot be mistaken for room two."""
    leave = [["PUSH", 1], ["AT"], ["IF"]] + list(before_leaving) + [
        ["PUSH", 0], ["RESE"], ["PUSH", 1], ["RESE"], ["PUSH", 2], ["GOTO"],
        ["END"],
    ]
    stop = [["PUSH", 2], ["AT"], ["IF"], ["PUSH", 0], ["SET?"], ["IF"],
            ["EXIT"], ["END"], ["END"]]
    return adventure(
        hpcs=leave + stop,
        rooms={
            "1": {"graphic_id": 0, "exits": [], "desc": "UN CUARTO"},
            "2": {"graphic_id": 0, "exits": [], "desc": "OTRO CUARTO"},
        },
    )


@needs_tools
def test_the_dark_describes_nothing():
    assert not ends(two_rooms([])), (
        "a room with no light was described anyway: marker zero was set"
    )


@needs_tools
def test_a_lamp_is_light_enough():
    carrying = [["PUSH", 2], ["SET"]]
    assert ends(two_rooms(carrying)), (
        "the room stayed dark although the player was carrying a light"
    )


@needs_tools
def test_the_dark_says_so():
    lines = played(two_rooms([]))
    assert any("ESTA OSCURO." in line for line in lines), (
        f"the interpreter never said it was dark: {lines}"
    )
    assert not any("OTRO CUARTO" in line for line in lines), (
        f"the room was described in the dark: {lines}"
    )


@needs_tools
def test_what_lies_about_is_named_after_the_description():
    """The introduction first and then the names, commas between and all on
    one line: TAMBIEN PUEDO VER:UN DISCO METALICO,UNA PISTOLA."""
    lines = played(adventure(objects={
        "1": {"weight": 1, "initial_loc": 1, "name": "UNA LLAVE"},
        "2": {"weight": 1, "initial_loc": 1, "name": "UNA VELA"},
        "3": {"weight": 1, "initial_loc": 9, "name": "UN BARCO"},
    }))
    written = " ".join(lines)
    assert "VES:UNA LLAVE,UNA VELA" in written, (
        f"what was lying in the room was not named: {lines}"
    )
    assert "UN BARCO" not in written, (
        f"something in another room was named: {lines}"
    )


@needs_tools
def test_an_empty_room_says_nothing_at_all():
    lines = played(adventure(objects={
        "1": {"weight": 1, "initial_loc": 9, "name": "UN BARCO"},
    }))
    assert not any("VES:" in line for line in lines), (
        f"an empty room introduced what can be seen anyway: {lines}"
    )


@needs_tools
def test_list_names_them_the_same_way():
    """LIST is where the inventory comes from -- LLEVAS UN LIBRO,UNA CAMISA --
    and with nothing to name it writes the word the adventure gives for it."""
    listing = [["PUSH", LOOK_VERB], ["VERB"], ["IF"],
               ["PUSH", 255], ["LIST"], ["WAIT"], ["END"]]
    lines = played(adventure(
        lpcs=listing,
        objects={
            "1": {"weight": 1, "initial_loc": 255, "name": "UNA LLAVE"},
            "2": {"weight": 1, "initial_loc": 255, "name": "UNA VELA"},
        },
    ), orders=["MIRA"])
    assert any("UNA LLAVE,UNA VELA" in line for line in lines), (
        f"the inventory came out wrong: {lines}"
    )

    empty = played(adventure(lpcs=listing), orders=["MIRA"])
    assert any("NADA" in line for line in empty), (
        f"with nothing to name, the word for it was not written: {empty}"
    )


@needs_tools
def test_the_turn_is_counted_after_the_high_table():
    """MegaCorp sets its whole game up in a condition guarded by the count
    still being zero.  Counted first, that condition never runs, the counter
    it should have filled stays at nought, and the next line of the same
    table kills the player on the opening move."""
    first = [["PUSH", 0], ["PUSH", 126], ["EQU?"], ["IF"], ["EXIT"], ["END"]]
    assert ends(adventure(hpcs=first)), (
        "the turn was counted before the high priority table, so a condition "
        "that only holds on the first turn could never run"
    )


@needs_tools
def test_the_score_is_told_at_the_end():
    quit_now = [["PUSH", QUIT_VERB], ["VERB"], ["IF"],
                ["PUSH", 7], ["PUSH", 0], ["CSET"], ["EXIT"], ["END"]]
    lines = played(adventure(lpcs=quit_now), orders=["SALIR"])
    written = " ".join(lines)
    assert "PUNTOS:7" in written, f"the score was not told: {lines}"
    assert "PASOS." in written, f"the turns were not told: {lines}"


@needs_tools
def test_the_fourth_marker_keeps_the_score_quiet():
    quiet = [["PUSH", QUIT_VERB], ["VERB"], ["IF"],
             ["PUSH", 3], ["SET"], ["EXIT"], ["END"]]
    lines = played(adventure(lpcs=quiet), orders=["SALIR"])
    assert not any("PUNTOS:" in line for line in lines), (
        f"the score was told although the adventure asked for silence: {lines}"
    )


if __name__ == "__main__":
    test_a_room_described_sets_the_marker()
    test_a_game_starts_in_the_light()
    test_the_dark_describes_nothing()
    test_a_lamp_is_light_enough()
    test_the_dark_says_so()
    test_what_lies_about_is_named_after_the_description()
    test_an_empty_room_says_nothing_at_all()
    test_list_names_them_the_same_way()
    test_the_turn_is_counted_after_the_high_table()
    test_the_score_is_told_at_the_end()
    test_the_fourth_marker_keeps_the_score_quiet()
    print("the markers are the interpreter's own")
