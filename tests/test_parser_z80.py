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
    "separators": ["then", "and"],
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
def test_an_abbreviation_is_its_own_word():
    """N reaches NORTE because the vocabulary holds both under one number, not
    because the matching guesses at it."""
    assert parse("N")["vm_verb"] == 1


@needs_tools
def test_words_it_does_not_know_are_passed_over():
    """LA must not be swallowed by LAMPARA, which is what matching on the
    start of a word would do."""
    state = parse("EXAMINA LA PUERTA DESPACIO")
    assert state["vm_verb"] == 9
    assert state["vm_noun1"] == 4
    assert state["vm_adverb"] == 1
    assert state["vm_noun2"] == 0


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
    for check in (test_a_verb_and_a_noun, test_an_abbreviation_is_its_own_word,
                  test_words_it_does_not_know_are_passed_over, test_a_second_noun,
                  test_nothing_understood):
        check()
        print(f"{check.__name__}: correcto")
