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
"""The machines pictures can be drawn on.

The targets fall into two families.  The Spectrum and the MSX carry colour per
block of pixels, with the colour clash that implies.  The Amstrad, the Sam
Coupé and the Next carry colour per pixel and have no clash at all, but then a
lit pixel no longer marks the edge of a shape, so those devices keep a
separate one bit mask for the outlines.  The 8 bit runtime will need the same
mask, and it costs four kilobytes.
"""

from .gfx import (
    CONTRAST,
    MAX_Y,
    PAPER,
    SHADE,
    SOURCE_ROWS,
    SOURCE_WIDTH,
    TRANSPARENT,
    Device,
    shaded,
)

# The colours of the original, which is what the commands are written in.
SPECTRUM_PALETTE = [
    0x000000, 0x0100CE, 0xCF0100, 0xCF01CE,
    0x00CF15, 0x01CFCF, 0xCFCF15, 0xCFCFCF,
    0x000000, 0x0200FD, 0xFF0201, 0xFF02FD,
    0x00FF1C, 0x02FFFF, 0xFFFF1D, 0xFFFFFF,
]

CHAR_SIDE = 8


def rgb(colour):
    return ((colour >> 16) & 0xFF, (colour >> 8) & 0xFF, colour & 0xFF)


def nearest(colour, palette):
    """The entry of a palette closest to a colour, by plain squared distance."""
    red, green, blue = rgb(colour)
    best, best_distance = 0, None
    for index, candidate in enumerate(palette):
        cr, cg, cb = rgb(candidate)
        distance = (red - cr) ** 2 + (green - cg) ** 2 + (blue - cb) ** 2
        if best_distance is None or distance < best_distance:
            best, best_distance = index, distance
    return best


class BitmapDevice(Device):
    """A machine with one bit per pixel, where a lit pixel is what stops a
    fill.  How colour is carried is left to the machine underneath."""

    width = SOURCE_WIDTH
    height = SOURCE_ROWS
    char_width = SOURCE_WIDTH // CHAR_SIDE

    def init_bitmap(self):
        # The buffer covers the whole screen, not just the picture, because
        # the frontends print text into the rows below.
        self.pixels = bytearray(self.char_width * 192)

    def is_boundary(self, x, y):
        if not (0 <= x < self.width and 0 <= y < self.height):
            return True
        return (self.pixels[y * self.char_width + (x >> 3)] >> (7 - (x & 7))) & 1

    def set_pixel(self, x, y, on):
        if not (0 <= x < self.width and 0 <= y < self.height):
            return
        index = y * self.char_width + (x >> 3)
        mask = 1 << (7 - (x & 7))
        if on:
            self.pixels[index] |= mask
        else:
            self.pixels[index] &= 0xFF ^ mask

    def draw_point(self, x, y):
        self.set_pixel(x, y, True)
        self.set_colour_at(x, y)

    def fill_run(self, x, y, pattern):
        """Lay the pattern across the run of clear pixels through this point.

        The original walks whole bytes where it can, because eight clear
        pixels are one byte of zero, and goes bit by bit only at the two ends.
        That comes to the same pixels as going one at a time, which is what
        this does.
        """
        row = self.to_device(x, y)[1]
        left = x
        while left > 0 and not self.is_boundary(left - 1, row):
            left -= 1
        right = x
        while right < self.width - 1 and not self.is_boundary(right + 1, row):
            right += 1
        for place in range(left, right + 1):
            lit = (pattern >> (7 - (place & 7))) & 1
            self.set_pixel(place, row, lit)
            self.set_colour_at(place, row)
        return right - left + 1

    def set_colour_at(self, x, y):
        """Give the point the colours in force, however this machine stores
        them."""
        raise NotImplementedError


class SpectrumDevice(BitmapDevice):
    """Colour per eight by eight cell, one bit per pixel.  The original."""

    name = "spectrum"
    palette = SPECTRUM_PALETTE

    def __init__(self):
        self.init_bitmap()
        self.attrs = bytearray([0x38] * (self.char_width * 24))
        self.border = 0
        self.ink = 0
        self.paper = 7
        self.bright = 0
        self.flash = 0

    def set_border(self, colour):
        self.border = colour

    def set_colours(self, ink, paper, bright, flash):
        self.ink, self.paper, self.bright, self.flash = ink, paper, bright, flash

    def attr_at(self, x, y):
        """The attribute to write at a point, honouring transparency."""
        current = self.attrs[(y >> 3) * self.char_width + (x >> 3)]
        ink = current & 7 if self.ink >= TRANSPARENT else self.ink
        paper = (current >> 3) & 7 if self.paper >= TRANSPARENT else self.paper
        bright = (current >> 6) & 1 if self.bright >= TRANSPARENT else self.bright
        flash = (current >> 7) & 1 if self.flash >= TRANSPARENT else self.flash
        if self.ink == CONTRAST:
            ink = 0 if paper >= 4 else 7
        return ink | (paper << 3) | (bright << 6) | (flash << 7)

    def set_colour_at(self, x, y):
        if not (0 <= x < self.width and 0 <= y < self.height):
            return
        self.attrs[(y >> 3) * self.char_width + (x >> 3)] = self.attr_at(x, y)

    def to_rgb(self):
        rows = []
        for y in range(self.height):
            row = []
            for x in range(self.width):
                attr = self.attrs[(y >> 3) * self.char_width + (x >> 3)]
                bright = 8 if (attr >> 6) & 1 else 0
                lit = (self.pixels[y * self.char_width + (x >> 3)] >> (7 - (x & 7))) & 1
                row.append(rgb(self.palette[((attr & 7) if lit else ((attr >> 3) & 7)) + bright]))
            rows.append(row)
        return rows


