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
# The interpreters in z80/ are not part of this program and are given under
# the MIT licence instead: see z80/LICENSE.
#
"""Glyphs for the letters the original alphabet has not got.

An adventure written today says ARAÑA and PEQUEÑO and ¿QUÉ?, and the font it
inherits from 1986 has nothing to draw them with: the character set here gives
every one of those a code of its own -- that part never needed a special case
-- but eight bytes of shape had to come from somewhere, and until now they
came out blank.

They are not drawn by hand.  A letter with an accent is the adventure's own
letter with a mark on top of it, so that it looks like the rest of the
typeface whichever typeface that is, and the mark is the only thing this file
holds.  Unicode says which letter and which mark: NFD takes á apart into a and
an acute, ñ into n and a tilde, and every language this could want is the same
five marks over again.

Where the mark goes follows from the letter.  In a font of this kind a small
letter stands on rows two to six, so there are two rows free above it and the
whole mark fits; a capital stands on rows nought to six, so it is moved down
one -- the row under it is always free -- and only the body of the mark goes
above.  That is why every mark below is two rows with the second one the one
that matters: the second row is what a capital gets.

The two Spanish marks that are not accents, ¿ and ¡, are the question mark and
the exclamation mark turned upside down, which is exactly what they are.
"""

import unicodedata

GLYPH_ROWS = 8
ASCII_GLYPHS = 128


# Each mark as two rows, drawn so that the second is the essential one.
TOP_MARKS = {
    "́": (0b00000110, 0b00001100),         # acute
    "̀": (0b00110000, 0b00011000),         # grave
    "̂": (0b00011000, 0b00100100),         # circumflex
    "̃": (0b00110010, 0b00100110),         # tilde
    "̈": (0b00000000, 0b00100100),         # diaeresis
}

# And the one that hangs below.
BOTTOM_MARKS = {
    "̧": 0b00011000,                       # cedilla
}

# The letters whose dot is in the way: an accent takes its place rather than
# landing on top of it.
DOTTED = "ij"

# What is not a letter and a mark but a letter turned over.
TURNED = {"¿": "?", "¡": "!"}


def turn_over(glyph):
    """A glyph rotated by half a turn, which is what an inverted mark is.

    Turning it moves it across the cell as well as over: a font of this kind
    leaves the leftmost column clear and uses the rightmost, so what comes out
    is one column to the left of where the rest of the letters stand.  It is
    put back, when there is room to put it.
    """
    out = []
    for row in reversed(glyph):
        flipped = 0
        for bit in range(8):
            if row & (1 << bit):
                flipped |= 1 << (7 - bit)
        out.append(flipped)
    if any(row & 0b10000000 for row in out) and not any(row & 1 for row in out):
        out = [row >> 1 for row in out]
    return out


def first_used(glyph):
    for index, row in enumerate(glyph):
        if row:
            return index
    return len(glyph)


def last_used(glyph):
    for index in reversed(range(len(glyph))):
        if glyph[index]:
            return index
    return -1


def with_mark(glyph, mark, dotted=False):
    """Put a two row mark above a letter, making room for it if there is none.

    Room is made the way a typesetter would: a letter that reaches the top is
    moved down into the row below it, which in a font like this one is always
    free because that is where a descender would go.  A letter whose own dot
    is in the way loses the dot, because the accent is standing where it was.
    """
    body = list(glyph)
    if dotted:
        top = first_used(body)
        gap = body.index(0, top) if 0 in body[top:] else top + 1
        for row in range(top, min(gap, len(body))):
            body[row] = 0
    free = first_used(body)
    if free >= 2:
        return [mark[0], mark[1]] + body[2:]
    if last_used(body) < GLYPH_ROWS - 1:
        return [mark[1]] + body[:GLYPH_ROWS - 1]
    return [body[0] | mark[1]] + body[1:]       # nowhere to go: lay it over


def with_tail(glyph, mark):
    """And a mark that hangs below, which needs the bottom row free."""
    body = list(glyph)
    if last_used(body) < GLYPH_ROWS - 1:
        body[GLYPH_ROWS - 1] = mark
        return body
    return body[1:] + [mark]


def ascii_glyph(char, source):
    """The eight bytes the original font holds for a character, or nothing."""
    point = ord(char)
    at = point * GLYPH_ROWS
    if point < ASCII_GLYPHS and at + GLYPH_ROWS <= len(source):
        return list(source[at:at + GLYPH_ROWS])
    return None


def glyph_for(char, source):
    """The eight bytes to draw `char` with, out of the adventure's own font.

    Comes back as None when there is nothing to build it from, which is what
    leaves a character blank rather than guessing at it.
    """
    plain = ascii_glyph(char, source)
    if plain is not None:
        return bytes(plain)
    if char in TURNED:
        upright = ascii_glyph(TURNED[char], source)
        return bytes(turn_over(upright)) if upright else None
    pieces = unicodedata.normalize("NFD", char)
    body = ascii_glyph(pieces[0], source) if pieces else None
    if body is None:
        return None
    for mark in pieces[1:]:
        if mark in TOP_MARKS:
            body = with_mark(body, TOP_MARKS[mark], dotted=pieces[0] in DOTTED)
        elif mark in BOTTOM_MARKS:
            body = with_tail(body, BOTTOM_MARKS[mark])
        else:
            return None                         # a mark this does not know
    return bytes(body)
