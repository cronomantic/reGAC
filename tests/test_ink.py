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
r"""A change of ink, from the source to the codes it travels as.

`\ink 5` is written inside the text of a message, because what is red is a
word of a sentence and not a property of the whole message.  What it becomes
is two codes: the one the character set keeps for a change of ink, and the
colour as a printable character -- so that the compressor pairs it like
anything else, and so that no colour can ever be the null that ends a string.

What is checked here is the whole of the Python side of it: the writing, the
reading, what the codes come out as, that the font does not grow a glyph for a
command it will never draw, and that a message with a colour in it survives
being written to a source and read back.
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

from regac.binary import Database  # noqa: E402
from regac.srcgen import generate  # noqa: E402
from regac.srcparse import parse  # noqa: E402
from regac.text import (INK_ARG_FIRST, INK_CHAR, INK_CODE,  # noqa: E402
                        TextStore, expand, plain, written)
from test_conditions_z80 import adventure  # noqa: E402

MESSAGE = r"uno \ink 2 dos \ink 12 tres"


def test_what_a_command_becomes():
    codes = expand(MESSAGE)
    assert codes == f"uno {INK_CHAR}2dos {INK_CHAR}<tres", repr(codes)
    assert ord("<") - INK_ARG_FIRST == 12, "twelve rides as the twelfth character"


def test_the_space_after_a_command_is_eaten():
    """Or `rojo \\ink 2 y negro` would come out with two spaces in it, which is
    what a command of this kind does in every other language too."""
    assert plain(expand(r"rojo \ink 2 y negro")) == "rojo y negro"
    assert plain(expand(r"rojo\ink 2 y negro")) == "rojoy negro"


def test_a_backslash_of_its_own():
    assert plain(expand(r"dos \\ barras")) == r"dos \ barras"


def test_it_is_written_back_as_it_was_written():
    assert written(expand(MESSAGE)) == MESSAGE


def test_a_colour_there_is_not_is_refused():
    for bad in (r"\ink 16", r"\ink 99"):
        with_error = None
        try:
            expand(bad)
        except ValueError as e:
            with_error = str(e)
        assert with_error and "colour" in with_error, bad
    try:
        expand(r"\music 2")
    except ValueError as e:
        assert "not a text command" in str(e)
    else:
        raise AssertionError("an unknown command should be refused")


def test_the_codes_it_travels_as():
    store = TextStore([MESSAGE])
    codes = list(store.packer.unpack(store.messages[0]))
    assert codes.count(INK_CODE) == 2, codes
    at = codes.index(INK_CODE)
    assert codes[at + 1] == INK_ARG_FIRST + 2
    assert INK_CODE not in codes[:4], "nothing before the first word"


def test_the_font_grows_no_glyph_for_it():
    """A change of ink has a code like a letter, so that the compressor can
    pair it, but it is never drawn -- and if it counted as a letter it would
    drag the run of glyphs down to code one and carry thirty blanks."""
    plain_store = TextStore(["uno dos tres"])
    inked = TextStore([MESSAGE])
    assert inked.charset.first == plain_store.charset.first
    assert inked.charset.first >= 32


def test_a_message_with_a_colour_goes_to_a_source_and_back():
    ddb = adventure([])
    ddb["messages"]["1"] = MESSAGE
    again = parse(generate(ddb))
    # What comes back from a source numbers its messages, where the JSON of a
    # decompiled adventure names them; either way it is message one.
    assert again["messages"][1] == MESSAGE


def test_an_adventure_with_one_builds():
    ddb = adventure([])
    ddb["messages"]["1"] = MESSAGE
    image = Database(ddb).build()
    assert image[:4] == b"RGAC"


if __name__ == "__main__":
    for name, test in sorted(globals().items()):
        if name.startswith("test_"):
            test()
            print(name[5:].replace("_", " "))