class PixelDevice(Device):
    """Colour per pixel, with a separate one bit mask marking the outlines so
    that fills still know where to stop."""

    name = "pixel"

    def __init__(self, width, height, palette, name=None):
        self.width = width
        self.height = height
        self.palette = list(palette)
        if name:
            self.name = name
        self.mask = bytearray(width * height)
        self.border = 0
        # The colours in the commands are the Spectrum's; map each to the
        # nearest this machine can actually show.
        self.map = [nearest(c, self.palette) for c in SPECTRUM_PALETTE]
        self.ink = 0
        self.paper = 7
        self.bright = 0
        self.fill_colour = self.map[7]
        self.line_colour = self.map[0]
        # The screen starts in the colour the Spectrum starts in, so that an
        # area no fill ever reaches looks the same on every machine.
        self.colours = bytearray([self.fill_colour]) * (width * height)

    def to_device(self, x, y):
        """Scale into this screen.  Endpoints are mapped before anything is
        rasterised, so lines come out joined up whatever the resolution."""
        row = MAX_Y - y
        return (x * self.width) // SOURCE_WIDTH, (row * self.height) // SOURCE_ROWS

    def set_border(self, colour):
        self.border = self.map[colour & 7]

    def set_colours(self, ink, paper, bright, flash):
        if bright < TRANSPARENT:
            self.bright = bright
        if paper < TRANSPARENT:
            self.paper = paper
        if ink < TRANSPARENT:
            self.ink = ink
        elif ink == CONTRAST:
            self.ink = 0 if self.paper >= 4 else 7
        lift = 8 if self.bright else 0
        self.line_colour = self.map[self.ink + lift]
        self.fill_colour = self.map[self.paper + lift]

    def inside(self, x, y):
        return 0 <= x < self.width and 0 <= y < self.height

    def draw_point(self, x, y):
        if not self.inside(x, y):
            return
        index = y * self.width + x
        self.mask[index] = 1
        self.colours[index] = self.line_colour

    def is_boundary(self, x, y):
        if not self.inside(x, y):
            return True
        return self.mask[y * self.width + x]

    def fill_run(self, x, y, pattern):
        """The same as on the Spectrum, over this machine's mask and colours.

        Keeping the mask in step with what a Spectrum bitmap would hold is
        what makes the pictures come out the same: a half tone lays down real
        marks that stop any later fill, and the artists drew against that.
        """
        row = self.to_device(x, y)[1]
        left = x
        while left > 0 and not self.is_boundary(left - 1, row):
            left -= 1
        right = x
        while right < self.width - 1 and not self.is_boundary(right + 1, row):
            right += 1
        for place in range(left, right + 1):
            lit = (pattern >> (7 - (place & 7))) & 1
            index = row * self.width + place
            self.mask[index] = lit
            self.colours[index] = self.line_colour if lit else self.fill_colour
        return right - left + 1

    def vram(self):
        """The picture as a machine with a byte to a pixel holds it: one row
        after another, each byte the colour of its pixel.  That is a Next's
        layer 2 exactly, which is what the Z80 side is compared against."""
        return bytes(self.colours)

    def to_rgb(self):
        return [
            [rgb(self.palette[self.colours[y * self.width + x]]) for x in range(self.width)]
            for y in range(self.height)
        ]


# The Sam Coupé in mode 4: the same resolution as the Spectrum, sixteen
# colours per pixel and no clash, so only the colour model changes.
def sam_device():
    return PixelDevice(SOURCE_WIDTH, SOURCE_ROWS, SPECTRUM_PALETTE, name="sam")


# The Spectrum Next drawing into layer 2, which is also 256 wide.
def next_device():
    return PixelDevice(SOURCE_WIDTH, SOURCE_ROWS, SPECTRUM_PALETTE, name="next")


# The palette of the TMS9918 the MSX1 draws with, in the usual approximation
# to RGB.  Entry zero is the transparent colour, which shows the backdrop; a
# picture never wants it, so it is left out of the colour matching below.
MSX1_PALETTE = [
    0x000000, 0x000000, 0x3EB849, 0x74D07D,
    0x5955E0, 0x8076F1, 0xB95E51, 0x65DBEF,
    0xDB6559, 0xFF897D, 0xCCC35E, 0xDED087,
    0x3AA241, 0xB766B5, 0xCCCCCC, 0xFFFFFF,
]


# Where screen 2 keeps a byte of eight pixels, and how much of that table the
# picture takes: the top sixteen rows, which is two of its three blocks.
MSX_BLOCK = 2048
MSX_PICTURE_BYTES = 2 * MSX_BLOCK
MSX_PATTERNS = 0x0000  # where the two tables sit in the video chip's memory
MSX_COLOURS = 0x2000


def msx_address(x, y):
    return ((y & 0xF8) << 5) | (x & 0xF8) | (y & 7)


