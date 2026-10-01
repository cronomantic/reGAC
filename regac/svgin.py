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
"""An SVG made into the orders of a picture, for regac draw --import.

Decided by the user: what comes in is the outline of every shape, and only
that -- the fills are put in afterwards in the editor, where the seed and
its leaks can be seen -- and its colours are not looked at, because each
machine has a palette of its own and a colour of an SVG does not say which
of them it means.  The drawing is laid over the picture as --trace lays an
image: as big as it fits without being put out of shape, and centred.

GAC has straight lines, rectangles and ellipses and nothing else, so:

  - a rectangle and an ellipse that are not turned, and fit, are a RECT and
    an ELLIPSE, which cost less and are what the artwork of 1986 used;
  - every other curve -- a turned ellipse, the Béziers and the arcs of a
    path -- is cut into straight pieces, none of them further than half a
    pixel of the picture from the curve it stands for;
  - what reaches past the picture is cut at its edge, because the original
    would not cut it: it brings a point that is outside to the edge, which
    turns a line that leaves the picture into a different line.

Text, images and whatever else is not lines is left out, and said.
"""

import math
import re
import xml.etree.ElementTree as ET

from .gfx import MAX_Y, SOURCE_ROWS, SOURCE_WIDTH
from .i18n import _

# How far, in pixels of the picture, a straight piece may stray from the
# curve it stands for.
TOLERANCE = 0.5

# What holds things that are not drawn where they are written, or are not
# drawing at all.
NOT_DRAWN = {"defs", "symbol", "clipPath", "mask", "marker", "pattern",
             "linearGradient", "radialGradient", "style", "script", "title",
             "desc", "metadata", "filter"}
# Drawn, but not lines: left out, and said.
NOT_LINES = {"text", "image", "foreignObject"}
CONTAINERS = {"svg", "g", "a", "switch"}

