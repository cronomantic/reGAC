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
"""The picture interpreter.

An adventure stores each picture as a short list of drawing commands.  This
module walks that list; the machine it draws on is a `Device`, which is the
only part that changes from one target to another.  The split is the same one
the 8 bit runtime will have: one shared command interpreter in Z80, and a
handful of primitives written once per machine.

Coordinates in the commands are the ones the Spectrum used: x from 0 to 255
left to right, y from 0 at the bottom of the screen to 175 at the top.  A
device maps them to its own screen, so scaling happens before anything is
rasterised and lines stay joined up.
"""

SOURCE_WIDTH = 256  # the coordinate space the commands are written in
SOURCE_ROWS = 128  # the picture is the top sixteen character rows
MAX_Y = 175  # y=175 is the top pixel row

TRANSPARENT = 8  # colour 8 means leave the colour alone, as in BASIC
CONTRAST = 9  # colour 9 means pick black or white, whichever reads

# What a fill lays down.  GAC holds each as two bytes: the low one is used on
# even rows and the high one is exclusive ored into it on odd ones, counting in
# the y of the commands.  Read out of the original at $6364.
INK = "ink"
PAPER = "paper"
SHADE = "shade"

FILL_PATTERNS = {
    INK: (0xFF, 0x00),  # solid
    PAPER: (0x00, 0x00),  # wiped
    SHADE: (0xAA, 0xFF),  # a half tone, so $AA and $55 by turns
}

PICTURE_TOP = 175  # the y a picture reaches
PICTURE_BOTTOM = 48


def fill_pattern(mode, y):
    """The byte a fill lays down on row y."""
    low, high = FILL_PATTERNS[mode]
    return low ^ (high if y & 1 else 0)


ELLIPSE_STEPS = 8  # steps to a quarter turn

# The table GAC carries at $A1ED: eight cosines then eight sines, for the
# angles a quarter turn divided in eight, scaled by 256 and held to 255 so
# that each fits a byte.  Read out of the adventures themselves.
ELLIPSE_TABLE = [
    251, 237, 213, 181, 142, 98, 50, 0,
    50, 98, 142, 181, 213, 237, 251, 255,
]


def shaded(x, y):
    """The dither SHADE lays down: every other pixel of every other row."""
    return (x + y) & 1 == 0


class Device:
    """What a target machine has to provide for pictures to be drawn on it.

    A device owns its screen, its colour model and its resolution.  Everything
    above this line is shared between machines.
    """

    name = "device"
    width = SOURCE_WIDTH  # its own picture area, in its own pixels
    height = SOURCE_ROWS
    start_ink = 0  # what it draws in before a picture says otherwise
    start_paper = 7
    # Whether a line is the same whichever end it starts from.  The Spectrum
    # ROM's is not: where it puts the diagonal steps depends on which end it
    # was given first.  The Amstrad's firmware puts the two ends in order
    # along the longer side before it draws, so A to B and B to A come out
    # the same points, which was measured on the machine.
    sorts_line_ends = False

    def to_device(self, x, y):
        """Map a coordinate of the commands onto this screen."""
        return x, MAX_Y - y

    def set_border(self, colour):
        raise NotImplementedError

    def set_colours(self, ink, paper, bright, flash):
        raise NotImplementedError

    def ellipse_offset(self, radius, value, sign):
        """How far from the centre one step of an ellipse falls, with the
        sign saying which way it goes along the machine's own axis.

        The Spectrum works in its own pixels and simply takes the top byte of
        radius by table value.  The Amstrad does not, which is why its
        ellipses come out a pixel wider on the side the radius is taken from.
        """
        return sign * ((radius * value) >> 8)

    def set_fill_pens(self, first, second):
        """The two pens a fill weaves together, on a machine that has them.

        The Amstrad parts this from the pen it draws outlines in; the Spectrum
        has no such thing and pays it no attention.
        """

    def draw_point(self, x, y):
        """Put down an outline pixel.  It also becomes a boundary for fills."""
        raise NotImplementedError

    def is_boundary(self, x, y):
        """Whether a fill has to stop here, in this screen's own pixels."""
        raise NotImplementedError

    def is_blocked(self, x, y):
        """The same question in the coordinates of the commands, y upwards."""
        return self.is_boundary(*self.to_device(x, y))

    def begin_fill(self, x, y):
        """A fill is about to start here.

        The Spectrum asks of every point only whether it is set, so it has
        nothing to remember.  The Amstrad asks whether the pen has changed
        from the one under the seed, so that is where it takes note of it.
        """

    def fill_run(self, x, y, pattern):
        """Lay the pattern across the run of clear pixels through this point,
        and give the cells it passes the colours in force.  Returns how many
        pixels it covered."""
        raise NotImplementedError

    def to_rgb(self):
        """The finished picture as rows of (red, green, blue), for saving and
        for comparing one machine against another."""
        raise NotImplementedError