class MsxDevice(BitmapDevice):
    """The MSX1 in screen 2.

    One bit per pixel as on the Spectrum, so fills behave identically, but the
    colour is carried per row of eight pixels rather than per eight by eight
    cell.  The clash is therefore milder vertically and the same horizontally.
    There is no bright and no flash, and the fifteen colours are not the
    Spectrum's, so every colour is matched to the nearest this machine has.
    """

    name = "msx"
    palette = MSX1_PALETTE

    def __init__(self):
        self.init_bitmap()
        # Entry zero is transparent, so match against the rest and shift back.
        self.map = [1 + nearest(c, self.palette[1:]) for c in SPECTRUM_PALETTE]
        self.border = self.map[0]
        self.ink = 0
        self.paper = 7
        start = (self.map[0] << 4) | self.map[7]
        self.colours = bytearray([start]) * (self.char_width * 192)

    def set_border(self, colour):
        self.border = self.map[colour & 7]

    def set_colours(self, ink, paper, bright, flash):
        # Bright and flash have nowhere to go on this machine.
        self.ink, self.paper = ink, paper

    def cell(self, x, y):
        return y * self.char_width + (x >> 3)

    def set_colour_at(self, x, y):
        if not (0 <= x < self.width and 0 <= y < self.height):
            return
        index = self.cell(x, y)
        current = self.colours[index]
        foreground = current >> 4 if self.ink >= TRANSPARENT else self.map[self.ink]
        background = current & 15 if self.paper >= TRANSPARENT else self.map[self.paper]
        if self.ink == CONTRAST:
            foreground = self.map[0] if self.paper >= 4 else self.map[7]
        self.colours[index] = (foreground << 4) | background

    def vram(self):
        """The picture as the two tables the video chip reads.

        Screen 2 keeps the eight lines of a cell together and the cells in
        blocks of a third of the screen, which comes out as

            (y & $F8) * 32 + (x & $F8) + (y & 7)

        -- cheaper than the Spectrum's own sum, and the colour table has
        exactly the same shape one block further on, because a colour here
        belongs to eight pixels of one line and not to a cell of eight by
        eight.  The picture is the top sixteen rows, which is the first two
        blocks of each table; the eight rows of text below are the third.
        """
        patterns = bytearray(MSX_PICTURE_BYTES)
        colours = bytearray(MSX_PICTURE_BYTES)
        for y in range(self.height):
            for column in range(self.char_width):
                at = msx_address(column * 8, y)
                patterns[at] = self.pixels[y * self.char_width + column]
                colours[at] = self.colours[y * self.char_width + column]
        return bytes(patterns), bytes(colours)

    def to_rgb(self):
        rows = []
        for y in range(self.height):
            row = []
            for x in range(self.width):
                colour = self.colours[self.cell(x, y)]
                lit = (self.pixels[y * self.char_width + (x >> 3)] >> (7 - (x & 7))) & 1
                row.append(rgb(self.palette[(colour >> 4) if lit else (colour & 15)]))
            rows.append(row)
        return rows


# The MSX2 in screen 5: colour per pixel, sixteen at a time out of a palette
# wide enough to hold the Spectrum's own colours, so nothing has to be matched.
def msx2_device():
    return PixelDevice(SOURCE_WIDTH, SOURCE_ROWS, SPECTRUM_PALETTE, name="msx2")


# The 27 colours the Amstrad hardware can make, three levels of red, green and
# blue.  The order is the firmware's own colour numbering, 0 black to 26 bright
# white.  Mode 1 loads four of these at a time, mode 0 sixteen.
CPC_HARDWARE_PALETTE = [
    0x000000,  #  0 black
    0x000080,  #  1 blue
    0x0000FF,  #  2 bright blue
    0x800000,  #  3 red
    0x800080,  #  4 magenta
    0x8000FF,  #  5 violet
    0xFF0000,  #  6 bright red
    0xFF0080,  #  7 purple
    0xFF00FF,  #  8 bright magenta
    0x008000,  #  9 green
    0x008080,  # 10 cyan
    0x0080FF,  # 11 sky blue
    0x808000,  # 12 yellow
    0x808080,  # 13 grey
    0x8080FF,  # 14 pale blue
    0xFF8000,  # 15 orange
    0xFF8080,  # 16 pink
    0xFF80FF,  # 17 pale magenta
    0x00FF00,  # 18 bright green
    0x00FF80,  # 19 sea green
    0x00FFFF,  # 20 bright cyan
    0x80FF00,  # 21 lime green
    0x80FF80,  # 22 pale green
    0x80FFFF,  # 23 pale cyan
    0xFFFF00,  # 24 bright yellow
    0xFFFF80,  # 25 pale yellow
    0xFFFFFF,  # 26 bright white
]

CPC_MODE1_INKS = 4
CPC_MODE0_INKS = 16
CPC_SCREEN_WIDTH = 320
CPC_MARGIN = (CPC_SCREEN_WIDTH - SOURCE_WIDTH) // 2

# What the machine loads when nothing has chosen for it: the four the pictures
# of these adventures need most often.  A picture is better off with inks
# picked for it, see choose_inks.
CPC_MODE1_DEFAULT = [
    CPC_HARDWARE_PALETTE[0],  # black
    CPC_HARDWARE_PALETTE[26],  # bright white
    CPC_HARDWARE_PALETTE[20],  # bright cyan
    CPC_HARDWARE_PALETTE[8],  # bright magenta
]


def distance(one, other):
    ar, ag, ab = rgb(one)
    br, bg, bb = rgb(other)
    return (ar - br) ** 2 + (ag - bg) ** 2 + (ab - bb) ** 2


def choose_inks(usage, hardware=None, count=CPC_MODE1_INKS):
    """Pick the colours a machine with few inks should load for one picture.

    `usage` maps a colour of the original to how much of the screen it covers.
    The choice minimises the error over the whole picture weighted by area, so
    a colour covering a wall counts for more than one used on a door handle.
    """
    hardware = hardware or CPC_HARDWARE_PALETTE
    from itertools import combinations

    wanted = [(SPECTRUM_PALETTE[i], area) for i, area in usage.items() if area]
    if not wanted:
        return [hardware[0]] * count
    # Distance from every colour in use to every colour the machine can make.
    table = [[distance(colour, h) for h in hardware] for colour, _ in wanted]
    areas = [area for _, area in wanted]
    best, best_cost = None, None
    for combo in combinations(range(len(hardware)), count):
        cost = 0
        for row, area in zip(table, areas):
            cost += area * min(row[c] for c in combo)
            if best_cost is not None and cost >= best_cost:
                break
        else:
            if best_cost is None or cost < best_cost:
                best, best_cost = combo, cost
    return [hardware[c] for c in best]