IDENTITY = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
NUMBER = re.compile(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")
TRANSFORM = re.compile(r"(matrix|translate|scale|rotate|skewX|skewY)\s*\(([^)]*)\)")
# The handles of a quarter of a circle drawn as a Bézier.
QUARTER = 4 / 3 * (math.sqrt(2) - 1)


class Unreadable(ValueError):
    """An attribute whose value is not a number this understands."""


# -- the transforms -----------------------------------------------------------

def times(m, n):
    """The transform that is n and then m."""
    a, b, c, d, e, f = m
    p, q, r, s, t, u = n
    return (a * p + c * q, b * p + d * q, a * r + c * s, b * r + d * s,
            a * t + c * u + e, b * t + d * u + f)


def at(m, point):
    a, b, c, d, e, f = m
    x, y = point
    return (a * x + c * y + e, b * x + d * y + f)


def upright(m):
    """Whether a transform keeps the sides of a rectangle across and down,
    which is what a RECT and an ELLIPSE can be."""
    return abs(m[1]) < 1e-9 and abs(m[2]) < 1e-9


def transform_of(text):
    """The transform an attribute says, the first one listed applied last."""
    out = IDENTITY
    for name, args in TRANSFORM.findall(text or ""):
        v = [float(n) for n in NUMBER.findall(args)]
        if name == "matrix" and len(v) == 6:
            m = tuple(v)
        elif name == "translate" and v:
            m = (1, 0, 0, 1, v[0], v[1] if len(v) > 1 else 0)
        elif name == "scale" and v:
            m = (v[0], 0, 0, v[1] if len(v) > 1 else v[0], 0, 0)
        elif name == "rotate" and v:
            a = math.radians(v[0])
            m = (math.cos(a), math.sin(a), -math.sin(a), math.cos(a), 0, 0)
            if len(v) == 3:
                m = times(times((1, 0, 0, 1, v[1], v[2]), m),
                          (1, 0, 0, 1, -v[1], -v[2]))
        elif name == "skewX" and v:
            m = (1, 0, math.tan(math.radians(v[0])), 1, 0, 0)
        elif name == "skewY" and v:
            m = (1, math.tan(math.radians(v[0])), 0, 1, 0, 0)
        else:
            continue
        out = times(out, m)
    return out


# -- what a shape is ----------------------------------------------------------
#
# A shape is a path -- a list of pieces, each a start, its segments and
# whether it closes -- or, when it is not turned, a rectangle or an ellipse.
# A segment is ("L", end) or ("C", handle, handle, end): quadratics and arcs
# become cubics as they are read, because a cubic stays one under any
# transform and the cutting into straight pieces happens once at the end,
# in the picture's own pixels.

class Piece:
    def __init__(self, start):
        self.start = start
        self.segments = []
        self.closed = False

    def moved(self, m):
        out = Piece(at(m, self.start))
        out.closed = self.closed
        for seg in self.segments:
            out.segments.append((seg[0],) + tuple(at(m, p) for p in seg[1:]))
        return out

    def points(self):
        yield self.start
        for seg in self.segments:
            yield from seg[1:]


def quadratic(p0, q, p1):
    """A quadratic Bézier as the cubic that draws the same."""
    return ("C", (p0[0] + 2 / 3 * (q[0] - p0[0]), p0[1] + 2 / 3 * (q[1] - p0[1])),
            (p1[0] + 2 / 3 * (q[0] - p1[0]), p1[1] + 2 / 3 * (q[1] - p1[1])), p1)


def arc(p0, rx, ry, turned, large, sweep, p1):
    """An arc of a path as cubics, a quarter turn or less each.  The way from
    its two ends to its centre is the one in the SVG specification, F.6.5."""
    if p0 == p1:
        return []
    rx, ry = abs(rx), abs(ry)
    if rx == 0 or ry == 0:
        return [("L", p1)]
    phi = math.radians(turned)
    cos, sin = math.cos(phi), math.sin(phi)
    hx, hy = (p0[0] - p1[0]) / 2, (p0[1] - p1[1]) / 2
    x1, y1 = cos * hx + sin * hy, -sin * hx + cos * hy
    grow = x1 * x1 / (rx * rx) + y1 * y1 / (ry * ry)
    if grow > 1:                        # too small to reach: as small as reaches
        rx, ry = rx * math.sqrt(grow), ry * math.sqrt(grow)
    over = rx * rx * y1 * y1 + ry * ry * x1 * x1
    root = math.sqrt(max(0.0, (rx * rx * ry * ry - over) / over))
    if large == sweep:
        root = -root
    cx1, cy1 = root * rx * y1 / ry, -root * ry * x1 / rx
    cx = cos * cx1 - sin * cy1 + (p0[0] + p1[0]) / 2
    cy = sin * cx1 + cos * cy1 + (p0[1] + p1[1]) / 2

    def angle(ux, uy, vx, vy):
        return math.atan2(ux * vy - uy * vx, ux * vx + uy * vy)

    ux, uy = (x1 - cx1) / rx, (y1 - cy1) / ry
    vx, vy = (-x1 - cx1) / rx, (-y1 - cy1) / ry
    first = angle(1, 0, ux, uy)
    turn = angle(ux, uy, vx, vy)
    if not sweep and turn > 0:
        turn -= 2 * math.pi
    elif sweep and turn < 0:
        turn += 2 * math.pi
    return around(cx, cy, rx, ry, phi, first, turn, p1)


def around(cx, cy, rx, ry, phi, first, turn, end=None):
    """Cubics along an ellipse from angle `first`, `turn` round."""
    cos, sin = math.cos(phi), math.sin(phi)

    def point(t):
        return (cx + rx * math.cos(t) * cos - ry * math.sin(t) * sin,
                cy + rx * math.cos(t) * sin + ry * math.sin(t) * cos)

    def towards(t):
        return (-rx * math.sin(t) * cos - ry * math.cos(t) * sin,
                -rx * math.sin(t) * sin + ry * math.cos(t) * cos)

    count = max(1, math.ceil(abs(turn) / (math.pi / 2) - 1e-9))
    step = turn / count
    k = 4 / 3 * math.tan(step / 4)
    out = []
    for i in range(count):
        t0, t1 = first + i * step, first + (i + 1) * step
        a, b = point(t0), point(t1)
        da, db = towards(t0), towards(t1)
        if end is not None and i == count - 1:
            b = end
        out.append(("C", (a[0] + k * da[0], a[1] + k * da[1]),
                    (b[0] - k * db[0], b[1] - k * db[1]), b))
    return out


def ellipse_path(cx, cy, rx, ry):
    piece = Piece((cx + rx, cy))
    piece.segments = around(cx, cy, rx, ry, 0, 0, 2 * math.pi, (cx + rx, cy))
    piece.closed = True
    return [piece]


class Scanner:
    """The numbers, flags and letters of a path's d, one at a time."""

    def __init__(self, text):
        self.text = text
        self.i = 0

    def skip(self):
        while self.i < len(self.text) and self.text[self.i] in " \t\r\n,":
            self.i += 1

    def letter(self):
        self.skip()
        if self.i < len(self.text) and self.text[self.i].isalpha():
            self.i += 1
            return self.text[self.i - 1]
        return None

    def has_number(self):
        self.skip()
        return (self.i < len(self.text)
                and (self.text[self.i] in "+-." or self.text[self.i].isdigit()))

    def number(self):
        self.skip()
        found = NUMBER.match(self.text, self.i)
        if not found:
            raise Unreadable(self.text[self.i:self.i + 10])
        self.i = found.end()
        return float(found.group())

    def flag(self):
        """An arc's flag, which may be written with nothing after it."""
        self.skip()
        if self.i < len(self.text) and self.text[self.i] in "01":
            self.i += 1
            return self.text[self.i - 1] == "1"
        raise Unreadable(self.text[self.i:self.i + 10])


def path_of(d):
    """The pieces a path's d draws."""
    s = Scanner(d or "")
    pieces = []
    here = start = (0.0, 0.0)
    piece = None
    handle = None                       # the last cubic or quadratic handle
    previous = None                     # which of the two, for S and T
    command = None
    while True:
        letter = s.letter()
        if letter is None:
            if s.i >= len(s.text):
                break
            if command is None or not s.has_number():
                raise Unreadable(s.text[s.i:s.i + 10])
            letter = command            # more numbers for the same command
        command = letter
        up = letter.upper()
        rel = letter.islower()

        def pt(x, y):
            return (here[0] + x, here[1] + y) if rel else (x, y)

        if up == "Z":
            if piece is not None:
                piece.closed = True
            here = start
            piece = None
            previous = None
            command = None
            continue
        if up == "M":
            here = start = pt(s.number(), s.number())
            piece = Piece(start)
            pieces.append(piece)
            command = "l" if rel else "L"   # what numbers after it are
            previous = None
            continue
        if piece is None:               # drawing on after a Z
            piece = Piece(here)
            pieces.append(piece)
        if up == "L":
            here = pt(s.number(), s.number())
            piece.segments.append(("L", here))
            previous = None
        elif up == "H":
            x = s.number()
            here = (here[0] + x if rel else x, here[1])
            piece.segments.append(("L", here))
            previous = None
        elif up == "V":
            y = s.number()
            here = (here[0], here[1] + y if rel else y)
            piece.segments.append(("L", here))
            previous = None
        elif up in "CS":
            if up == "C":
                h1 = pt(s.number(), s.number())
            else:
                h1 = ((2 * here[0] - handle[0], 2 * here[1] - handle[1])
                      if previous == "C" else here)
            h2 = pt(s.number(), s.number())
            end = pt(s.number(), s.number())
            piece.segments.append(("C", h1, h2, end))
            handle, previous, here = h2, "C", end
        elif up in "QT":
            if up == "Q":
                q = pt(s.number(), s.number())
            else:
                q = ((2 * here[0] - handle[0], 2 * here[1] - handle[1])
                     if previous == "Q" else here)
            end = pt(s.number(), s.number())
            piece.segments.append(quadratic(here, q, end))
            handle, previous, here = q, "Q", end
        elif up == "A":
            rx, ry, turned = s.number(), s.number(), s.number()
            large, sweep = s.flag(), s.flag()
            end = pt(s.number(), s.number())
            piece.segments += arc(here, rx, ry, turned, large, sweep, end)
            here = end
            previous = None
        else:
            raise Unreadable(letter)
    return pieces


def numbers(text):
    return [float(n) for n in NUMBER.findall(text or "")]


def length(element, name, default=0.0):
    """A coordinate or a size, in the drawing's own units."""
    value = element.get(name)
    if value is None:
        return default
    said = value.strip()
    if said.endswith("px"):
        said = said[:-2].strip()
    try:
        return float(said)
    except ValueError:
        raise Unreadable(f'{name}="{value}"') from None


def hidden(element):
    style = dict(part.split(":", 1) for part in (element.get("style") or "")
                 .split(";") if ":" in part)
    style = {k.strip(): v.strip() for k, v in style.items()}
    display = style.get("display", element.get("display"))
    visibility = style.get("visibility", element.get("visibility"))
    return display == "none" or visibility in ("hidden", "collapse")


def tag_of(element):
    """The name of an element without its namespace; None for one of
    another namespace, which an editor keeps for itself."""
    tag = element.tag
    if not isinstance(tag, str):
        return None                     # a comment
    if tag.startswith("{"):
        space, name = tag[1:].split("}", 1)
        return name if space == "http://www.w3.org/2000/svg" else None
    return tag


# -- reading the drawing --------------------------------------------------------

class Reading:
    """What the shapes of a drawing are, in its own units, and what was left
    out of it."""

    def __init__(self, root):
        self.shapes = []                # ("path", pieces), ("rect"...), ("ellipse"...)
        self.left_out = {}              # what was said, and how many times
        self.ids = {el.get("id"): el for el in root.iter() if el.get("id")}

    def say(self, text):
        self.left_out[text] = self.left_out.get(text, 0) + 1

    def walk(self, element, m, depth=0):
        tag = tag_of(element)
        if tag is None or tag in NOT_DRAWN or hidden(element):
            return
        if tag in NOT_LINES:
            self.say(_("left out, as it is not lines: {what}", what=tag))
            return
        m = times(m, transform_of(element.get("transform")))
        try:
            if tag in CONTAINERS:
                for child in element:
                    self.walk(child, m, depth)
            elif tag == "use":
                self.use(element, m, depth)
            else:
                self.shape(tag, element, m)
        except Unreadable as e:
            self.say(_("left out, as it does not read: a {what} with {where}",
                       what=tag, where=e))

    def use(self, element, m, depth):
        href = element.get("href") or element.get(
            "{http://www.w3.org/1999/xlink}href") or ""
        target = self.ids.get(href[1:]) if href.startswith("#") else None
        if target is None or depth > 16:
            self.say(_("left out: a use of {what}, which is not there",
                       what=href or "?"))
            return
        m = times(m, (1, 0, 0, 1, length(element, "x"), length(element, "y")))
        if tag_of(target) == "symbol":   # drawn only where a use puts it
            for child in target:
                self.walk(child, m, depth + 1)
        else:
            self.walk(target, m, depth + 1)

    def shape(self, tag, el, m):
        if tag == "line":
            piece = Piece((length(el, "x1"), length(el, "y1")))
            piece.segments.append(("L", (length(el, "x2"), length(el, "y2"))))
            self.path([piece], m)
        elif tag in ("polyline", "polygon"):
            v = numbers(el.get("points"))
            if len(v) < 2:
                return
            piece = Piece((v[0], v[1]))
            piece.segments = [("L", (v[i], v[i + 1]))
                              for i in range(2, len(v) - 1, 2)]
            piece.closed = tag == "polygon"
            self.path([piece], m)
        elif tag == "rect":
            self.rect(el, m)
        elif tag == "circle":
            r = length(el, "r")
            self.ellipse(length(el, "cx"), length(el, "cy"), r, r, m)
        elif tag == "ellipse":
            self.ellipse(length(el, "cx"), length(el, "cy"),
                         length(el, "rx"), length(el, "ry"), m)
        elif tag == "path":
            self.path(path_of(el.get("d")), m)
        # anything else of the SVG namespace is not a shape, and draws nothing

    def path(self, pieces, m):
        if pieces:
            self.shapes.append(("path", [p.moved(m) for p in pieces]))

    def rect(self, el, m):
        x, y = length(el, "x"), length(el, "y")
        w, h = length(el, "width"), length(el, "height")
        if w <= 0 or h <= 0:
            return
        rx = el.get("rx")
        ry = el.get("ry")
        rx = length(el, "rx") if rx is not None else None
        ry = length(el, "ry") if ry is not None else None
        rx = ry if rx is None else rx
        ry = rx if ry is None else ry
        rx, ry = min(rx or 0.0, w / 2), min(ry or 0.0, h / 2)
        if rx <= 0 or ry <= 0:
            if upright(m):
                (x0, y0), (x1, y1) = at(m, (x, y)), at(m, (x + w, y + h))
                self.shapes.append(("rect", min(x0, x1), min(y0, y1),
                                    max(x0, x1), max(y0, y1)))
                return
            piece = Piece((x, y))
            piece.segments = [("L", (x + w, y)), ("L", (x + w, y + h)),
                              ("L", (x, y + h))]
        else:                           # rounded: four sides, four quarters
            piece = Piece((x + rx, y))
            piece.segments.append(("L", (x + w - rx, y)))
            piece.segments += arc((x + w - rx, y), rx, ry, 0, False, True,
                                  (x + w, y + ry))
            piece.segments.append(("L", (x + w, y + h - ry)))
            piece.segments += arc((x + w, y + h - ry), rx, ry, 0, False, True,
                                  (x + w - rx, y + h))
            piece.segments.append(("L", (x + rx, y + h)))
            piece.segments += arc((x + rx, y + h), rx, ry, 0, False, True,
                                  (x, y + h - ry))
            piece.segments.append(("L", (x, y + ry)))
            piece.segments += arc((x, y + ry), rx, ry, 0, False, True,
                                  (x + rx, y))
        piece.closed = True
        self.path([piece], m)

    def ellipse(self, cx, cy, rx, ry, m):
        if rx <= 0 or ry <= 0:
            return
        if upright(m):
            centre = at(m, (cx, cy))
            self.shapes.append(("ellipse", centre[0], centre[1],
                                abs(rx * m[0]), abs(ry * m[3])))
        else:
            self.path(ellipse_path(cx, cy, rx, ry), m)

    def bounds(self):
        xs, ys = [], []
        for shape in self.shapes:
            if shape[0] == "path":
                for piece in shape[1]:
                    for x, y in piece.points():
                        xs.append(x)
                        ys.append(y)
            elif shape[0] == "rect":
                xs += [shape[1], shape[3]]
                ys += [shape[2], shape[4]]
            else:
                xs += [shape[1] - shape[3], shape[1] + shape[3]]
                ys += [shape[2] - shape[4], shape[2] + shape[4]]
        if not xs:
            return None
        return min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)


