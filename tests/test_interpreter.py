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


if __name__ == "__main__":
    for check in (
        test_the_start_of_a_word_is_enough,
        test_more_than_the_word_holds_matches_nothing,
        test_the_shortest_of_the_words_a_letter_starts,
        test_a_sentence_fills_the_four_slots,
        test_the_second_noun_needs_a_first,
    ):
        check()
        print(f"{check.__name__}: correcto")
