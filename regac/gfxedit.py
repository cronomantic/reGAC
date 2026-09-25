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
"""A picture written back into its source, for regac draw.

What is drawn in the window becomes a line of the source, in the /GFX entry
of the picture, and a point dragged rewrites the numbers of its line.  The
source is the author's, so it is touched as little as a person would touch
it: one line in, one line out or one line rewritten, the indent of the lines
around it, the comment at the end of a line kept, the ends of line the file
already had.

It does not write where it cannot be sure what it is writing into: a picture
in another file, taken in by `.include`, is edited in that file; and one
whose entry keeps lines for some machines, with `.if`, is edited by hand,
because a line put in the middle of it would be for some machines and not
others without anybody having said so.
"""

import os

from .srcparse import SourceError, directive, parse_with_places

# Which numbers of an order are a point that can be dragged, as the places of
# the x and the y in the order.  An ellipse's second point is not a corner:
# it is how far the curve reaches from the centre -- see doc/gac.md.
POINTS = {
    "PLOT": ((1, 2),),
    "LINE": ((1, 2), (3, 4)),
    "RECT": ((1, 2), (3, 4)),
    "ELLIPSE": ((1, 2), (3, 4)),
    "FILL": ((1, 2),),
    "BGFILL": ((1, 2),),
    "SHADE": ((1, 2),),
}


def points_of(order):
    """The points of an order that can be dragged, in the order of POINTS."""
    return [(order[x], order[y]) for x, y in POINTS.get(order[0], ())]


def moved(order, which, point):
    """The order with its point `which` put at `point`."""
    out = list(order)
    x, y = POINTS[order[0]][which]
    out[x], out[y] = point
    return out


def written(order):
    return " ".join(str(part) for part in order)


class Picture:
    """One picture of a source file, as the lines it is written on.

    `why_not` says why it cannot be written into, and is None when it can.
    """

    def __init__(self, path, picture, machine=None):
        self.path = path
        self.picture = int(picture)
        self.why_not = None
        self.head = None
        self.orders = []
        if not path.lower().endswith(".gac"):
            self.why_not = "a JSON is only looked at: open the source to draw"
            return
        with open(path, encoding="utf-8", newline="") as f:
            self.text = f.read()
        self.newline = "\r\n" if "\r\n" in self.text else "\n"
        self.lines = self.text.split(self.newline)
        name = os.path.basename(path)
        try:
            _, places = parse_with_places(
                self.text, name, os.path.dirname(os.path.abspath(path)), machine)
        except SourceError as e:
            self.why_not = f"the source does not read: {e}"
            return
        place = places.get(self.picture)
        if place is None:
            self.why_not = f"there is no picture {self.picture} in the source"
            return
        files = {place["head"][0]} | {f for f, _ in place["orders"]}
        if files != {name}:
            other = sorted(files - {name}) or sorted(files)
            self.why_not = (f"picture {self.picture} is written in "
                            f"{other[0]}: open that one to draw in it")
            return
        self.head = place["head"][1]
        self.orders = [number for _, number in place["orders"]]
        at = self.head          # the line after the header, counted from one
        while at < len(self.lines):
            line = self.lines[at]
            said = line.strip()
            if said.startswith("#") or said.startswith("/"):
                break
            if directive(line) is not None:
                self.why_not = (f"picture {self.picture} keeps lines for some "
                                f"machines, with .if: draw in it by hand")
                return
            at += 1

    def indent(self, near):
        """The indent of the order line nearest to `near`, or two spaces."""
        for number in [near] + self.orders:
            if number is not None:
                line = self.lines[number - 1]
                return line[:len(line) - len(line.lstrip())]
        return "  "

    def inserted(self, index, text):
        """The source with a line put in so that it is order number `index`
        of the picture, counted from nought: after the order before it, or
        straight after the header."""
        after = self.orders[index - 1] if index > 0 else self.head
        near = self.orders[index - 1] if index > 0 else (
            self.orders[0] if self.orders else None)
        lines = list(self.lines)
        lines.insert(after, self.indent(near) + text.strip())
        return self.newline.join(lines)

    def deleted(self, index):
        lines = list(self.lines)
        del lines[self.orders[index] - 1]
        return self.newline.join(lines)

    def rewritten(self, index, text):
        """The source with order `index` saying `text`, its indent and its
        comment as they were."""
        lines = list(self.lines)
        line = lines[self.orders[index] - 1]
        indent = line[:len(line) - len(line.lstrip())]
        rest = line[len(indent):]
        tail = ""
        if ";" in rest:
            cut = rest.index(";")
            code = rest[:cut].rstrip()
            tail = rest[len(code):]
        lines[self.orders[index] - 1] = indent + text.strip() + tail
        return self.newline.join(lines)

    def write(self, text):
        with open(self.path, "w", encoding="utf-8", newline="") as f:
            f.write(text)
