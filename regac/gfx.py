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


ELLIPSE_STEPS = 64
SINE_SCALE = 7  # the table is scaled by 128


def scaled(radius, sine):
    """radius * sine / 128, cut towards zero, the way the Z80 will do it."""
    magnitude = (radius * abs(sine)) >> SINE_SCALE
    return -magnitude if sine < 0 else magnitude


# round(128 * sin(2 * pi * step / 64)), held to 127 so that it fits a byte
# with a sign, which is what the Z80 has to work with
SINE = [0, 13, 25, 37, 49, 60, 71, 81, 91, 99, 106, 113, 118, 122, 126, 127, 127, 127, 126, 122, 118, 113, 106, 99, 91, 81, 71, 60, 49, 37, 25, 13, 0, -13, -25, -37, -49, -60, -71, -81, -91, -99, -106, -113, -118, -122, -126, -127, -127, -127, -126, -122, -118, -113, -106, -99, -91, -81, -71, -60, -49, -37, -25, -13]


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

    def to_device(self, x, y):
        """Map a coordinate of the commands onto this screen."""
        return x, MAX_Y - y

    def set_border(self, colour):
        raise NotImplementedError

    def set_colours(self, ink, paper, bright, flash):
        raise NotImplementedError

    def draw_point(self, x, y):
        """Put down an outline pixel.  It also becomes a boundary for fills."""
        raise NotImplementedError

    def is_boundary(self, x, y):
        """Whether a fill has to stop here, in this screen's own pixels."""
        raise NotImplementedError

    def is_blocked(self, x, y):
        """The same question in the coordinates of the commands, y upwards."""
        return self.is_boundary(*self.to_device(x, y))

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
        self.ink = 0
        self.paper = 7
        self.bright = 0
        self.flash = 0
        self.fill_coverage = []  # pixels each fill command reached, in order
        self.__push_colours()

    def __push_colours(self):
        self.device.set_colours(self.ink, self.paper, self.bright, self.flash)

    # -- primitives ---------------------------------------------------------

    def plot(self, x, y):
        self.device.draw_point(x, y)

    def line(self, x0, y0, x1, y1):
        """A straight line, drawn the way the Spectrum ROM draws one.

        GAC did not write its own: it called the ROM at $24BA, so that is what
        the artwork was drawn against.  The error starts at half the longer
        side and counts up by the shorter one; when it reaches the longer side
        it comes off again and the step goes diagonal.  Counting the other way
        round, which is just as valid a Bresenham, puts the diagonal steps one
        place along and shows up on short slanted lines.
        """
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
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

    def ellipse(self, x0, y0, x1, y1):
        """An ellipse inscribed in the given box, walked round in fixed steps.

        A table of sines and whole number arithmetic, rather than anything
        smoother, so that the Z80 can do exactly the same and the two can be
        compared pixel for pixel.  Every ellipse in the eight adventures fits
        in 36 pixels, where the steps are smaller than the pixels anyway.
        """
        if x0 > x1:
            x0, x1 = x1, x0
        if y0 > y1:
            y0, y1 = y1, y0
        cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
        rx, ry = (x1 - x0) // 2, (y1 - y0) // 2
        if rx < 1 and ry < 1:
            self.plot(cx, cy)
            return
        points = []
        for step in range(ELLIPSE_STEPS):
            points.append(
                (
                    cx + scaled(rx, SINE[(step + ELLIPSE_STEPS // 4) % ELLIPSE_STEPS]),
                    cy + scaled(ry, SINE[step]),
                )
            )
        for index, point in enumerate(points):
            following = points[(index + 1) % ELLIPSE_STEPS]
            if point == following:
                self.plot(*point)
            else:
                self.line(point[0], point[1], following[0], following[1])

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
            elif name == "CALL":
                self.run(args[0], depth + 1)
        return self.device


def render(gfx, picture_id, device=None):
    """Draw one picture and return the device it was drawn on."""
    return Renderer(gfx, device).run(picture_id)