def canvas_of(root):
    """The area of the drawing that is laid over the picture: its viewBox,
    or its width and height, or None to go by what is drawn."""
    box = numbers(root.get("viewBox"))
    if len(box) == 4 and box[2] > 0 and box[3] > 0:
        return tuple(box)
    try:
        w, h = length(root, "width", None), length(root, "height", None)
    except Unreadable:                  # in mm, or a percentage
        return None
    if w and h and w > 0 and h > 0:
        return (0.0, 0.0, w, h)
    return None


# -- into the picture -----------------------------------------------------------

def flattened(piece):
    """The points a piece goes through, its curves cut into straight pieces
    no further than TOLERANCE from them.  In the picture's pixels."""
    out = [piece.start]
    here = piece.start
    for seg in piece.segments:
        if seg[0] == "L":
            out.append(seg[1])
        else:
            cut(here, seg[1], seg[2], seg[3], out, 0)
        here = seg[-1]
    if piece.closed and out[-1] != out[0]:
        out.append(out[0])
    return out


def cut(p0, p1, p2, p3, out, depth):
    """A cubic as straight pieces, halving it until both handles are near
    enough the line between its ends."""
    if depth >= 16 or (off_line(p1, p0, p3) <= TOLERANCE
                       and off_line(p2, p0, p3) <= TOLERANCE):
        out.append(p3)
        return
    mid = lambda a, b: ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)  # noqa: E731
    a, b, c = mid(p0, p1), mid(p1, p2), mid(p2, p3)
    d, e = mid(a, b), mid(b, c)
    f = mid(d, e)
    cut(p0, a, d, f, out, depth + 1)
    cut(f, e, c, p3, out, depth + 1)


