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


if __name__ == "__main__":
    test_a_message_says_its_words_in_three_colours()
    print("a message says its words in three colours")