def colour_usage(device):
    """How much of the screen each colour of the original covers.  Reads a
    Spectrum device, which is the reference every other machine follows."""
    counts = {}
    cw = device.char_width
    for y in range(device.height):
        for x in range(device.width):
            attr = device.attrs[(y >> 3) * cw + (x >> 3)]
            lift = 8 if (attr >> 6) & 1 else 0
            lit = (device.pixels[y * cw + (x >> 3)] >> (7 - (x & 7))) & 1
            index = ((attr & 7) if lit else ((attr >> 3) & 7)) + lift
            counts[index] = counts.get(index, 0) + 1
    return counts


# What the text of an adventure off a Spectrum is printed in when it says
# nothing: white on black, as on the Spectrum.
SPECTRUM_TEXT_INK = 7
SPECTRUM_TEXT_PAPER = 0


def cpc_picture_colours(gfx, picture_id, text_ink=SPECTRUM_TEXT_INK):
    """How a picture off a Spectrum is shown on an Amstrad: the four inks it
    gets, as the firmware numbers them, and the pen each of the sixteen colours
    of the original comes to.

    It is drawn with the Spectrum's rules -- that is what the picture is -- and
    only the colours have to give, because the machine has four at a time.
    Which four is chosen for each picture against the reference, weighted by
    how much of the screen each colour covers.  The database carries both, so
    that the interpreter looks nothing up, and the reference is built from
    this same function, so that the two cannot disagree.

    The text shares the four pens with the picture, and on the Amstrad the
    original prints it in pen one on pen nought and never changes them.  So of
    the four, the one the text's paper comes to goes to pen nought and the one
    its ink comes to to pen one: which pen an ink is in changes nothing of the
    picture, and this way the text is always in the colours closest to the
    ones it asks for, and what is already on the screen stays paper and letter
    when the next picture comes.
    """
    from .gfx import Renderer

    reference = Renderer(gfx, SpectrumDevice()).run(int(picture_id))
    chosen = choose_inks(colour_usage(reference))
    order = list(range(len(chosen)))
    paper = nearest(SPECTRUM_PALETTE[SPECTRUM_TEXT_PAPER], chosen)
    letter = nearest(SPECTRUM_PALETTE[text_ink], chosen)
    order.remove(paper)
    order.insert(0, paper)
    if letter != paper:
        order.remove(letter)
        order.insert(1, letter)
    chosen = [chosen[n] for n in order]
    inks = [CPC_HARDWARE_PALETTE.index(colour) for colour in chosen]
    pens = [nearest(colour, chosen) for colour in SPECTRUM_PALETTE]
    return inks, pens


def text_ink_of(ddb):
    """The colour an adventure's text is printed in when it says nothing
    else: its own, from ink= in /CTL, or white."""
    return (ddb or {}).get("ink") or SPECTRUM_TEXT_INK


class AmstradDevice(Device):
    """Four pens a pixel, the way the Amstrad drew.

    Two things set it apart from the Spectrum, and both were read out of the
    original interpreter.  A fill stops where the pen stops being the one it
    started on, rather than wherever a pixel happens to be set; and what it
    lays down is a chequer of two pens, which is how four colours are made to
    look like more.  With the two pens the same it comes out solid.

    Drawn on the Spectrum's model instead, an Amstrad picture comes out as one
    flat block of colour, because a fill that should have stopped at a pen of
    its own goes straight over it.
    """

    name = "amstrad"
    # The pen a picture starts drawing in.  Nothing in the picture data says
    # so: the frame every room draws carries no colour order at all and comes
    # out in pen one on the machine.
    start_ink = 1
    start_paper = 1
    sorts_line_ends = True

    def __init__(self, palette, name=None):
        self.palette = list(palette)
        if name:
            self.name = name
        self.pens = bytearray(self.width * self.height)
        self.ink = 1                            # what an outline is drawn in
        self.first = 1                          # and the two a fill weaves
        self.second = 1
        self.seed = 0
        self.border = 0

    def set_border(self, colour):
        self.border = colour & 3

    def set_colours(self, ink, paper, bright, flash):
        if ink < TRANSPARENT:
            self.ink = ink & 3

    def set_fill_pens(self, first, second):
        self.first = first & 3
        self.second = second & 3

    def ellipse_offset(self, radius, value, sign):
        """The Amstrad keeps its coordinates in halves of a pixel, because
        the firmware's screen is 640 by 400 whatever the mode is.  So the step
        is worked out in halves and only then brought down to a pixel, and
        since that is a whole position rather than a distance it always goes
        down: away from the centre on the side the step is taken from, towards
        it on the other.  That one pixel is the whole difference between an
        ellipse of ours and one of theirs.
        """
        halves = (2 * radius * value) >> 8
        return (halves >> 1) if sign > 0 else -((halves + 1) >> 1)

    def inside(self, x, y):
        return 0 <= x < self.width and 0 <= y < self.height

    def draw_point(self, x, y):
        if self.inside(x, y):
            self.pens[y * self.width + x] = self.ink

    def is_boundary(self, x, y):
        if not self.inside(x, y):
            return True
        return self.pens[y * self.width + x] != self.seed

    def begin_fill(self, x, y):
        column, row = self.to_device(x, y)
        self.seed = self.pens[row * self.width + column] if self.inside(column, row) else 0

    def fill_run(self, x, y, pattern):
        row = self.to_device(x, y)[1]
        left = x
        while left > 0 and not self.is_boundary(left - 1, row):
            left -= 1
        right = x
        while right < self.width - 1 and not self.is_boundary(right + 1, row):
            right += 1
        for column in range(left, right + 1):
            # Which of the two pens a point gets turns on the y of the
            # commands, not on the screen row: the original picks between its
            # two pattern bytes with bit zero of that y.
            self.pens[row * self.width + column] = (
                self.first if (column + y) % 2 == 0 else self.second
            )
        return right - left + 1

    def to_rgb(self):
        return [
            [rgb(self.palette[self.pens[y * self.width + x]]) for x in range(self.width)]
            for y in range(self.height)
        ]

    def vram(self):
        """The picture as a machine with a byte to a pixel holds it: the pen
        of every point, row after row.  That is the Next's layer 2 for a
        picture off an Amstrad, whose palette puts the picture's inks in the
        first four entries."""
        return bytes(self.pens)


