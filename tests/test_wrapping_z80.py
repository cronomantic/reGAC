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
"""Where the lines break, which is the author's business and not ours.

The original's text is words with a terminator of three bits each, and it
prints them one at a time, so a mark of punctuation ends a word as surely as
a space does.  Ours broke only at spaces, and that is not a nicety: MegaCorp
writes its rooms as `La cabina de la nave. Salidas:Sur.` followed by a rule
of thirty two asterisks, counted to fill a line exactly.  Broken only at
spaces that is one word of forty four letters, and it came out as two ragged
lines instead of the three its author laid out.

What the original does, on the machine:

    La cabina de la nave. Salidas:
    Sur.
    ********************************
    >>>

Note the prompt straight after the rule, with no blank line between: a line
that has just filled itself is not ended again.
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
from test_markers_z80 import adventure, played  # noqa: E402

RULE = "*" * 32                 # a line of the screen, exactly

if pytest is not None:
    needs_tools = pytest.mark.skipif(
        not emulator.available(), reason="sjasmplus and ZEsarUX must be in tools/"
    )
else:

    def needs_tools(func):
        return func


def room_saying(description):
    return adventure(rooms={
        "1": {"graphic_id": 0, "exits": [], "desc": description},
    })


def laid_out(description):
    """The lines of the screen, with the part nothing was written on taken
    off: a cell nobody has touched reads back as no letter at all."""
    out = []
    for line in played(room_saying(description)):
        out.append(line.replace("?", " ").rstrip())
    return [line for line in out if line]


@needs_tools
def test_a_mark_of_punctuation_ends_a_word():
    """MegaCorp's own shape, written the way MegaCorp writes it."""
    lines = laid_out("LA CABINA DE LA NAVE. SALIDAS:SUR." + RULE)
    assert lines[:3] == ["LA CABINA DE LA NAVE. SALIDAS:", "SUR.", RULE], (
        f"the lines came out as {lines}"
    )


@needs_tools
def test_a_space_after_a_mark_goes_down_with_the_word():
    """MegaCorp's second room, which the original shows with the space after
    the full stop at the start of the new line: that space follows another
    separator, and the original's $778A breaks at the first of the two.  A
    space that ends a word stays where it is: see doc/pendiente.md."""
    lines = laid_out("LA BODEGA DE CARGA DE LA NAVE. SALIDAS:NORTE." + RULE)
    assert lines[:3] == ["LA BODEGA DE CARGA DE LA NAVE.", " SALIDAS:NORTE.",
                         RULE], f"the lines came out as {lines}"


@needs_tools
def test_a_line_that_fills_itself_is_not_ended_again():
    """The prompt comes on the line straight after the rule."""
    lines = laid_out("UN CUARTO." + RULE)
    assert lines[:2] == ["UN CUARTO.", RULE], (
        f"the rule did not go whole onto its own line: {lines}"
    )
    lines = laid_out(RULE)
    assert lines[0] == RULE, f"the rule is not the first line: {lines}"
    assert lines[1].startswith(">"), (
        f"a blank line was left between a full line and the prompt: {lines}"
    )


@needs_tools
def test_a_word_is_still_never_split():
    """Breaking at marks must not lose what it was for: a word that does not
    fit goes whole onto the next line."""
    lines = laid_out("AAAA BBBBBBBBBBBBBBBBBBBBBBBBBBBBBB CC")
    assert lines[0] == "AAAA", f"the long word was split: {lines}"
    assert lines[1].startswith("BBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"), (
        f"the long word did not go whole onto its own line: {lines}"
    )


@needs_tools
def test_a_text_longer_than_any_buffer_prints_whole():
    """A text is printed while it is unpacked, a word at a time, so it may be
    as long as it likes.  It used to be unpacked whole into a buffer of 256
    bytes and printed afterwards, and a longer one ran off the end of the
    buffer and over the code behind it.  No original adventure does that --
    GAC's editor would not let a text of more than 255 characters be typed,
    its line reader beeps at the next one -- but a source of ours can.

    This one is six hundred odd characters, with a word in it longer than the
    line: that one cannot be held whole, and goes out in pieces that must land
    exactly where the whole of it would have.  What is on the screen before
    the prompt has to be the end of what it should come to, and the prompt has
    to be there at all, which it was not while the text was trampling code."""
    words = ["PALABRA" if n % 3 else "OTRA." for n in range(90)]
    words.insert(84, "X" * 45)                  # near the end, so it is on the screen
    text = " ".join(words)
    assert len(text) > 600
    lines = laid_out(text)
    prompts = [n for n, line in enumerate(lines) if line.startswith(">")]
    assert prompts, f"no prompt after the long text; the screen was {lines}"
    shown = lines[:prompts[-1]]
    want = emulator.wrapped([text], 32)
    assert shown and want[-len(shown):] == shown, (
        f"the long text came out as {shown}, not as the end of {want}"
    )


if __name__ == "__main__":
    test_a_mark_of_punctuation_ends_a_word()
    test_a_line_that_fills_itself_is_not_ended_again()
    test_a_word_is_still_never_split()
    test_a_text_longer_than_any_buffer_prints_whole()
    print("the lines break where the author meant them to")