def off_line(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    size = math.hypot(dx, dy)
    if size < 1e-12:
        return math.hypot(p[0] - a[0], p[1] - a[1])
    return abs((p[0] - a[0]) * dy - (p[1] - a[1]) * dx) / size


def clipped(a, b):
    """The part of the line from a to b inside the picture, Liang-Barsky, or
    None; and whether anything was cut off it."""
    (x0, y0), (x1, y1) = a, b
    dx, dy = x1 - x0, y1 - y0
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, x0), (dx, SOURCE_WIDTH - x0),
                 (-dy, y0), (dy, SOURCE_ROWS - y0)):
        if abs(p) < 1e-12:
            if q < 0:
                return None, True
            continue
        t = q / p
        if p < 0:
            t0 = max(t0, t)
        else:
            t1 = min(t1, t)
        if t0 > t1:
            return None, True
    cut_off = t0 > 1e-9 or t1 < 1 - 1e-9
    return ((x0 + t0 * dx, y0 + t0 * dy), (x0 + t1 * dx, y0 + t1 * dy)), cut_off


def pixel(point, far=(SOURCE_WIDTH, SOURCE_ROWS)):
    """Where a point of the picture's area falls, as the orders count it:
    x across, y up from the bottom of the screen.

    A pixel is the square from its number to the next, so a point on the
    line between two goes to the one after it -- except on the far side of
    the drawing, `far`, where the one after it is not the drawing's any
    more: a rectangle round the whole of it is round the pixels it covers."""
    x, row = point
    if abs(x - far[0]) < 1e-6:
        x -= 0.5
    if abs(row - far[1]) < 1e-6:
        row -= 0.5
    x = min(max(int(math.floor(x)), 0), SOURCE_WIDTH - 1)
    row = min(max(int(math.floor(row)), 0), SOURCE_ROWS - 1)
    return x, MAX_Y - row


