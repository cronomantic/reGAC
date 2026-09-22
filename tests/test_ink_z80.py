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
r"""A message that changes ink half way through, printed on a real Spectrum.

`\ink 2` inside the text of a message is two codes by the time it reaches the
machine -- the one code the character set keeps for a change of ink, and then
the colour as a printable character -- and the printing obeys it and shows
neither.  Here a message says three words in three colours, and what is read
back is the screen: the letters, so that nothing of the command was printed
and nothing of the text was eaten, and the attribute of every cell under them,
so that each word came out in the colour it asked for.

The last of the three asks for a bright colour, which on this machine is a bit
of the attribute and not a colour of its own.
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
from test_conditions_z80 import DATABASE, SOURCE, adventure  # noqa: E402
from test_game_z80 import glyph_table  # noqa: E402

SPECTRUM = os.path.join(ROOT, "z80", "spectrum")
SNAPSHOT = os.path.join(SPECTRUM, "conditions.sna")
LISTING = os.path.join(SPECTRUM, "conditions.lst")

TEXT_THIRD = 0x5000             # where the eight rows of text are
ATTRIBUTES = 0x5A00             # and their attributes
ROWS = 8
COLUMNS = 32

WHITE = 7                       # what the window is cleared to
BRIGHT = 0x40

MESSAGE = r"uno \ink 2 dos \ink 12 tres"
WANTED = {"uno": WHITE, "dos": 2, "tres": BRIGHT | 4}

# And the pair that says how far a change of ink reaches: one message that
# turns the text red and never turns it back, and another behind it.
LEAKY = r"rojo \ink 2 rojo"
AFTER = "blanco"

if pytest is not None:
    needs_tools = pytest.mark.skipif(
        not emulator.available(), reason="sjasmplus and ZEsarUX must be in tools/"
    )
else:

    def needs_tools(func):
        return func


def printed(bitmap, attributes, glyphs):
    """The window as pairs of letter and attribute, row by row."""
    rows = []
    for row in range(ROWS):
        line = []
        for column in range(COLUMNS):
            cell = bytes(bitmap[page * 256 + row * 32 + column]
                         for page in range(8))
            # Nothing at all is a cell nothing was printed in: the font this
            # is read with draws even a space, on purpose.
            char = " " if not any(cell) else glyphs.get(cell, "?")
            line.append((char, attributes[row * 32 + column]))
        rows.append(line)
    return rows


def lettered():
    """A font where every character draws something of its own, so that a cell
    of the screen can be read back as the letter that put it there.  The small
    adventure the conditions are run in has a blank one, which is no use when
    what is being looked at is the printing itself."""
    return [code if code >= 32 else 0 for code in range(128) for _ in range(8)]


@needs_tools
def test_a_message_says_its_words_in_three_colours():
    ddb = adventure(["MESS 1 END"])
    ddb["messages"]["1"] = MESSAGE
    ddb["font"] = lettered()
    database = Database(ddb)
    with open(DATABASE, "wb") as f:
        f.write(database.build())
    listing = emulator.assemble(SOURCE, listing=LISTING)
    glyphs = glyph_table(database)

    finished, (bitmap, attributes) = emulator.run(
        SNAPSHOT, listing,
        reads=[(TEXT_THIRD, 2048), (ATTRIBUTES, 256)],
    )
    assert finished, "the conditions never reached the end"

    rows = printed(bitmap, attributes, glyphs)
    line = "".join(char for char, _ in rows[0]).rstrip()
    assert line == "uno dos tres", (
        f"the command was printed or the text was eaten: {line!r}"
    )

    # Every letter of every word, against the colour that word asked for.
    at = 0
    for word, colour in WANTED.items():
        at = line.index(word, at)
        for offset in range(len(word)):
            char, attribute = rows[0][at + offset]
            assert attribute == colour, (
                f"{char!r} of {word!r} came out in {attribute:#04x} and not"
                f" {colour:#04x}"
            )
        at += len(word)

    # And the space between two words keeps the ink of what came before it,
    # which is what any machine of this kind does.
    assert rows[0][3][1] == WHITE


@needs_tools
def test_a_change_of_ink_dies_with_its_own_message():
    """Which is the whole of the rule, and it used not to be.

    A change of ink lasted until the next one, and there need never be a next
    one: a message that turned the text red and did not turn it back left the
    next room red, and the prompt, and what the parser says when it does not
    understand.  The damage showed up a long way from the line that caused
    it, and the author could not see it while writing that line.

    So here the first message ends red on purpose and the second says nothing
    about colour at all.  The second has to come out white.
    """
    ddb = adventure(["MESS 1 MESS 2 END"])
    ddb["messages"]["1"] = LEAKY
    ddb["messages"]["2"] = AFTER
    ddb["font"] = lettered()
    database = Database(ddb)
    with open(DATABASE, "wb") as f:
        f.write(database.build())
    listing = emulator.assemble(SOURCE, listing=LISTING)
    glyphs = glyph_table(database)

    finished, (bitmap, attributes) = emulator.run(
        SNAPSHOT, listing,
        reads=[(TEXT_THIRD, 2048), (ATTRIBUTES, 256)],
    )
    assert finished, "the conditions never reached the end"

    rows = printed(bitmap, attributes, glyphs)
    line = "".join(char for char, _ in rows[0]).rstrip()
    assert AFTER in line, f"the second message never came out: {line!r}"
    at = line.index(AFTER)
    for offset, char in enumerate(AFTER):
        _, attribute = rows[0][at + offset]
        assert attribute == WHITE, (
            f"{char!r} of the message behind came out in {attribute:#04x} and"
            f" not {WHITE:#04x}: the red of the one before it reached past its"
            f" own end -- {line!r}"
        )


CHOSEN = 4                      # green, which is not what any machine starts in


@needs_tools
def test_an_adventure_may_choose_the_ink_of_all_its_text():
    """Because a change of ink now dies with its message, there had to be
    somewhere to say it once.

    It used to be possible by accident: an ink set in the first message stuck
    for ever, because nothing put it back.  That was the fault this rule
    fixed, and fixing it took the only way there was of colouring a whole
    adventure -- so `/CTL ink` says it properly, and each message goes back to
    that and not to the white the interpreter was assembled with.
    """
    ddb = adventure(["MESS 1 MESS 2 END"])
    ddb["ink"] = CHOSEN
    ddb["messages"]["1"] = LEAKY        # changes the ink and does not put it back
    ddb["messages"]["2"] = AFTER
    ddb["font"] = lettered()
    database = Database(ddb)
    with open(DATABASE, "wb") as f:
        f.write(database.build())
    listing = emulator.assemble(SOURCE, listing=LISTING)
    glyphs = glyph_table(database)

    finished, (bitmap, attributes) = emulator.run(
        SNAPSHOT, listing,
        reads=[(TEXT_THIRD, 2048), (ATTRIBUTES, 256)],
    )
    assert finished, "the conditions never reached the end"

    rows = printed(bitmap, attributes, glyphs)
    line = "".join(char for char, _ in rows[0]).rstrip()
    assert AFTER in line, f"the second message never came out: {line!r}"
    at = line.index(AFTER)
    for offset, char in enumerate(AFTER):
        _, attribute = rows[0][at + offset]
        assert attribute == CHOSEN, (
            f"{char!r} came out in {attribute:#04x} and not {CHOSEN:#04x}: the"
            f" adventure asked for its own ink and got the machine's -- {line!r}"
        )
    # And the first message still says what it asked for, over the top of it.
    assert rows[0][0][1] == CHOSEN, "the text before the change is not the chosen ink"


if __name__ == "__main__":
    test_a_message_says_its_words_in_three_colours()
    print("a message says its words in three colours")
    test_a_change_of_ink_dies_with_its_own_message()
    print("a change of ink dies with its own message")
    test_an_adventure_may_choose_the_ink_of_all_its_text()
    print("an adventure may choose the ink of all its text")
