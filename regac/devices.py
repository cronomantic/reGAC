# MIT License
#
# Copyright (c) 2025 Cronomantic
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
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

    def fill_point(self, x, y, mode):
        self.set_colour_at(x, y)
        if mode == PAPER:
            self.set_pixel(x, y, False)
        elif mode == SHADE and shaded(x, y):
            self.set_pixel(x, y, True)

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

    def fill_point(self, x, y, mode):
        """Paint the pixel, and keep the mask in step with what the Spectrum
        bitmap would hold.

        This matters more than it looks.  On the original, a half tone lays
        down real pixels, which then stop any later fill, and a background
        fill wipes pixels, which opens a way through for one.  Artists drew
        against that behaviour, so the mask has to follow the same rules or
        fills that stopped short on the Spectrum flood the screen here.
        """
        if not self.inside(x, y):
            return
        index = y * self.width + x
        if mode == SHADE and shaded(x, y):
            self.colours[index] = self.line_colour
            self.mask[index] = 1
            return
        self.colours[index] = self.fill_colour
        if mode == PAPER:
            self.mask[index] = 0

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


# The Amstrad in mode 1: four colours at a time, which is the real constraint
# of this target.  The screen is 320 pixels across but the picture keeps the
# 256 of the original and sits centred, with a margin of 32 either side.
# Stretching it to 320 costs nothing in looks and breaks fills, see
# doc/graficos.md.
CPC_MODE1_PALETTE = [0x000000, 0x0000FF, 0xFF0000, 0xFFFF00]
CPC_SCREEN_WIDTH = 320
CPC_MARGIN = (CPC_SCREEN_WIDTH - SOURCE_WIDTH) // 2


def cpc_device():
    return PixelDevice(SOURCE_WIDTH, SOURCE_ROWS, CPC_MODE1_PALETTE, name="cpc")


# The same machine with the picture stretched across the full screen, kept so
# that the cost of stretching can be measured rather than argued about.
def cpc_stretched_device():
    return PixelDevice(CPC_SCREEN_WIDTH, SOURCE_ROWS, CPC_MODE1_PALETTE, name="cpc-wide")


DEVICES = {
    "spectrum": SpectrumDevice,
    "sam": sam_device,
    "next": next_device,
    "cpc": cpc_device,
    "cpc-wide": cpc_stretched_device,
    "msx": MsxDevice,
    "msx2": msx2_device,
}


def make(name):
    if name not in DEVICES:
        raise KeyError(f"unknown machine {name!r}; try one of {sorted(DEVICES)}")
    return DEVICES[name]()
