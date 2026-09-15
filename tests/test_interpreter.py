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
    game.__dict__["_GAC_Interpreter__parse_input"](it, sentence)
    return it.verb, it.noun1, it.noun2, it.adverb


def test_the_interpreter_here_knows_every_opcode():
    """The one that runs on this side has to keep up with the language.

    It is a big chain of names, so an opcode nobody added to it falls through
    to the end and prints INVALID OPCODE in the middle of somebody's
    adventure -- which is what MUSIC and SOUND did until this was written.
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


def cut(line, named=()):
    """One typed line into the orders it holds."""
    game = interpreter()
    it = object.__new__(game)
    it.separators = list(named)
    it.punctuation = list("\0 .,-!?:")
    return game.__dict__["_GAC_Interpreter__cut_into_orders"](it, line)


def test_a_mark_of_punctuation_parts_two_orders():
    assert cut("XYZY.SUR") == ["XYZY", "SUR"]


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
        test_a_sentence_fills_the_four_slots,
        test_the_second_noun_needs_a_first,
    ):
        check()
        print(f"{check.__name__}: correcto")
