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
"""Renderer for the vector graphics of a GAC adventure.

The adventures store each picture as a short list of drawing commands.  This
module turns that list into a plain bitmap plus a colour attribute per 8x8
cell, which is the shape every target machine can then paint in its own way.

Coordinates are the ones the Spectrum used: x from 0 to 255 left to right, y
from 0 at the bottom of the screen to 175 at the top.  The pictures occupy the
top sixteen character rows, leaving the bottom eight for text.

Colour values follow the same conventions BASIC used: 8 means leave the current
colour alone and 9 means pick black or white for contrast.
"""

SCREEN_WIDTH = 256
SCREEN_HEIGHT = 192
CHAR_WIDTH = SCREEN_WIDTH // 8
CHAR_HEIGHT = SCREEN_HEIGHT // 8
PICTURE_ROWS = 128  # the top sixteen character rows
MAX_Y = 175  # y=175 is the top pixel row

TRANSPARENT = 8
CONTRAST = 9
SHADE_PATTERN = 0  # checkerboard, see shaded()


def shaded(x, y):
    """The dither SHADE paints: every other pixel of every other row."""
    return (x + y) & 1 == SHADE_PATTERN


class Picture:
    """A bitmap and its colour attributes, in the linear layout the frontends
    use: one bit per pixel, `CHAR_WIDTH` bytes per row."""

    def __init__(self):
        self.pixels = bytearray(CHAR_WIDTH * SCREEN_HEIGHT)
        self.attrs = bytearray([0x38] * (CHAR_WIDTH * CHAR_HEIGHT))
        self.border = 0

    def get(self, x, y):
        if not (0 <= x < SCREEN_WIDTH and 0 <= y < PICTURE_ROWS):
            return 1  # outside the picture counts as a boundary
        return (self.pixels[y * CHAR_WIDTH + (x >> 3)] >> (7 - (x & 7))) & 1

    def set(self, x, y, on=True):
        if not (0 <= x < SCREEN_WIDTH and 0 <= y < PICTURE_ROWS):
            return
        index = y * CHAR_WIDTH + (x >> 3)
        mask = 1 << (7 - (x & 7))
        if on:
            self.pixels[index] |= mask
        else:
            self.pixels[index] &= 0xFF ^ mask

    def set_attr(self, x, y, attr):
        if not (0 <= x < SCREEN_WIDTH and 0 <= y < PICTURE_ROWS):
            return
        self.attrs[(y >> 3) * CHAR_WIDTH + (x >> 3)] = attr


