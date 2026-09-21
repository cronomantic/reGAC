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
"""The Python interpreter has to understand a sentence the way the 8 bit one
does, because it is what the adventure is written against.

Both rules here were settled by asking the original rather than by reading it:
typing EX at MegaCorp makes it ask what to examine, and typing EXAMINAR, one
letter more than the word it holds, makes it say it does not understand.
"""

import importlib.util
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from regac.opcodes import OPS  # noqa: E402


def interpreter():
    """runGAC is a program rather than a module, so it is loaded by hand."""
    spec = importlib.util.spec_from_file_location(
        "rungac", os.path.join(ROOT, "runGAC.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.GAC_Interpreter


VERBS = {"NORTE": 1, "N": 1, "SUR": 2, "COGE": 5, "EXAMINA": 9}
NOUNS = {"LLAVE": 3, "PUERTA": 4, "LAMPARA": 7}
ADVERBS = {"DESPACIO": 1}


def find(word, words=None):
    game = interpreter()
    return game.__dict__["_GAC_Interpreter__find_word"](None, words or VERBS, word)


def parse(sentence):
    game = interpreter()
    it = object.__new__(game)
    it.verbs, it.nouns, it.adverbs = VERBS, NOUNS, ADVERBS
    it.pronouns, it.old_noun = ["LO"], 0
    # what the order before left behind, which is where a pronoun of this one
    # would take its meaning from
    it.noun1 = it.noun2 = 0
    game.__dict__["_GAC_Interpreter__parse_input"](it, sentence)
    return it.verb, it.noun1, it.noun2, it.adverb


def test_the_interpreter_here_knows_every_opcode():
    """The one that runs on this side has to keep up with the language.

    It is a big chain of names, so an opcode nobody added to it falls through
    to the end and prints INVALID OPCODE in the middle of somebody's
    adventure -- which is what SOUND did until this was written.
    The two that do nothing anywhere are the two the original left empty.
    """
    with open(os.path.join(ROOT, "runGAC.py"), encoding="utf-8") as f:
        source = f.read()
    missing = [op.name for op in OPS
               if op.name not in ("ENDTABLE", "NOP", "NOP29")
               and f'"{op.name}"' not in source
               and f"'{op.name}'" not in source]
    assert not missing, f"runGAC.py has never heard of {missing}"


def test_the_start_of_a_word_is_enough():
    assert find("EX") == 9
    assert find("EXAMINA") == 9
    assert find("NOR") == 1


def test_more_than_the_word_holds_matches_nothing():
    assert find("EXAMINAR") == 0
    assert find("XYZZY") == 0


def test_the_shortest_of_the_words_a_letter_starts():
    assert find("N") == 1                       # N, not NORTE
    assert find("LA", NOUNS) == 7               # swallowed by LAMPARA


def test_a_sentence_fills_the_four_slots():
    assert parse("COGE LLAVE PUERTA DESPACIO") == (5, 3, 4, 1)


def test_the_second_noun_needs_a_first():
    verb, noun1, noun2, adverb = parse("COGE LLAVE PUERTA")
    assert (noun1, noun2) == (3, 4)


def test_a_pronoun_stands_for_the_last_noun_named():
    """The last, which is the second when the order before named two.  Read
    in the original and measured on Los pajaros de Bangkok: after COGER AGUA
    BAR, the LO of COGER LO came out as the BAR."""
    game = interpreter()
    it = object.__new__(game)
    it.verbs, it.nouns, it.adverbs = VERBS, NOUNS, ADVERBS
    it.pronouns, it.old_noun = ["LO"], 0
    it.noun1 = it.noun2 = 0
    parse_input = game.__dict__["_GAC_Interpreter__parse_input"]
    parse_input(it, "COGE LLAVE PUERTA")
    assert (it.noun1, it.noun2) == (3, 4)
    parse_input(it, "COGE LO")
    assert it.noun1 == 4, "the pronoun took the first noun, not the last"


def cut(line, named=()):
    """One typed line into the orders it holds."""
    game = interpreter()
    it = object.__new__(game)
    it.separators = list(named)
    it.punctuation = list("\0 .,-!?:")
    return game.__dict__["_GAC_Interpreter__cut_into_orders"](it, line)


def test_a_mark_of_punctuation_parts_two_orders():
    assert cut("XYZY.SUR") == ["XYZY", "SUR"]
    assert cut("XYZY,SUR") == ["XYZY", "SUR"]


def test_the_other_marks_part_words_and_not_orders():
    """Only four marks cut an order in two, and the adventure's own table of
    punctuation is what parts words.  Measured on the original: COGE-MATA is
    one order, where COGE,MATA is two."""
    assert cut("XYZY-SUR") == ["XYZY SUR"]
    assert cut("XYZY?SUR") == ["XYZY SUR"]
    assert cut("XYZY:SUR") == ["XYZY SUR"]


ORIGINALS = ["THEN", "AND"]                     # what the decompiler writes


def test_then_and_and_part_them_as_in_the_original():
    """Typing XYZZY THEN SUR at MegaCorp makes it complain about the first
    word and then walk south.  The two words are the original interpreter's;
    the decompiler writes them into the database so that a recompiled original
    parts orders where it always did."""
    assert cut("COGE LLAVE THEN SUR", ORIGINALS) == ["COGE LLAVE", "SUR"]
    assert cut("COGE LLAVE AND SUR", ORIGINALS) == ["COGE LLAVE", "SUR"]


def test_the_interpreter_names_none_by_itself():
    assert cut("COGE LLAVE THEN SUR") == ["COGE LLAVE THEN SUR"]


def test_a_spanish_y_parts_nothing():
    """Measured on the original, which walks south without complaining."""
    assert cut("XYZZY Y SUR", ORIGINALS) == ["XYZZY Y SUR"]


def test_the_words_are_matched_whole():
    assert cut("ESPERA ANDAR SUR", ORIGINALS) == ["ESPERA ANDAR SUR"]


def test_an_adventure_names_its_own():
    assert cut("COGE LLAVE Y SUR", named=["Y"]) == ["COGE LLAVE", "SUR"]


def a_memory_holding(word):
    """A stand-in for the interpreter's own little table of words."""
    blob = bytearray(b"\x00" * 64)
    blob += b"Memory full ... " + bytes((0xFF, 13, 10, 0xFF))
    blob += word + bytes((0xFF, 13, 10))
    blob += b"Enter name of"
    return list(blob)


def test_the_word_for_having_nothing_is_read_from_the_interpreter():
    """It is the one text of an adventure that is not in its database: the
    interpreter keeps it as plain letters, and MegaCorp answering
    `Llevo conmigo:XXXX` once it was changed in the machine is what proved
    it.  Seven bytes, padded with spaces, ended by $FF."""
    from deGAC import word_for_nothing

    assert word_for_nothing(a_memory_holding(b"nada   ")) == "nada"
    assert word_for_nothing(a_memory_holding(b"NADA   ")) == "NADA"
    assert word_for_nothing(a_memory_holding(b"nothing")) == "nothing"
    assert word_for_nothing(a_memory_holding(b"       ")) == "Nothing"
    assert word_for_nothing([0] * 256) == "Nothing"


#: What each of the eight really says, which is not the same in all of them:
#: two of the four Spanish adaptations never translated the word.
WORD_FOR_NOTHING = {
    "Bangkok1": "nothing", "Bangkok2": "nothing",
    "quijote1": "nothing", "quijote2": "nothing",
    "megacorp1": "nada", "megacorp2": "nada",
    "vajillas1": "NADA", "vajillas2": "NADA",
}


def test_the_decompiler_reads_the_word_each_adventure_really_has():
    import glob
    import json

    where = os.path.join(ROOT, "snapshots", "*.json")
    for path in sorted(glob.glob(where)):
        name = os.path.basename(path)[:-5]
        if name not in WORD_FOR_NOTHING:
            continue
        with open(path, encoding="utf-8") as f:
            said = json.load(f).get("no_objs_msg")
        assert said == WORD_FOR_NOTHING[name], (
            f"{name} says {said!r} and its interpreter says "
            f"{WORD_FOR_NOTHING[name]!r}: decompile it again"
        )


def test_the_decompiler_writes_the_two_the_original_knew():
    """A decompiled adventure that lost them would stop parting orders where
    it used to, and nothing else would notice."""
    import glob
    import json

    where = os.path.join(ROOT, "snapshots", "*.json")
    for path in sorted(glob.glob(where)):
        with open(path, encoding="utf-8") as f:
            named = json.load(f).get("separators", [])
        assert [w.upper() for w in named] == ORIGINALS, (
            f"{os.path.basename(path)} names {named}: decompile it again"
        )


if __name__ == "__main__":
    for check in (
        test_the_start_of_a_word_is_enough,
        test_more_than_the_word_holds_matches_nothing,
        test_the_shortest_of_the_words_a_letter_starts,
        test_a_mark_of_punctuation_parts_two_orders,
        test_then_and_and_part_them_as_in_the_original,
        test_the_interpreter_names_none_by_itself,
        test_a_spanish_y_parts_nothing,
        test_the_words_are_matched_whole,
        test_an_adventure_names_its_own,
        test_the_word_for_having_nothing_is_read_from_the_interpreter,
        test_a_sentence_fills_the_four_slots,
        test_the_second_noun_needs_a_first,
    ):
        check()
        print(f"{check.__name__}: correcto")