def imported(path):
    """The orders an SVG draws, as lists like the ones a source reads into,
    and what was left out of it, a sentence each."""
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError) as e:
        raise ValueError(_("{file} does not read as an SVG: {error}",
                           file=path, error=e)) from None
    if tag_of(root) != "svg":
        raise ValueError(_("{file} is not an SVG", file=path))
    reading = Reading(root)
    reading.walk(root, IDENTITY)
    canvas = canvas_of(root) or reading.bounds()
    if canvas is None:
        return [], said(reading.left_out)
    x0, y0, w, h = canvas
    if w <= 0 or h <= 0:                # everything on one line, or one point
        w, h = max(w, 1e-9), max(h, 1e-9)
    scale = min(SOURCE_WIDTH / w, SOURCE_ROWS / h)
    fit = (scale, 0.0, 0.0, scale,
           (SOURCE_WIDTH - w * scale) / 2 - x0 * scale,
           (SOURCE_ROWS - h * scale) / 2 - y0 * scale)
    far = ((SOURCE_WIDTH + w * scale) / 2, (SOURCE_ROWS + h * scale) / 2)

    def spot(point):
        return pixel(point, far)

    orders, seen, cuts = [], set(), [0]

    def put(order):
        key = tuple(order)
        if order[0] == "LINE":
            ends = sorted([tuple(order[1:3]), tuple(order[3:5])])
            key = ("LINE",) + ends[0] + ends[1]
        if key not in seen:
            seen.add(key)
            orders.append(order)

    def lines(pieces):
        for piece in pieces:
            points = flattened(piece.moved(fit))
            drawn = False
            for a, b in zip(points, points[1:]):
                part, cut_off = clipped(a, b)
                cuts[0] += cut_off
                if part is None:
                    continue
                p, q = spot(part[0]), spot(part[1])
                if p != q:
                    put(["LINE", p[0], p[1], q[0], q[1]])
                    drawn = True
            if not drawn:               # all of it inside one pixel
                inside = [p for p in points
                          if 0 <= p[0] <= SOURCE_WIDTH and 0 <= p[1] <= SOURCE_ROWS]
                if inside:
                    put(["PLOT", *spot(inside[0])])

    for shape in reading.shapes:
        kind = shape[0]
        if kind == "path":
            lines(shape[1])
        elif kind == "rect":
            (ax, ay), (bx, by) = at(fit, shape[1:3]), at(fit, shape[3:5])
            if (ax >= -1e-9 and ay >= -1e-9 and bx <= SOURCE_WIDTH + 1e-9
                    and by <= SOURCE_ROWS + 1e-9):
                left, top = spot((ax, ay))
                right, bottom = spot((bx, by))
                put(["RECT", left, top, right, bottom])
            else:
                piece = Piece(shape[1:3])
                piece.segments = [("L", (shape[3], shape[2])),
                                  ("L", (shape[3], shape[4])),
                                  ("L", (shape[1], shape[4]))]
                piece.closed = True
                lines([piece])
        else:
            _kind, cx, cy, rx, ry = shape
            x, y = spot(at(fit, (cx, cy)))
            across, up = round(rx * scale), round(ry * scale)
            if (x - across >= 0 and x + across <= SOURCE_WIDTH - 1
                    and y - up >= MAX_Y - SOURCE_ROWS + 1 and y + up <= MAX_Y):
                put(["ELLIPSE", x, y, x + across, y + up] if across or up
                    else ["PLOT", x, y])
            else:
                lines(ellipse_path(cx, cy, rx, ry))
    if cuts[0]:
        reading.say(_("lines cut at the edge of the picture, as they reached "
                      "past it: {count}", count=cuts[0]))
    return orders, said(reading.left_out)


def said(left_out):
    """What was left out, a sentence each, with how many times when it was
    more than one."""
    return [text if count == 1 else _("{what} (x{count})", what=text,
                                      count=count)
            for text, count in left_out.items()]
