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
from regac import fontfile, png  # noqa: E402
from regac.srcparse import SourceError, parse  # noqa: E402
from regac.text import SPECIALS, typed  # noqa: E402
from test_spectrum import COLUMNS, decode_screen, glyph_table  # noqa: E402

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
    """A font to build the letters out of: the example's, which is in the
    repository.  It was MegaCorp's, which is not, and every test here that
    has nothing to do with MegaCorp failed where the originals are not."""
    from regac.viewer import read_adventure

    return read_adventure(os.path.join(ROOT, "ejemplo", "faro.gac"),
                          "spectrum")["font"]


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


def test_every_letter_of_the_set_can_be_drawn():
    """The set promises thirty letters below the space, so all thirty have to
    come out of an ordinary alphabet one way or another: with a mark on them,
    turned over, stretched, or drawn here because nothing else would do."""
    font = a_font()
    blank = [c for c in SPECIALS if glyph_for(c, font) is None]
    assert not blank, f"nothing to draw {blank} with"


def test_a_dash_is_the_hyphen_of_the_typeface_it_stands_in():
    """As wide as the cell, so that two of them join up, and at the height
    that typeface puts its hyphen."""
    font = a_font()
    hyphen, dash = glyph_for("-", font), glyph_for("—", font)
    assert [bool(row) for row in dash] == [bool(row) for row in hyphen]
    assert all(row in (0, 0xFF) for row in dash), "it does not reach both edges"


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
    assert "eight bytes a letter" in str(complaint.value)


def test_a_font_of_a_size_nobody_uses_asks_where_it_starts(tmp_path):
    """Sizes this knows say where their first letter is; anything else has to
    be told, and is told so."""
    text = a_source(tmp_path, font=bytes(8 * 40)).replace(" first=32", "")
    with pytest.raises(SourceError) as complaint:
        parse(text, "juego.gac", str(tmp_path))
    assert "first=" in str(complaint.value)


def test_the_shapes_a_font_file_can_come_in(tmp_path):
    """A dump of the ninety six from the space up, the same with a load
    address in front of it, the same behind an AMSDOS header, and a console
    font: all of them the same letters in the end."""
    plain = bytes(a_font()[32 * 8:])
    wanted = fontfile.read(str(tmp_path / "plain.bin")) if False else None
    for name, blob, first in (
        ("plain.bin", plain, None),
        ("charset.64c", bytes([0x00, 0x20]) + plain, None),
        ("font.bin", bytes(128) + plain, None),            # AMSDOS and +3DOS
        ("console.psf", bytes([0x36, 0x04, 0x00, 0x08]) + plain, 32),
    ):
        (tmp_path / name).write_bytes(blob)
        glyphs = fontfile.read(str(tmp_path / name), first)
        assert glyphs[65] == bytes(a_font()[65 * 8:66 * 8]), f"{name} lost its A"


def a_listing(dump, kind):
    """The same font written out as source, in the dialects the collections
    publish: a C header and four assemblers."""
    rows = [dump[n:n + 8] for n in range(0, len(dump), 8)]
    if kind == "c":
        body = ",\n  ".join(", ".join(f"0x{b:02X}" for b in row) for row in rows)
        return f"/* Aardvark */\nconst unsigned char font[{len(dump)}] = {{\n  {body}\n}};\n"
    if kind == "z80":
        lines = "\n".join("    defb " + ", ".join(f"${b:02X}" for b in row)
                          for row in rows)
        return f"; Aardvark\n    org 0x8000\nfont:\n{lines}\n"
    if kind == "6502":
        lines = "\n".join("    .byte " + ",".join(f"${b:02X}" for b in row)
                          for row in rows)
        return f"; Aardvark\n{lines}\n"
    if kind == "x86":
        lines = "\n".join("    db " + ", ".join(f"{b:02X}h" for b in row)
                          for row in rows)
        return f"; Aardvark\n{lines}\n"
    if kind == "68000":
        lines = "\n".join("    dc.b " + ",".join(f"${b:02X}" for b in row)
                          for row in rows)
        return f"* Aardvark\n{lines}\n"
    if kind == "binary":
        return "\n".join("    defb " + ", ".join(f"%{b:08b}" for b in row)
                          for row in rows) + "\n"
    raise AssertionError(kind)


@pytest.mark.parametrize("kind", ["c", "z80", "6502", "x86", "68000", "binary"])
def test_a_font_written_out_as_source(tmp_path, kind):
    """The collections publish the same font half a dozen ways: a heap of
    numbers with something different around it.  What is taken is what is
    inside the braces, or what stands on the lines that carry a byte
    directive, which is what keeps the length out of `font[768]` and the
    address out of an `org`."""
    dump = bytes(a_font()[32 * 8:])
    (tmp_path / f"font.{kind}").write_text(a_listing(dump, kind), encoding="utf-8")
    glyphs = fontfile.read(str(tmp_path / f"font.{kind}"))
    assert len(glyphs) == 96, "a 768 byte font is the ninety six from the space up"
    assert glyphs[65] == bytes(a_font()[65 * 8:66 * 8]), "the A came out wrong"