class Renderer:
    """Runs the drawing commands of a picture on a device."""

    MAX_DEPTH = 8  # a picture may call others; stop runaway recursion

    def __init__(self, gfx, device=None):
        from .devices import SpectrumDevice

        self.gfx = gfx  # id -> list of commands
        self.device = device if device is not None else SpectrumDevice()
        self.ink = self.device.start_ink
        self.paper = self.device.start_paper
        self.bright = 0
        self.flash = 0
        self.fill_coverage = []  # pixels each fill command reached, in order
        self.__push_colours()

    def __push_colours(self):
        self.device.set_colours(self.ink, self.paper, self.bright, self.flash)

    # -- primitives ---------------------------------------------------------

    def at_most_the_edge(self, x, y):
        """Where the original puts a point that falls outside the picture.

        It does not drop it, it brings it to the edge: x into the width and y
        into the picture's rows.  That is what stops a curve which leaves the
        top of the picture from coming back as a line across the whole screen,
        and it is the reason a byte of coordinate is not enough on its own.
        GAC does it at $643C, on sixteen bit values, before working out the
        two deltas it hands to the ROM.
        """
        return (min(max(x, 0), self.device.width - 1),
                min(max(y, 0), self.device.height - 1))

    def plot(self, x, y):
        self.device.draw_point(*self.at_most_the_edge(x, y))

    def line(self, x0, y0, x1, y1):
        """A straight line, drawn the way the Spectrum ROM draws one.

        GAC did not write its own: it called the ROM at $24BA, so that is what
        the artwork was drawn against.  The error starts at half the longer
        side and counts up by the shorter one; when it reaches the longer side
        it comes off again and the step goes diagonal.  Counting the other way
        round, which is just as valid a Bresenham, puts the diagonal steps one
        place along and shows up on short slanted lines.
        """
        x0, y0 = self.at_most_the_edge(x0, y0)
        x1, y1 = self.at_most_the_edge(x1, y1)
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        if self.device.sorts_line_ends:
            if (x1 < x0) if dx >= dy else (y1 < y0):
                x0, y0, x1, y1 = x1, y1, x0, y0
        sx = 1 if x1 > x0 else -1
        sy = 1 if y1 > y0 else -1
        self.plot(x0, y0)
        if dx >= dy:
            larger, smaller = dx, dy
        else:
            larger, smaller = dy, dx
        error = larger >> 1
        for _ in range(larger):
            error += smaller
            if error >= larger:
                error -= larger
                if dx >= dy:
                    y0 += sy
                else:
                    x0 += sx
            if dx >= dy:
                x0 += sx
            else:
                y0 += sy
            self.plot(x0, y0)

    def rect(self, x0, y0, x1, y1):
        if x0 > x1:
            x0, x1 = x1, x0
        if y0 > y1:
            y0, y1 = y1, y0
        for x in range(x0, x1 + 1):
            self.plot(x, y0)
            self.plot(x, y1)
        for y in range(y0, y1 + 1):
            self.plot(x0, y)
            self.plot(x1, y)

    def ellipse(self, cx, cy, x1, y1):
        """An ellipse, drawn the way GAC drew one.

        The two pairs in the command are not a box round it: the first is the
        centre and the second gives the radii, as the distance from one to the
        other.  Read out of the original at $88FE.

        It is walked in eight steps a quarter, off a table of sines held at
        $A1ED in the adventure itself, scaled by 256.  Each quarter is drawn
        on its own, starting from the point at the side, which is why the
        curve is made of thirty two straight pieces.
        """
        rx = abs(x1 - cx)
        ry = abs(y1 - cy)
        if rx == 0 and ry == 0:
            self.plot(cx, cy)
            return
        for across, down in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
            # the machine keeps these as sixteen bit values, so a curve that
            # leaves the picture keeps going rather than coming round again;
            # what brings it back is the edge, in at_most_the_edge
            place = (cx + across * rx, cy)
            for step in range(ELLIPSE_STEPS):
                # y counts the other way on the screen than in the commands,
                # so the sign the machine would see is the other one
                following = (
                    cx + self.device.ellipse_offset(rx, ELLIPSE_TABLE[step], across),
                    cy - self.device.ellipse_offset(
                        ry, ELLIPSE_TABLE[ELLIPSE_STEPS + step], -down
                    ),
                )
                if following != place:
                    self.line(place[0], place[1], following[0], following[1])
                place = following

    def flood(self, x, y, mode):
        """Fill, the way GAC filled.

        This is not a flood fill, which is what took so long to work out.  It
        walks up and down the one column the fill was started in, laying a
        horizontal run across each row, and stops the moment the point
        directly above or below is blocked.  It never spreads round a corner.
        That is why a picture carries dozens of fill commands where a flood
        would need one, and why filling solid does not bury the drawing.

        Read out of the original interpreter at $6374.  The coordinates here
        are the ones the commands are written in, y upwards.
        """
        reached = 0
        self.device.begin_fill(x, y)
        if self.device.is_blocked(x, y):
            self.fill_coverage.append(0)
            return 0
        row = y
        while row <= PICTURE_TOP and not self.device.is_blocked(x, row):
            reached += self.device.fill_run(x, row, fill_pattern(mode, row))
            row += 1
        row = y - 1
        while row >= PICTURE_BOTTOM and not self.device.is_blocked(x, row):
            reached += self.device.fill_run(x, row, fill_pattern(mode, row))
            row -= 1
        self.fill_coverage.append(reached)
        return reached

    # -- command dispatch ---------------------------------------------------

    def run(self, picture_id, depth=0):
        commands = self.gfx.get(picture_id)
        if commands is None:
            commands = self.gfx.get(str(picture_id))
        if commands is None or depth > self.MAX_DEPTH:
            return self.device
        point = self.device.to_device
        for command in commands:
            name = command[0]
            args = command[1:]
            if name == "BORDER":
                self.device.set_border(args[0] & 7)
            elif name in ("INK", "PAPER", "BRIGHT", "FLASH"):
                setattr(self, name.lower(), args[0])
                self.__push_colours()
            elif name == "PLOT":
                self.plot(*point(args[0], args[1]))
            elif name == "LINE":
                self.line(*point(args[0], args[1]), *point(args[2], args[3]))
            elif name == "RECT":
                self.rect(*point(args[0], args[1]), *point(args[2], args[3]))
            elif name == "ELLIPSE":
                self.ellipse(*point(args[0], args[1]), *point(args[2], args[3]))
            elif name == "FILL":
                self.flood(args[0], args[1], INK)
            elif name == "BGFILL":
                self.flood(args[0], args[1], PAPER)
            elif name == "SHADE":
                self.flood(args[0], args[1], SHADE)
            elif name == "PENS":
                self.device.set_fill_pens(args[0], args[1])
            elif name == "CALL":
                self.run(args[0], depth + 1)
        return self.device


def render(gfx, picture_id, device=None):
    """Draw one picture and return the device it was drawn on."""
    return Renderer(gfx, device).run(picture_id)