# The inks the firmware starts the machine with, which is what an Amstrad
# picture with none of its own is shown in.
CPC_START_INKS = [1, 24, 20, 6]


def amstrad_device(header=None):
    """A device for one Amstrad picture, in the four inks it names.

    Those are the eight bytes it carries at its head: four pairs, because an
    ink there can flash between two colours.  Of each pair the second is the
    one the machine shows first -- it is what the original hands SCR SET INK
    as the first colour -- so that is the one a still picture is drawn in.
    Only the five bits the firmware reads count: a colour that was typed
    rather than taken from the screen is stored as the letter that was typed,
    and A or a comes out 1, Z or z 26, and a space black, which is what the
    machine does with it.
    """
    if header:
        inks = [header[n * 2 + 1] & 0x1F for n in range(4)]
    else:
        inks = CPC_START_INKS
    return AmstradDevice([CPC_HARDWARE_PALETTE[min(c, 26)] for c in inks])


def cpc_device(palette=None):
    return PixelDevice(
        SOURCE_WIDTH, SOURCE_ROWS, palette or CPC_MODE1_DEFAULT, name="cpc"
    )


# The same machine with the picture stretched across the full screen, kept so
# that the cost of stretching can be measured rather than argued about.
def cpc_stretched_device():
    return PixelDevice(
        CPC_SCREEN_WIDTH, SOURCE_ROWS, CPC_MODE1_DEFAULT, name="cpc-wide"
    )


# The Amstrad PCW's screen is 720 by 256 and carries no colour at all: one bit
# a pixel, lit or not.  Its lines are not stored one after another either.  The
# video reads a row of eight lines out of 720 bytes, taking every eighth byte
# down a column, so within a row the eight lines of a byte column are the eight
# bytes in a row.  Which 720 bytes make which row is the roller RAM's business,
# and that is ours to lay out.
PCW_COLUMNS = 90                        # bytes across the screen
PCW_ROW_BYTES = CHAR_SIDE * PCW_COLUMNS  # what one row of eight lines takes
PCW_SCALE = 2                           # a picture pixel is two of its own
PCW_PICTURE_ROWS = SOURCE_ROWS // CHAR_SIDE