def test_a_listing_whose_comments_hold_braces(tmp_path):
    """The one the real files caught.  These listings put the letter each row
    draws in a comment at the end of it, so the line for the open brace has an
    open brace in it -- and looking for the braces of a C array without taking
    the comments out first finds that one and reads eight bytes."""
    dump = bytes(a_font()[32 * 8:])
    lines = []
    for n in range(0, len(dump), 8):
        letter = chr(32 + n // 8)
        row = ", ".join(f"&{b:02X}" for b in dump[n:n + 8])
        lines.append(f"\tdefb {row} ; {letter}")
    body = "\t; Envious font, \u00a9 somebody\n" + "\n".join(lines) + "\n"
    (tmp_path / "font.z80.asm").write_text(body, encoding="utf-8")
    glyphs = fontfile.read(str(tmp_path / "font.z80.asm"))
    assert len(glyphs) == 96, "the braces in the comments were taken for the font's"
    assert glyphs[65] == bytes(a_font()[65 * 8:66 * 8])


def test_a_bdf_says_what_each_glyph_is(tmp_path):
    """The format that needs no layout at all: every glyph carries its own
    number, so a font of letters in no order reads as easily as a run."""
    font = a_font()
    wanted = {0x41: font[0x41 * 8:0x42 * 8], 0xD1: glyph_for("Ñ", font)}
    body = ["STARTFONT 2.1", "FONT Prueba", "SIZE 8 75 75",
            "FONTBOUNDINGBOX 8 8 0 -1", f"CHARS {len(wanted)}"]
    for code, glyph in wanted.items():
        body += [f"STARTCHAR C{code:04X}", f"ENCODING {code}",
                 "DWIDTH 8 0", "BBX 8 8 0 -1", "BITMAP"]
        body += [f"{row:02X}" for row in glyph]
        body.append("ENDCHAR")
    body.append("ENDFONT")
    (tmp_path / "font.bdf").write_text("\n".join(body) + "\n", encoding="utf-8")
    glyphs = fontfile.read(str(tmp_path / "font.bdf"))
    assert glyphs == {code: bytes(glyph) for code, glyph in wanted.items()}


def test_a_stream_of_vdu_commands(tmp_path):
    """How a BBC Micro is told to redefine a character, and how that machine's
    file in these collections is written: the twenty three, the character, its
    eight rows, and again."""
    font = a_font()
    blob = bytearray()
    for code in (65, 66):
        blob += bytes([23, code]) + bytes(font[code * 8:code * 8 + 8])
    (tmp_path / "font.bbc").write_bytes(bytes(blob))
    glyphs = fontfile.read(str(tmp_path / "font.bbc"))
    assert glyphs[65] == bytes(font[65 * 8:66 * 8])
    assert set(glyphs) == {65, 66}


def test_a_basic_listing_that_redefines_characters(tmp_path):
    """The Amstrad's, which is what its file in these collections is: a line
    number, SYMBOL, the character and its eight rows."""
    font = a_font()
    lines = ["9000 REM Prueba", "9020 SYMBOL AFTER 33"]
    drawn = {65: bytes(font[65 * 8:66 * 8]), 193: glyph_for("Á", font)}
    for n, (code, glyph) in enumerate(drawn.items()):
        rows = ",".join(str(b) for b in glyph)
        lines.append(f"{9030 + n * 10} SYMBOL {code},{rows}")
    (tmp_path / "font.bas").write_text("\n".join(lines) + "\n", encoding="utf-8")
    glyphs = fontfile.read(str(tmp_path / "font.bas"))
    assert glyphs[65] == drawn[65], "the line numbers got in"
    assert glyphs[193] == drawn[193]


def test_a_console_font_with_a_table_of_meanings_behind_it(tmp_path):
    """A PSF carries a table saying what each glyph means, after the glyphs.
    It is not glyphs, and taking it for some was what made a real one come out
    as not a whole number of letters."""
    dump = bytes(a_font()[32 * 8:])
    glyphs = len(dump) // 8
    header = (bytes([0x72, 0xb5, 0x4a, 0x86]) + (0).to_bytes(4, "little")
              + (32).to_bytes(4, "little") + (1).to_bytes(4, "little")
              + glyphs.to_bytes(4, "little") + (8).to_bytes(4, "little")
              + (8).to_bytes(4, "little") + (8).to_bytes(4, "little"))
    table = b"".join(bytes([32 + n]) + b"\xff" for n in range(glyphs))
    (tmp_path / "font.psf").write_bytes(header + dump + table)
    read = fontfile.read(str(tmp_path / "font.psf"))
    assert len(read) == glyphs
    assert read[65 - 32] == bytes(a_font()[65 * 8:66 * 8])


def test_something_that_is_not_a_font_at_all(tmp_path):
    (tmp_path / "notes.txt").write_text(
        "Este fichero no tiene nada dentro que sea una fuente.\n", encoding="utf-8")
    with pytest.raises(fontfile.FontError):
        fontfile.read(str(tmp_path / "notes.txt"))


def test_a_font_kept_in_another_machines_order(tmp_path):
    """A C64 keeps @ABC... at nought, so slot one is the A and slot two the
    B; what comes out has them where ASCII has them."""
    glyphs = [bytes([code] * 8) for code in range(64)]
    (tmp_path / "c64.bin").write_bytes(b"".join(glyphs))
    read = fontfile.read(str(tmp_path / "c64.bin"), first=0, order="c64")
    assert read[ord("A")] == glyphs[1]
    assert read[ord("0")] == glyphs[48]


def draw_sheet(path, glyphs, cells, across, scale=1):
    """A sheet of letters: cells left to right and top to bottom, ink black,
    and `scale` pixels to a pixel because a person draws one big."""
    down = (cells + across - 1) // across
    rows = []
    for line in range(down * 8):
        cell_row, in_cell = divmod(line, 8)
        row = []
        for column in range(across):
            glyph = glyphs.get(cell_row * across + column, bytes(8))
            row += [(0, 0, 0) if glyph[in_cell] & (0x80 >> bit) else (255, 255, 255)
                    for bit in range(8)]
        rows.append(row)
    png.write(str(path), rows, scale)


def latin1_sheet(tmp_path, scale=1, name="hoja.png"):
    """Every letter where Latin-1 keeps it, which is where an artist would
    draw it without ever hearing about the codes reGAC uses."""
    font = a_font()
    glyphs = {code: glyph_for(chr(code), font) for code in range(32, 256)
              if glyph_for(chr(code), font)}
    draw_sheet(tmp_path / name, glyphs, 256, 16, scale)
    return tmp_path / name


def test_a_letter_is_known_by_where_it_sits_on_the_sheet(tmp_path):
    """Which is why the layout is named: Latin-1 says the first cell is the
    null and the two hundred and tenth is the Ñ, and reGAC's own codes never
    come into it."""
    read = fontfile.read(str(latin1_sheet(tmp_path)), layout="latin1")
    font = a_font()
    for char in "AzÑáé¿ç":
        assert read[ord(char)] == glyph_for(char, font), f"{char} is not where it sat"


def test_a_sheet_drawn_larger_is_still_a_sheet(tmp_path):
    """Nobody draws at eight pixels to a letter.  Knowing how many cells there
    are supposed to be is what says a sheet is at three times the size rather
    than nine times as many letters."""
    big = latin1_sheet(tmp_path, scale=3)
    read = fontfile.read(str(big), layout="latin1")
    assert read[ord("Ñ")] == glyph_for("Ñ", a_font())
    # and without the layout it can only be read as what it looks like
    assert len(fontfile.read(str(big))) == 256 * 9


def test_a_sheet_that_is_not_the_shape_its_layout_says(tmp_path):
    sheet = latin1_sheet(tmp_path)
    with pytest.raises(fontfile.FontError) as complaint:
        fontfile.read(str(sheet), layout="ascii")
    assert "cells" in str(complaint.value)


def test_a_sheet_reaches_the_adventure(tmp_path):
    """The whole way: a sheet beside the source, and a letter of it in the
    font the machine is given."""
    latin1_sheet(tmp_path, name="letras.png")
    source = SOURCE_WITH_A_FONT.format(entries="").replace(
        'file="letras.bin" first=32', 'file="letras.png" layout=latin1')
    ddb = parse(source, "juego.gac", str(tmp_path))
    assert glyph_for("ñ", ddb["font"]) == glyph_for("ñ", a_font())
    assert Database(adventure(SPANISH))  # and it still builds


def test_a_sheet_of_letters_drawn_as_a_picture(tmp_path):
    """What an artist would rather hand over: the letters in a grid of eight
    by eight cells, ink darker than half."""
    letters = [a_font()[code * 8:code * 8 + 8] for code in range(32, 48)]
    rows = []
    for line in range(8):
        row = []
        for glyph in letters:
            row += [(0, 0, 0) if glyph[line] & (0x80 >> bit) else (255, 255, 255)
                    for bit in range(8)]
        rows.append(row)
    png.write(str(tmp_path / "hoja.png"), rows, 1)
    glyphs = fontfile.read(str(tmp_path / "hoja.png"), first=32)
    for code in range(32, 48):
        assert glyphs[code] == bytes(a_font()[code * 8:code * 8 + 8]), (
            f"the cell for {chr(code)!r} came back wrong"
        )


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
    expected = emulator.wrapped(SPANISH[:MESSAGES_PRINTED], COLUMNS)
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
