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
"""An adventure written in Spanish, with the letters Spanish is written in.

And where the shapes of those letters come from, which is either the
adventure's own typeface or nothing at all: an author writing one of these
rather than decompiling one hands over a font of their own, whole as a file or
a letter at a time, and whatever they drew is used as they drew it.

The character set never needed a special case for them -- a code is a code --
but two things did.  The shapes had to come from somewhere, because the font
an adventure inherits from 1986 has no accented letter in it; and the words
the parser matches had to lose their marks, because no keyboard here has a key
for one and a vocabulary that says ARAÑA could never be matched by anything a
player types.

Both are checked here, and then the whole of it on a real Spectrum: an
adventure whose messages are full of accents is printed by the Z80 and read
back off the screen through its own font, which only comes out right if the
codes, the glyphs, the packing and the printing all agree.
"""

import json
import os
import subprocess
import sys
import textwrap

try:
    import pytest
except ImportError:
    pytest = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import emulator  # noqa: E402
from regac.binary import BuildError, Database, Reader, S_FONT  # noqa: E402
from regac.glyphs import glyph_for  # noqa: E402
from regac.srcparse import SourceError, parse  # noqa: E402
from regac.text import typed  # noqa: E402
from test_spectrum import decode_screen, glyph_table, wrapped  # noqa: E402

SPECTRUM = os.path.join(ROOT, "z80", "spectrum")
SOURCE = os.path.join(SPECTRUM, "main.asm")
DATABASE = os.path.join(SPECTRUM, "game.rgac")
SNAPSHOT = os.path.join(SPECTRUM, "out.sna")
ADVENTURE = os.path.join(ROOT, "snapshots", "megacorp2.json")

TEXT_THIRD = 0x5000
MESSAGES_PRINTED = 6

SPANISH = [
    "¿Qué año es? Pregúntaselo a la araña.",
    "Está en el salón pequeño, al día.",
    "La señora Muñoz te miró con desdén.",
    "Ahí no hay más que telarañas y polvo.",
    "Una habitación diminuta y fría.",
    "Ñandú, cigüeña, cañón: ¡vaya bicho!",
]

if pytest is not None:
    needs_tools = pytest.mark.skipif(
        not emulator.available() or not os.path.exists(ADVENTURE),
        reason="sjasmplus and ZEsarUX must be in tools/, with a decompiled adventure",
    )
else:

    def needs_tools(func):
        return func


def a_font():
    """A font to build the letters out of: the one Megacorp carries."""
    with open(ADVENTURE, encoding="utf-8") as f:
        return json.load(f)["font"]


def adventure(messages, nouns=None):
    """The smallest adventure that can hold a few messages and a word."""
    return {
        "font": a_font(),
        "verbs": {"MIRAR": 1},
        "nouns": nouns if nouns is not None else {},
        "adverbs": {}, "pronouns": [],
        "messages": {str(n + 1): text for n, text in enumerate(messages)},
        "objects": {}, "locations": {},
        "hpcs": [], "lpcs": [], "lcs": {}, "model": "48K",
        "punctuation": list("\0 .,-!?:"), "separators": [],
        "init_loc": 1, "no_objs_msg": "nada", "gfx": {},
    }


def rows(glyph):
    return [f"{row:08b}" for row in glyph]


def test_an_accent_is_the_letter_with_a_mark_on_it():
    """A small letter has two rows free above it and takes the whole mark; a
    capital has none, so it is moved down into the row below and takes the
    body of it.  Either way the letter itself is the adventure's own."""
    font = a_font()
    small, capital = glyph_for("a", font), glyph_for("A", font)
    assert glyph_for("á", font)[2:] == small[2:], "the letter under it changed"
    assert any(glyph_for("á", font)[:2]), "nothing was put above it"
    assert glyph_for("Á", font)[1:] == capital[:7], "the capital did not move down"
    assert glyph_for("Á", font)[0], "nothing was put above the capital"
    # and the two marks Spanish has that are not accents
    assert glyph_for("¿", font) != glyph_for("?", font)
    assert glyph_for("¡", font) != glyph_for("!", font)
    assert any(glyph_for("¿", font)), "the inverted question mark is blank"


def test_a_letter_nothing_can_be_built_from_is_left_alone():
    """Better a blank than a wrong shape: a character with no letter under it
    and no mark this knows comes back as nothing at all."""
    assert glyph_for("中", a_font()) is None          # a Chinese character
    assert glyph_for("Ж", a_font()) is None          # and a Cyrillic one


def test_every_letter_of_an_accented_adventure_has_a_shape():
    built = Database(adventure(SPANISH))
    font = Reader(built.build()).section(S_FONT)
    blank = []
    for index, char in enumerate(built.store.charset.order):
        if char is None or char == " ":         # a hole, and the space
            continue
        if not any(font[2 + index * 8 : 10 + index * 8]):
            blank.append(char)
    assert not blank, f"nothing to draw {blank} with"


def test_a_word_is_stored_as_a_player_can_type_it():
    built = Database(adventure(SPANISH, nouns={"ARAÑA": 5, "CIGÜEÑA": 6}))
    chars = built.store.charset.chars
    words = {
        "".join(chars[code] for code in word)
        for _, _, word in Reader(built.build()).vocabulary()
    }
    assert "ARANA" in words and "ARAÑA" not in words
    assert "CIGUENA" in words


