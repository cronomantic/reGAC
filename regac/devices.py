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
            [self.palette[self.pens[y * self.width + x]] for x in range(self.width)]
            for y in range(self.height)
        ]


def amstrad_device(header=None):
    """A device for one Amstrad picture, in the four inks it names.

    Those are the eight bytes it carries at its head: four pairs, because an
    ink there can flash between two colours, and the three bits above the
    colour are not understood yet.
    """
    if header:
        inks = [header[n * 2] & 0x1F for n in range(4)]
    else:
        inks = [0, 26, 20, 8]
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


DEVICES = {
    "spectrum": SpectrumDevice,
    "sam": sam_device,
    "next": next_device,
    "cpc": cpc_device,
    "cpc-wide": cpc_stretched_device,
    "msx": MsxDevice,
    "msx2": msx2_device,
    "amstrad": amstrad_device,
}


# Machines with too few inks to hold the colours of the original, which are
# therefore better off having them chosen for each picture.
LIMITED = {"cpc", "cpc-wide"}


def make(name):
    if name not in DEVICES:
        raise KeyError(f"unknown machine {name!r}; try one of {sorted(DEVICES)}")
    return DEVICES[name]()


def device_for(name, gfx=None, picture_id=None):
    """Build a device for one picture.

    On a machine short of inks, which four or sixteen colours to load is a
    decision per picture, not per adventure: the Amstrad can reload its inks
    for every screen.  Choosing them from what the picture actually uses beats
    any fixed palette.
    """
    if name not in LIMITED or gfx is None or picture_id is None:
        return make(name)
    from .gfx import Renderer

    reference = Renderer(gfx, SpectrumDevice()).run(int(picture_id))
    inks = choose_inks(colour_usage(reference))
    if name == "cpc-wide":
        return PixelDevice(CPC_SCREEN_WIDTH, SOURCE_ROWS, inks, name="cpc-wide")
    return cpc_device(inks)
