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
"""Reading a typeface somebody else drew.

A font for one of these machines is eight bytes a letter, one bit a pixel, and
there is no format: there is a heap of them, all the same bytes with something
different in front and the letters in a different order.  So this takes a file
and works out what it is, and says what it could not work out rather than
guessing.

What it knows:

  * a plain dump, which is what a font editor writes and what the ROM of one
    of these machines is -- 768 bytes is the ninety six from the space up, the
    shape a Spectrum's font comes in; 1024 and 2048 are a hundred and
    twenty eight and two hundred and fifty six from nought
  * the same with a load address in front, which is how a C64 charset travels
  * the same with the hundred and twenty eight byte header AMSDOS and +3DOS
    put on everything
  * the two PSF headers a console font has
  * a PNG of the letters in a grid, which is what an artist would rather draw

And two orders that are not ASCII: a C64 keeps its letters in screen codes and
an Atari in ATASCII, so what is in slot one is not what ASCII has there.

What comes back is a map from the character's own number -- its codepoint,
which is what the rest of this reads a font by -- to its eight bytes.
"""

from .png import read_image

GLYPH_ROWS = 8

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
PSF1_MAGIC = b"\x36\x04"
PSF2_MAGIC = b"\x72\xb5\x4a\x86"
DOS_HEADER = 128                # what AMSDOS and +3DOS put in front of a file

# The sizes a plain dump comes in, and where its first letter stands.
PLAIN = {768: 32, 1024: 0, 2048: 0, 6144: 0}

# How a sheet of letters is laid out: which character the first cell is, and
# how many cells there are.  A name for it is worth having because an image
# does not say either of those things -- and because with the count known, a
# sheet drawn at twice the size is still a sheet this can read.
#
# Latin-1 is the one to draw.  Every letter this project can print is in it,
# in the place every font editor puts it, so an artist never has to hear about
# the codes reGAC uses: draw the a-acute where Latin-1 keeps it and it lands
# where it belongs.
LAYOUTS = {
    "ascii": (32, 96),          # the space to the copyright sign
    "latin1": (0, 256),         # and the whole of Latin-1, accents and all
    "latin1-high": (160, 96),   # just its top half, which is where they are
}

# A C64 keeps @ABC... at nought and the digits at forty eight; an Atari keeps
# the punctuation first.  Only the letters and digits are worth mapping: what
# is not in one of these is left where it is.
C64_ORDER = ("@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_"
             " !\"#$%&'()*+,-./0123456789:;<=>?")
ATASCII_ORDER = (" !\"#$%&'()*+,-./0123456789:;<=>?"
                 "@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_"
                 "`abcdefghijklmnopqrstuvwxyz{|}~")

ORDERS = {"ascii": None, "c64": C64_ORDER, "atascii": ATASCII_ORDER}


class FontError(Exception):
    pass


def strip_header(blob):
    """Take off whatever is in front of the glyphs, and say where they start.

    Comes back as the bytes and the slot the first glyph stands for, because
    some of these formats say that and some only imply it.
    """
    if blob[:len(PSF2_MAGIC)] == PSF2_MAGIC:
        length = int.from_bytes(blob[8:12], "little")
        height = int.from_bytes(blob[24:28], "little")
        if height != GLYPH_ROWS:
            raise FontError(f"this console font is {height} rows tall, not eight")
        return blob[length:], 0
    if blob[:len(PSF1_MAGIC)] == PSF1_MAGIC:
        if blob[3] != GLYPH_ROWS:
            raise FontError(f"this console font is {blob[3]} rows tall, not eight")
        return blob[4:], 0
    if len(blob) > DOS_HEADER and (len(blob) - DOS_HEADER) in PLAIN:
        # AMSDOS and +3DOS: the header is a hundred and twenty eight bytes and
        # the length in it is the rest of the file.
        return blob[DOS_HEADER:], None
    if len(blob) % GLYPH_ROWS == 2 and (len(blob) - 2) in PLAIN:
        return blob[2:], None                   # a load address, as on a C64
    return blob, None