def pcw_margin(scale=PCW_SCALE):
    """The columns to the left of a picture drawn this wide, which is what
    puts it in the middle of the ninety the screen has."""
    return (PCW_COLUMNS - (SOURCE_WIDTH * scale) // CHAR_SIDE) // 2


PCW_MARGIN = pcw_margin()


def pcw_address(x, y):
    """Where a pixel lives, counting from the first byte of the first row."""
    return (y >> 3) * PCW_ROW_BYTES + CHAR_SIDE * (x >> 3) + (y & 7)


def luminance(colour):
    """How light a colour is, nought to 255, in the usual weights."""
    red, green, blue = rgb(colour)
    return (299 * red + 587 * green + 114 * blue) // 1000


# A four by four ordered dither, indexed by the low two bits of y then of x.
# Sixteen thresholds give seventeen levels, which is what it takes to keep the
# eight colours of the original apart: with four of them the dark blue of a
# window came out the same black as the outline around it.
#
# Four across is also as wide as it can be and still cost nothing.  What a fill
# lays down repeats every four points, so eight points are still one byte and a
# whole run of them is still that byte written along it, which is what makes a
# fill affordable on the machine.
DITHER = (
    0, 8, 2, 10,
    12, 4, 14, 6,
    3, 11, 1, 9,
    15, 7, 13, 5,
)
DITHER_LEVELS = 16


def dithered(level, x, y):
    return level > DITHER[((y & 3) << 2) | (x & 3)]


class PcwDevice(Device):
    """The Amstrad PCW: light or no light, and nothing in between.

    A machine with no colour cannot be told the Spectrum's colours and left to
    it, so two things happen here.  Areas are laid down as a dither chosen by
    how light the colour was, which keeps a dark wall darker than a bright sky
    and keeps two different colours apart; outlines are not dithered at all,
    because half a line is not a line, so they come out solid, black or white
    by that same lightness.

    The colour going and the light staying means a lit pixel can no longer be
    what stops a fill: a black outline on this screen is an unlit pixel.  So,
    like the machines with colour per pixel, it keeps a separate one bit mask,
    and that mask holds exactly what a Spectrum's bitmap would hold.  It has
    to: the pictures were drawn against the Spectrum's own rule, where the lit
    half of a half tone stops the next fill and the unlit half does not.

    The picture is drawn twice as wide as it is written, because a pixel of
    this screen is about half as wide as it is tall.  Nothing here knows about
    that: it is a coordinate space of 256 across, as on every other machine,
    and the doubling happens on the way to the screen, which is what the
    runtime does too.
    """

    name = "pcw"
    palette = [0x000000, 0xFFFFFF]

    def __init__(self, scale=PCW_SCALE):
        # How wide a point of the picture is drawn.  Two is what keeps the
        # shape it has on a Spectrum, because a pixel here is about half as
        # wide as it is tall; one puts it small in the middle of the screen.
        # The runtime takes the same number, and both of them work it out the
        # same way: it is the project file that says which.
        self.scale = scale
        self.margin = pcw_margin(scale)
        self.mask = bytearray(self.width * self.height)
        self.ink = 0
        self.paper = 7
        self.border = 0
        self.line_lit = 0
        self.ink_level = 0
        self.paper_level = DITHER_LEVELS
        # The screen starts in the colour the Spectrum starts in, so an area
        # no fill ever reaches looks the same on every machine.
        self.lit = bytearray(
            1 if dithered(self.paper_level, x, y) else 0
            for y in range(self.height)
            for x in range(self.width)
        )

    def level_of(self, colour):
        """How many of the sixteen thresholds a colour lights.

        The lightness is measured against white rather than against the
        brightest the Spectrum's hardware can manage, and that is why the
        bright bit does nothing at all here: it lifts the whole picture at
        once on a colour set, and a screen with one level of light has nowhere
        to put it.  Measured the other way a picture which never turns bright
        on would never reach the top of this screen, which is worse.
        """
        white = luminance(SPECTRUM_PALETTE[7])
        light = luminance(SPECTRUM_PALETTE[colour & 7])
        return (light * DITHER_LEVELS + white // 2) // white

    def set_border(self, colour):
        self.border = colour & 7

    def set_colours(self, ink, paper, bright, flash):
        """Work out what the colours in force come to on this screen.

        The ink and the paper are kept as they came, not as they came out, so
        that an ink of nine, which means pick whichever reads against the
        paper, is worked out again when the paper changes.  That is what the
        runtime does as well, where the colours are settled once per shape
        rather than once per pixel.
        """
        if paper < TRANSPARENT:
            self.paper = paper
        if ink < TRANSPARENT or ink == CONTRAST:
            self.ink = ink
        ink = self.ink
        if ink == CONTRAST:
            ink = 0 if self.paper >= 4 else 7
        self.ink_level = self.level_of(ink)
        self.paper_level = self.level_of(self.paper)
        self.line_lit = 1 if self.ink_level * 2 > DITHER_LEVELS else 0

    def inside(self, x, y):
        return 0 <= x < self.width and 0 <= y < self.height

    def draw_point(self, x, y):
        if not self.inside(x, y):
            return
        index = y * self.width + x
        self.mask[index] = 1
        self.lit[index] = self.line_lit

    def is_boundary(self, x, y):
        if not self.inside(x, y):
            return True
        return self.mask[y * self.width + x]

    def fill_run(self, x, y, pattern):
        row = self.to_device(x, y)[1]
        left = x
        while left > 0 and not self.is_boundary(left - 1, row):
            left -= 1
        right = x
        while right < self.width - 1 and not self.is_boundary(right + 1, row):
            right += 1
        for place in range(left, right + 1):
            lit = (pattern >> (7 - (place & 7))) & 1
            index = row * self.width + place
            self.mask[index] = lit
            level = self.ink_level if lit else self.paper_level
            self.lit[index] = 1 if dithered(level, place, row) else 0
        return right - left + 1

    def screen(self):
        """The picture as the sixteen rows of screen bytes it becomes, each
        row the 720 the video reads, with the picture put in the middle."""
        out = bytearray(PCW_PICTURE_ROWS * PCW_ROW_BYTES)
        for y in range(self.height):
            for x in range(self.width):
                if not self.lit[y * self.width + x]:
                    continue
                column = self.margin * CHAR_SIDE + x * self.scale
                for step in range(self.scale):
                    place = column + step
                    out[pcw_address(place, y)] |= 0x80 >> (place & 7)
        return bytes(out)

    def to_rgb(self):
        return [
            [rgb(self.palette[self.lit[y * self.width + x]])
             for x in range(self.width)]
            for y in range(self.height)
        ]


# -- the PC, with a CGA in its 320 by 200 mode -------------------------------

# The CGA's sixteen colours, the IBM monitor's: the dark yellow comes out
# brown, which the monitor does on purpose.
CGA_PALETTE = [
    0x000000, 0x0000AA, 0x00AA00, 0x00AAAA,
    0xAA0000, 0xAA00AA, 0xAA5500, 0xAAAAAA,
    0x555555, 0x5555FF, 0x55FF55, 0x55FFFF,
    0xFF5555, 0xFF55FF, 0xFFFF55, 0xFFFFFF,
]


class CgaTrio:
    """Three colours of the four a CGA shows in its 320 by 200 mode.  The
    fourth is the background, any of the sixteen; these three come as a set,
    and which set is two registers: the mode, whose third bit takes the colour
    away from a composite monitor and gives the third set on an RGB one, and
    the colour select, whose fourth bit is the brightness and fifth which of
    the other two sets."""

    def __init__(self, name, colours, bright, palette, mode5):
        self.name = name
        self.colours = colours          # what pixels one to three show
        self.bright = bright
        self.palette = palette
        self.mode5 = mode5

    def select(self, background):
        """The byte for port 3D9h: the background, the brightness, the set."""
        return background | (self.bright << 4) | (self.palette << 5)

    def mode(self):
        """The byte for port 3D8h: graphics, 320 across, the picture on, and
        the colour off for the third set."""
        return 0x0A | (0x04 if self.mode5 else 0)


CGA_TRIOS = [
    CgaTrio("paleta 0", (2, 4, 6), 0, 0, False),
    CgaTrio("paleta 0 brillante", (10, 12, 14), 1, 0, False),
    CgaTrio("paleta 1", (3, 5, 7), 0, 1, False),
    CgaTrio("paleta 1 brillante", (11, 13, 15), 1, 1, False),
    CgaTrio("modo 5", (3, 4, 7), 0, 0, True),
    CgaTrio("modo 5 brillante", (11, 12, 15), 1, 0, True),
]

CGA_BYTES_ACROSS = 80                   # four pixels to a byte
CGA_BANK = 0x2000                       # odd rows are in a bank of their own
CGA_SCREEN_BYTES = 0x4000
CGA_MARGIN = (320 - SOURCE_WIDTH) // 2 // 4   # the picture in the middle: 8


def cga_colours(background, trio):
    """What pixel values nought to three show."""
    return [CGA_PALETTE[background]] + [CGA_PALETTE[c] for c in trio.colours]


def best_cga_palette(cost_of, allowed=None):
    """The background and the trio that cost least, trying the ninety six.
    `cost_of` is given the four colours and says what they cost; `allowed`,
    when given, says which of them may be had at all."""
    best = None
    for trio in CGA_TRIOS:
        for background in range(16):
            four = cga_colours(background, trio)
            if allowed is not None and not allowed(four):
                continue
            cost = cost_of(four)
            if best is None or cost < best[0]:
                best = (cost, background, trio)
    return best[1], best[2]


def cga_picture_colours(gfx, picture_id):
    """How a picture off a Spectrum is shown on a CGA: the background and the
    trio chosen for it, and the pixel value each of the sixteen colours of the
    original comes to.  Chosen against the reference, weighted by how much of
    the screen each colour covers, as the Amstrad's four inks are -- see
    cpc_picture_colours.  Unlike the Amstrad's, the four cannot be put in any
    order: nought is the background and one to three the trio as it comes, so
    the text is printed in whichever values its colours come to.

    But the text's paper comes to nought, always, as it goes to pen nought on
    the Amstrad: nought is also the border and everything round the picture
    that nobody writes, and the paper anywhere else would leave the screen in
    two colours where it should be one -- the text that scrolled up beside
    the picture in one, and the border in the other.  So only a palette whose
    background is the nearest of its four to the paper is had."""
    from .gfx import Renderer

    reference = Renderer(gfx, SpectrumDevice()).run(int(picture_id))
    usage = colour_usage(reference)

    def cost_of(four):
        return sum(area * min(distance(SPECTRUM_PALETTE[colour], c) for c in four)
                   for colour, area in usage.items())

    def paper_on_the_background(four):
        return nearest(SPECTRUM_PALETTE[SPECTRUM_TEXT_PAPER], four) == 0

    background, trio = best_cga_palette(cost_of, paper_on_the_background)
    four = cga_colours(background, trio)
    return background, trio, [nearest(colour, four) for colour in SPECTRUM_PALETTE]


def cga_amstrad_colours(gfx, picture_id, header=None):
    """How a picture off an Amstrad is shown on a CGA: the background, the
    trio, and which pixel value each of its four pens is written as.

    The pens need not be the pixel values.  What the Amstrad's rules ask of a
    pen is only to be told apart from the others -- a fill stops where the pen
    changes -- and that holds for any way of dealing the four pens out to the
    four values, as long as it is the same over the whole picture.  So they
    are dealt out as suits the colours: the background can be any of sixteen
    and a trio is three in a fixed order, and a picture in yellow and white,
    say, has its white in the background and its yellow in the trio that has
    one.  Of the ninety six palettes and the ways to deal, the one closest to
    the inks the picture carries, pen by pen, weighted by how much of the
    picture each pen covers.

    Pen nought is not dealt: it is the background, value nought, always.  It
    is the text's paper, and on the Amstrad the border wears it too; on a CGA
    the border is the background, and so is everything round the picture
    that nobody writes, so pen nought anywhere else would leave the screen in
    two colours where the Amstrad shows one."""
    from itertools import permutations

    from .gfx import Renderer

    inks = [header[n * 2 + 1] & 0x1F for n in range(4)] if header else CPC_START_INKS
    wanted = [CPC_HARDWARE_PALETTE[min(ink, 26)] for ink in inks]
    drawn = Renderer(gfx, AmstradDevice(wanted)).run(int(picture_id))
    area = [drawn.pens.count(pen) for pen in range(4)]

    best = None
    for trio in CGA_TRIOS:
        for background in range(16):
            four = cga_colours(background, trio)
            for rest in permutations(range(1, 4)):
                values = (0,) + rest
                cost = sum(area[pen] * distance(wanted[pen], four[values[pen]])
                           for pen in range(4))
                if best is None or cost < best[0]:
                    best = (cost, background, trio, list(values))
    return best[1], best[2], best[3]


def cga_amstrad_flash(gfx, picture_id, header=None, chosen=None):
    """The other palette of a picture off an Amstrad, the one a flashing pen
    shows half the time: the background and the trio, in the two port bytes.

    On the Amstrad a pen that flashes changes on its own.  A CGA can change
    only its background or the whole of its trio, so this flashes what it
    can: the second palette is the one that brings the flashing pens nearest
    their other inks **without moving any pen that does not flash** -- every
    value a still pen is written in shows exactly the same colour in both.
    When nothing can move, the two are the same and nothing flashes.  The
    pens stay dealt as they were: which value a pen is written in is in the
    picture and cannot change with it.  `chosen` is what cga_amstrad_colours
    said, when it has been asked already."""
    background, trio, values = chosen or cga_amstrad_colours(gfx, picture_id,
                                                             header)
    if not header:
        return trio.select(background), trio.mode()
    shown = cga_colours(background, trio)
    flashing = [pen for pen in range(4)
                if header[pen * 2] & 0x1F != header[pen * 2 + 1] & 0x1F]
    if not flashing:
        return trio.select(background), trio.mode()
    other = [CPC_HARDWARE_PALETTE[min(header[pen * 2] & 0x1F, 26)]
             for pen in range(4)]
    best = None
    for candidate in CGA_TRIOS:
        for back in range(16):
            four = cga_colours(back, candidate)
            if any(four[values[pen]] != shown[values[pen]]
                   for pen in range(4) if pen not in flashing):
                continue                # a still pen would move
            cost = sum(distance(other[pen], four[values[pen]])
                       for pen in flashing)
            if best is None or cost < best[0]:
                best = (cost, back, candidate)
    return best[2].select(best[1]), best[2].mode()


def cga_device(gfx=None, picture_id=None, ddb=None):
    """A picture as a CGA shows it, drawn with the rules of the GAC the
    adventure was written with.  The drawing is the Amstrad's or the
    Spectrum's own device; what is the CGA's is the four colours and where
    the pixels go, which is cga_screen."""
    if from_an_amstrad(ddb):
        header = None
        if picture_id is not None:
            inks = ddb.get("gfx_inks") or {}
            header = inks.get(str(picture_id), inks.get(int(picture_id)))
        if gfx is None or picture_id is None:
            background, trio, values = 0, CGA_TRIOS[3], [0, 1, 2, 3]
        else:
            background, trio, values = cga_amstrad_colours(gfx, picture_id, header)
        four = cga_colours(background, trio)
        device = AmstradDevice([four[values[pen]] for pen in range(4)], name="cga")
        device.cga_values = values      # the pixel value each pen is written as
        return device
    if gfx is None or picture_id is None:
        four = cga_colours(0, CGA_TRIOS[3])
    else:
        background, trio, _ = cga_picture_colours(gfx, picture_id)
        four = cga_colours(background, trio)
    return PixelDevice(SOURCE_WIDTH, SOURCE_ROWS, four, name="cga")


def cga_screen(device):
    """The picture as the CGA's own memory at B800 holds it: two pixels to a
    nibble and four to a byte, the first in the top two bits; eighty bytes a
    row; the even rows in the first eight kilobytes and the odd ones in the
    second; and the picture eight bytes in, in the middle of the 320.  The
    rest is nought, which is the background.  What an interpreter's dump of
    the screen is compared against."""
    values = device.vram()
    dealt = getattr(device, "cga_values", None)
    if dealt:
        values = bytes(dealt[pen] for pen in values)
    out = bytearray(CGA_SCREEN_BYTES)
    for row in range(SOURCE_ROWS):
        base = (row & 1) * CGA_BANK + (row >> 1) * CGA_BYTES_ACROSS + CGA_MARGIN
        for x in range(SOURCE_WIDTH):
            out[base + (x >> 2)] |= (values[row * SOURCE_WIDTH + x] & 3) << (6 - 2 * (x & 3))
    return bytes(out)


DEVICES = {
    "spectrum": SpectrumDevice,
    "sam": sam_device,
    "next": next_device,
    "cpc": cpc_device,
    "cpc-wide": cpc_stretched_device,
    "msx": MsxDevice,
    "msx2": msx2_device,
    "pcw": PcwDevice,
    "amstrad": amstrad_device,
    "cga": cga_device,
}


# Machines with too few inks to hold the colours of the original, which are
# therefore better off having them chosen for each picture.
LIMITED = {"cpc", "cpc-wide"}

# The machines that draw an adventure off an Amstrad with the Amstrad's rules.
# An adventure is drawn with the rules of the GAC it was written with, on any
# machine that has room for them.  The Next does, and needs nothing extra: its
# screen is a byte a pixel, so the pen of every point is on it to be read back.
# A PC's CGA is two bits a pixel like the Amstrad's own, so the same holds;
# "pc" is the machine and "cga" its screen.  The others would need eight
# kilobytes to keep the pens in, and are left out: see doc/pendiente.md.
AMSTRAD_RULES = {"cpc", "amstrad", "next", "cga", "pc"}


def from_an_amstrad(ddb):
    """Whether an adventure was written with the Amstrad's GAC, whose
    pictures are pens and not the Spectrum's inks and papers."""
    return bool(ddb) and ddb.get("model") == "CPC"


def make(name):
    if name not in DEVICES:
        raise KeyError(f"unknown machine {name!r}; try one of {sorted(DEVICES)}")
    return DEVICES[name]()


def device_for(name, gfx=None, picture_id=None, ddb=None):
    """Build a device for one picture, the way that machine shows it.

    An adventure is drawn with the rules of the GAC it was written with: one
    off an Amstrad with the Amstrad's, in the inks each of its pictures
    carries; one off a Spectrum with the Spectrum's.  On a machine short of
    inks, which four to load is a decision per picture, not per adventure: the
    Amstrad reloads its inks for every screen, and choosing them from what the
    picture actually uses beats any fixed palette.
    """
    if name == "cga":
        return cga_device(gfx, picture_id, ddb)
    if name in AMSTRAD_RULES and from_an_amstrad(ddb):
        header = None
        if picture_id is not None:
            inks = ddb.get("gfx_inks") or {}
            header = inks.get(str(picture_id), inks.get(int(picture_id)))
        return amstrad_device(header)
    if name not in LIMITED or gfx is None or picture_id is None:
        return make(name)
    if name == "cpc-wide":
        from .gfx import Renderer

        reference = Renderer(gfx, SpectrumDevice()).run(int(picture_id))
        inks = choose_inks(colour_usage(reference))
        return PixelDevice(CPC_SCREEN_WIDTH, SOURCE_ROWS, inks, name="cpc-wide")
    inks, _ = cpc_picture_colours(gfx, picture_id, text_ink_of(ddb))
    return cpc_device([CPC_HARDWARE_PALETTE[ink] for ink in inks])
