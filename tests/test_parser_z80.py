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
"""Making sense of what the player typed, checked on a real Z80.

Each sentence is written into an include the build picks up, turned into the
adventure's own character codes and handed to the parser; what comes back is
the verb, the nouns and the adverb it settled on.
"""

import os
import sys

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
SOURCE = os.path.join(SPECTRUM, "test_parser.asm")
DATABASE = os.path.join(SPECTRUM, "parser.rgac")
SNAPSHOT = os.path.join(SPECTRUM, "parser.sna")
LISTING = os.path.join(SPECTRUM, "parser.lst")
INCLUDE = os.path.join(SPECTRUM, "parser_input.inc")

ADVENTURE = {
    "font": [0] * 1024,
    "verbs": {"NORTE": 1, "N": 1, "SUR": 2, "COGE": 5, "DEJA": 6, "EXAMINA": 9},
    "nouns": {"LLAVE": 3, "PUERTA": 4, "LAMPARA": 7},
    "adverbs": {"DESPACIO": 1, "RAPIDO": 2},
    "pronouns": ["LO"],
    "messages": {"1": "hola"},
    "objects": {"1": {"weight": 1, "initial_loc": 1, "name": "una llave"}},
    "locations": {"1": {"graphic_id": 0, "exits": [], "desc": "aqui"}},
    "hpcs": [],
    "lpcs": [],
    "lcs": {},
    "model": "SPECTRUM",
    "punctuation": list("\0 .,-!?:"),
    "separators": [],
    "init_loc": 1,
    "no_objs_msg": "nada",
    "gfx": {},
}

if pytest is not None:
    needs_tools = pytest.mark.skipif(
        not emulator.available(), reason="sjasmplus and ZEsarUX must be in tools/"
    )
else:

    def needs_tools(func):
        return func


def parse(sentence):
    with open(DATABASE, "wb") as f:
        f.write(Database(ADVENTURE).build())
    text = sentence.upper()
    with open(INCLUDE, "w", encoding="ascii") as f:
        f.write(f'input_text:     db      "{text}"\n')
        f.write(f"input_length    equ     {len(text)}\n")
    listing = emulator.assemble(SOURCE, listing=LISTING)
    names = ("vm_verb", "vm_noun1", "vm_noun2", "vm_adverb", "understood")
    where = {name: emulator.label_address(listing, name) for name in names}
    finished, values = emulator.run(
        SNAPSHOT, listing, reads=[(where[name], 1) for name in names]
    )
    assert finished, "the parser never reached the end"
    return dict(zip(names, [value[0] for value in values]))


@needs_tools
def test_a_verb_and_a_noun():
    assert parse("COGE LLAVE") == {
        "vm_verb": 5, "vm_noun1": 3, "vm_noun2": 0, "vm_adverb": 0, "understood": 1,
    }


@needs_tools
def test_the_shortest_of_the_words_a_letter_starts():
    """N is in the vocabulary in its own right, and so is NORTE; both carry
    the same number, and the shorter one is the one found."""
    assert parse("N")["vm_verb"] == 1


@needs_tools
def test_the_start_of_a_word_is_enough():
    """Typing EX at the original makes it ask what to examine, so it is enough
    here too."""
    assert parse("EX")["vm_verb"] == 9


@needs_tools
def test_more_than_the_word_holds_matches_nothing():
    """EXAMINAR is one letter longer than the word the adventure knows, and
    the original answers that one with a shrug."""
    state = parse("EXAMINAR")
    assert state["vm_verb"] == 0
    assert state["understood"] == 0


@needs_tools
def test_a_short_word_is_swallowed_by_a_longer_one():
    """The price of matching on the start of a word: LA finds LAMPARA, since
    the adventure holds no LA of its own.  The original does the same."""
    state = parse("EXAMINA LA PUERTA DESPACIO")
    assert state["vm_verb"] == 9
    assert state["vm_noun1"] == 7
    assert state["vm_noun2"] == 4
    assert state["vm_adverb"] == 1


@needs_tools
def test_a_mark_of_punctuation_parts_words():
    """Parting words is all the original uses the adventure's own table of
    punctuation for -- what ends an order is a comma, a full stop, a
    semicolon or an exclamation mark, and nothing else -- so COGE-LLAVE is
    two words and means what COGE LLAVE means."""
    state = parse("COGE-LLAVE")
    assert (state["vm_verb"], state["vm_noun1"]) == (5, 3)


@needs_tools
def test_a_second_noun():
    state = parse("COGE LLAVE PUERTA")
    assert (state["vm_noun1"], state["vm_noun2"]) == (3, 4)


@needs_tools
def test_nothing_understood():
    state = parse("XYZZY")
    assert state["understood"] == 0
    assert state["vm_verb"] == 0 and state["vm_noun1"] == 0


if __name__ == "__main__":
    for check in (test_a_verb_and_a_noun, test_the_shortest_of_the_words_a_letter_starts,
                  test_the_start_of_a_word_is_enough,
                  test_more_than_the_word_holds_matches_nothing,
                  test_a_short_word_is_swallowed_by_a_longer_one, test_a_second_noun,
                  test_nothing_understood):
        check()
        print(f"{check.__name__}: correcto")