class Renderer:
    """Runs the drawing commands of one picture over a `Picture`."""

    MAX_DEPTH = 8  # a picture may call others; stop runaway recursion

    def __init__(self, gfx, picture=None):
        self.gfx = gfx  # id -> list of commands
        self.pic = picture or Picture()
        self.ink = 0
        self.paper = 7
        self.bright = 0
        self.flash = 0

    # -- colour -------------------------------------------------------------

    def attr_at(self, x, y):
        """The attribute to write at a point, honouring transparency."""
        current = self.pic.attrs[(y >> 3) * CHAR_WIDTH + (x >> 3)]
        ink = current & 7 if self.ink >= TRANSPARENT else self.ink
        paper = (current >> 3) & 7 if self.paper >= TRANSPARENT else self.paper
        bright = (current >> 6) & 1 if self.bright >= TRANSPARENT else self.bright
        flash = (current >> 7) & 1 if self.flash >= TRANSPARENT else self.flash
        if self.ink == CONTRAST:
            ink = 0 if paper >= 4 else 7
        return ink | (paper << 3) | (bright << 6) | (flash << 7)

    def paint(self, x, y):
        self.pic.set_attr(x, y, self.attr_at(x, y))

    # -- primitives ---------------------------------------------------------

    @staticmethod
    def to_screen(y):
        return MAX_Y - y

    def plot(self, x, y, on=True):
        self.pic.set(x, y, on)
        self.paint(x, y)

    def line(self, x0, y0, x1, y1):
        """Bresenham, in screen coordinates."""
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            self.plot(x0, y0)
            if x0 == x1 and y0 == y1:
                return
            err2 = 2 * err
            if err2 >= dy:
                err += dy
                x0 += sx
            if err2 <= dx:
                err += dx
                y0 += sy

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
        """An ellipse inscribed in the given box, drawn by midpoint stepping."""
        if x0 > x1:
            x0, x1 = x1, x0
        if y0 > y1:
            y0, y1 = y1, y0
        cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
        rx, ry = (x1 - x0) / 2.0, (y1 - y0) / 2.0
        if rx < 1 or ry < 1:
            self.line(x0, y0, x1, y1)
            return
        steps = int(max(rx, ry) * 8) or 1
        from math import cos, pi, sin

        prev = None
        for step in range(steps + 1):
            angle = 2 * pi * step / steps
            point = (int(round(cx + rx * cos(angle))), int(round(cy + ry * sin(angle))))
            if prev is not None and prev != point:
                self.line(prev[0], prev[1], point[0], point[1])
            elif prev is None:
                self.plot(*point)
            prev = point

    def flood(self, x, y, mode):
        """Flood the area around a point, bounded by pixels already set.

        `mode` is "ink" to fill it solid, "paper" to leave the pixels clear and
        only recolour the cells, or "shade" to fill it with a dither.
        """
        if self.pic.get(x, y):
            return
        seen = set()
        stack = [(x, y)]
        while stack:
            px, py = stack.pop()
            if (px, py) in seen or self.pic.get(px, py):
                continue
            # walk the whole run of clear pixels on this row
            left = px
            while left > 0 and not self.pic.get(left - 1, py):
                left -= 1
            right = px
            while right < SCREEN_WIDTH - 1 and not self.pic.get(right + 1, py):
                right += 1
            for sx in range(left, right + 1):
                seen.add((sx, py))
                self.paint(sx, py)
                if mode == "paper":
                    self.pic.set(sx, py, False)
                elif mode == "shade" and shaded(sx, py):
                    self.pic.set(sx, py, True)
            for ny in (py - 1, py + 1):
                if 0 <= ny < PICTURE_ROWS:
                    for sx in range(left, right + 1):
                        if (sx, ny) not in seen and not self.pic.get(sx, ny):
                            stack.append((sx, ny))
        return

    # -- command dispatch ---------------------------------------------------

    def run(self, picture_id, depth=0):
        commands = self.gfx.get(picture_id) or self.gfx.get(str(picture_id))
        if commands is None or depth > self.MAX_DEPTH:
            return self.pic
        y = self.to_screen
        for command in commands:
            name = command[0]
            args = command[1:]
            if name == "BORDER":
                self.pic.border = args[0] & 7
            elif name == "INK":
                self.ink = args[0]
            elif name == "PAPER":
                self.paper = args[0]
            elif name == "BRIGHT":
                self.bright = args[0]
            elif name == "FLASH":
                self.flash = args[0]
            elif name == "PLOT":
                self.plot(args[0], y(args[1]))
            elif name == "LINE":
                self.line(args[0], y(args[1]), args[2], y(args[3]))
            elif name == "RECT":
                self.rect(args[0], y(args[1]), args[2], y(args[3]))
            elif name == "ELLIPSE":
                self.ellipse(args[0], y(args[1]), args[2], y(args[3]))
            elif name == "FILL":
                self.flood(args[0], y(args[1]), "ink")
            elif name == "BGFILL":
                self.flood(args[0], y(args[1]), "paper")
            elif name == "SHADE":
                self.flood(args[0], y(args[1]), "shade")
            elif name == "CALL":
                self.run(args[0], depth + 1)
        return self.pic


def render(gfx, picture_id):
    """Draw one picture and return it."""
    return Renderer(gfx).run(picture_id)