def glyphs_of(blob, first):
    """The glyphs of a dump, against the slot each one stands for."""
    if len(blob) % GLYPH_ROWS:
        raise FontError(
            f"a font is eight bytes a letter and this is {len(blob)} bytes, "
            "which is not a whole number of them"
        )
    return {first + n: bytes(blob[n * GLYPH_ROWS:(n + 1) * GLYPH_ROWS])
            for n in range(len(blob) // GLYPH_ROWS)}


def in_order(slots, order):
    """Move the glyphs from the order their machine keeps them in to ours.

    A slot the order says nothing about is left where it is, which is what
    keeps a dump that is already ASCII from being touched at all.
    """
    if order is None:
        return slots
    out = {}
    for slot, glyph in slots.items():
        if 0 <= slot < len(order):
            out[ord(order[slot])] = glyph
        else:
            out[slot] = glyph
    return out


def cell_size(width, height, wanted):
    """How big a cell is on this sheet.

    Eight pixels, unless the sheet was drawn bigger: knowing how many cells
    there are supposed to be says which, so a sheet at twice or three times
    the size is read as what it is instead of as four or nine times as many
    letters.
    """
    if wanted is None:
        return GLYPH_ROWS
    for scale in range(1, 9):
        side = GLYPH_ROWS * scale
        if width % side == 0 and height % side == 0:
            if (width // side) * (height // side) == wanted:
                return side
    raise FontError(
        f"this sheet is {width} by {height}, which is no way to lay out "
        f"{wanted} cells of eight by eight or a whole multiple of them"
    )


def from_image(blob, wanted=None):
    """The glyphs of a PNG: a grid of cells, read the way a page is, left to
    right and top to bottom, and a pixel is ink when it is darker than half."""
    width, height, ink = read_image(blob)
    side = cell_size(width, height, wanted)
    if width % side or height % side:
        raise FontError(
            f"a sheet of letters is a whole number of cells and this one is "
            f"{width} by {height}"
        )
    step = side // GLYPH_ROWS
    across = width // side
    slots = {}
    for cell in range(across * (height // side)):
        left = (cell % across) * side
        top = (cell // across) * side
        glyph = bytearray()
        for row in range(GLYPH_ROWS):
            bits = 0
            for column in range(GLYPH_ROWS):
                if ink[(top + row * step) * width + left + column * step]:
                    bits |= 0x80 >> column
            glyph.append(bits)
        slots[cell] = bytes(glyph)
    return slots


def read(path, first=None, order="ascii", layout=None):
    """Read a font file, whatever kind it is, into codepoint -> eight bytes.

    `layout` names how the letters are laid out and is the thing to reach for
    first: it says both where the sheet starts and how many letters it holds.
    `first` says only the former, for a file that does not say so itself, and
    `order` says which machine's order the glyphs are in.
    """
    if order not in ORDERS:
        raise FontError(f"no font is kept in {order!r} order; "
                        f"try one of {', '.join(sorted(ORDERS))}")
    if layout is not None and layout not in LAYOUTS:
        raise FontError(f"there is no {layout!r} layout; "
                        f"try one of {', '.join(sorted(LAYOUTS))}")
    starts, holds = LAYOUTS.get(layout, (None, None))
    with open(path, "rb") as f:
        blob = f.read()
    if blob[:len(PNG_MAGIC)] == PNG_MAGIC:
        slots = from_image(blob, holds)
        start = first if first is not None else (0 if starts is None else starts)
        slots = {slot + start: glyph for slot, glyph in slots.items()}
    else:
        body, said = strip_header(blob)
        start = first if first is not None else said
        if start is None:
            start = PLAIN.get(len(body)) if starts is None else starts
        if start is None:
            raise FontError(
                f"{len(body)} bytes is not a font this knows: say how it is "
                "laid out with layout=, or where its first letter stands "
                "with first="
            )
        if holds is not None and len(body) != holds * GLYPH_ROWS:
            raise FontError(
                f"a {layout} font is {holds * GLYPH_ROWS} bytes and this is "
                f"{len(body)}"
            )
        slots = glyphs_of(body, start)
    return in_order(slots, ORDERS[order])
