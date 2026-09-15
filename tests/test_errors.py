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
"""What the compiler says when the source is wrong.

An adventure is thousands of lines and its author is not a compiler writer, so
a mistake has to say four things: which file, which line, the line itself with
a finger under the word, and -- when the word is nearly right, which a typo
always is -- what it was probably meant to be.  The language is sixty seven
words long, so that last one is almost free and saves the hunt.

Every kind of mistake is checked in the same shape, because the shape is the
point: whatever reads it, a person or an editor, should find its way the same
way every time.
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

from regac.conds import CompileError, compile_line, nearest  # noqa: E402
from regac.srcparse import SourceError, parse  # noqa: E402

HEAD = "/CTL\nmodel SPECTRUM\n"


def broken(source, machine="cpc"):
    """The message a source of ours is refused with."""
    try:
        parse(HEAD + source, "partida.gac", machine=machine)
    except SourceError as e:
        return str(e)
    raise AssertionError(f"this should not have been read: {source!r}")


def finger(message):
    """Which column the message points at, counting from one."""
    lines = message.splitlines()
    assert len(lines) == 3, f"a mistake is three lines:\n{message}"
    return lines[2].index("^") - 4 + 1


def test_a_mistake_says_where_and_shows_it():
    said = broken("/HIGH\n    IF ( VERB 7 ) MESSS 14 END\n")
    first, shown, _ = said.splitlines()
    assert first.startswith("partida.gac:4: "), said
    assert shown.strip() == "IF ( VERB 7 ) MESSS 14 END", said
    assert finger(said) == 19, f"the finger is not under MESSS:\n{said}"


def test_a_typo_is_told_what_it_meant():
    for source, meant in (
        ("/HIGH\n IF ( VERB 7 ) MESSS 14 END\n", "MESS"),
        ("/MSGG\n#1\nhola\n", "/MSG"),
        ("/VOC\nNORTE   1  verbo\n", "verb"),
        ("/GFX\n#1\n  LINEA 1 2 3 4\n", "LINE"),
        ("/MSG\n#1\n.if cpcc\nhola\n.end\n", "cpc"),
    ):
        said = broken(source)
        assert f"did you mean {meant}?" in said, said


def test_a_word_that_is_nothing_like_one_gets_no_guess():
    """A guess at something that is not a near miss is noise, and worse: it
    sends the author looking at the wrong thing."""
    said = broken("/HIGH\n XYZZY 3 END\n")
    assert "did you mean" not in said, said
    said = broken("/MSG\n#1\n.if oric\nhola\n.end\n")
    assert "did you mean" not in said
    assert "what there is:" in said, "with no guess it should say what there is"


def test_the_line_is_the_author_s_and_not_the_compiler_s():
    """The compiler is handed the line with its comment cut off and its indent
    gone; what is shown has to be what is in the file, finger and all."""
    said = broken("/HIGH\n        IF ( VERB 7 ) MESSS 14 END   ; un comentario\n")
    shown = said.splitlines()[1]
    assert "; un comentario" in shown, said
    assert finger(said) == shown.index("MESSS") - 4 + 1, said


def test_what_is_wrong_in_a_picture_says_which_line_of_it():
    """A picture is read whole, so the count has to be kept as it goes: the
    mistake is on the third line of this one, not at the end of the entry."""
    said = broken("/GFX\n#1\n  LINE 1 2 3 4\n  RECT 1 2 3 4\n  FILL 1\n")
    assert said.startswith("partida.gac:7: "), said
    assert "FILL takes 2 numbers, and here it has 1" in said, said


def test_the_conditions_say_what_they_wanted():
    for source, wanted in (
        ("/HIGH\n IF ( VERB 7 MESS 14 END\n", "expected ')'"),
        ("/HIGH\n MESS\n", "stops in the middle"),
    ):
        said = broken(source)
        assert wanted in said, said


def test_the_compiler_on_its_own_says_where_too():
    """conds.py is used without a file around it -- by the tests, and by
    anything that compiles one line -- so it carries the column itself."""
    try:
        compile_line("IF ( VERB 7 ) MESSS 14 END")
    except CompileError as e:
        assert e.column == 15, e.column
        assert e.meant == "MESS"
        assert "did you mean MESS?" in str(e)
    else:
        raise AssertionError("that should not have compiled")


def test_the_guessing_is_not_case_bound():
    assert nearest("verbo", ("verb", "noun", "adverb")) == "verb"
    assert nearest("mess", ("MESS", "LOOK")) == "MESS"
    assert nearest("zzz", ("MESS", "LOOK")) is None


if __name__ == "__main__":
    for name, test in sorted(globals().items()):
        if name.startswith("test_"):
            test()
            print(name[5:].replace("_", " "))