def test_two_words_that_would_be_typed_the_same_are_refused():
    """PEÑA and PENA are one word to a player, so the build says so rather
    than letting the second one never be reached."""
    with pytest.raises(BuildError) as complaint:
        Database(adventure(SPANISH, nouns={"PEÑA": 5, "PENA": 6})).build()
    assert "PENA" in str(complaint.value)


def test_the_marks_come_off_the_words_and_off_nothing_else():
    assert typed("ARAÑA") == "ARANA"
    assert typed("cigüeña") == "cigueña".replace("ñ", "n")
    assert typed("¿Qué?") == "¿Que?", "only the marks come off, not the letters"


SOURCE_WITH_A_FONT = """/CTL
model    SPECTRUM
start    1
width    32
punct    "\0" " " "." "," "-" "!" "?" ":"
nothing  "nada"

/VOC
MIRAR 1 verb

/MSG
#1
Añoranza

/FONT chars=128 file="letras.bin" first=32
{entries}
"""


def a_source(tmp_path, entries="", font=None):
    """A source with a font of its own beside it, as an author would have.

    The file is a plain dump from the space upwards, 768 bytes of it, which is
    the shape every font editor for these machines writes and the shape the
    ROM of one is in.
    """
    dump = bytes(a_font()[32 * 8:])
    (tmp_path / "letras.bin").write_bytes(font if font is not None else dump)
    text = SOURCE_WITH_A_FONT.format(entries=entries)
    (tmp_path / "juego.gac").write_text(text, encoding="utf-8")
    return text


def test_a_font_of_the_authors_own_comes_out_of_a_file(tmp_path):
    """Eight bytes a character from `first` upwards, which is what a font
    editor for one of these machines writes."""
    text = a_source(tmp_path)
    ddb = parse(text, "juego.gac", str(tmp_path))
    theirs = bytes(a_font()[65 * 8:66 * 8])
    assert bytes(ddb["font"][65 * 8:66 * 8]) == theirs, (
        "the A is not the one in the file"
    )
    assert glyph_for("Á", ddb["font"])[1:] == theirs[:7], (
        "the accented one was not built out of it"
    )
    assert glyph_for("Á", ddb["font"])[0], "and nothing was put above it"


def test_a_letter_the_author_drew_is_used_as_they_drew_it(tmp_path):
    """Nothing is composed on top of a glyph somebody drew, and the table
    reaches it without having to be declared twice."""
    drawn = "18 00 7E 63 63 63 63 00"
    text = a_source(tmp_path, entries=f'#"Ñ"  {drawn}')
    ddb = parse(text, "juego.gac", str(tmp_path))
    assert glyph_for("Ñ", ddb["font"]) == bytes(int(b, 16) for b in drawn.split())
    assert len(ddb["font"]) >= 0xD2 * 8, "the table did not reach it"
    # and the one they did not draw is still built for them
    assert glyph_for("ñ", ddb["font"]) is not None


def test_a_font_by_number_and_a_font_by_letter_are_the_same(tmp_path):
    drawn = "18 00 7E 63 63 63 63 00"
    by_letter = parse(a_source(tmp_path, f'#"Ñ"  {drawn}'), "x", str(tmp_path))
    by_number = parse(a_source(tmp_path, f"#209  {drawn}"), "x", str(tmp_path))
    assert by_letter["font"] == by_number["font"]


def test_a_font_that_is_not_whole_characters_is_refused(tmp_path):
    text = a_source(tmp_path, font=bytes(100))
    with pytest.raises(SourceError) as complaint:
        parse(text, "juego.gac", str(tmp_path))
    assert "eight bytes a character" in str(complaint.value)


def test_a_font_that_is_not_there_says_so(tmp_path):
    text = SOURCE_WITH_A_FONT.format(entries="")
    with pytest.raises(SourceError) as complaint:
        parse(text, "juego.gac", str(tmp_path))
    assert "letras.bin" in str(complaint.value)


@needs_tools
def test_a_spectrum_prints_the_letters_spanish_is_written_in():
    ddb = adventure(SPANISH)
    with open(DATABASE, "wb") as f:
        f.write(Database(ddb).build())
    listing = emulator.assemble(SOURCE)
    finished, (memory,) = emulator.run(SNAPSHOT, listing, reads=[(TEXT_THIRD, 2048)])
    assert finished, "the interpreter never reached the end of its run"

    database = Database(ddb)
    lines = decode_screen(memory, glyph_table(database))
    expected = wrapped(SPANISH[:MESSAGES_PRINTED])
    visible = [line for line in lines if line]
    assert visible == expected[-len(visible):]
    assert any("ñ" in line or "é" in line or "¿" in line for line in visible), (
        "nothing accented reached the screen"
    )


if __name__ == "__main__":
    test_an_accent_is_the_letter_with_a_mark_on_it()
    test_every_letter_of_an_accented_adventure_has_a_shape()
    test_a_word_is_stored_as_a_player_can_type_it()
    print("the letters are there and the words can be typed")
    test_a_spectrum_prints_the_letters_spanish_is_written_in()
    print("and a Spectrum prints them")
