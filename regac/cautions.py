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
"""What is worth saying about a picture while it is being drawn.

Two things that are seen in the picture only if one knows to look:

- **A fill that got out.**  GAC's fill walks the column its seed is in, laying
  a row across at every step, and a gap of one pixel in a wall lets out one
  row and no more: a ray a pixel high, sticking out from the rows above and
  below it, as far as the next thing that stops it (doc/gac.md, the
  pictures).  That shape is what is looked for: a row of a fill that goes at
  least RAY pixels further, on one side, than the row above it and the row
  below it.
- **A fill that does nothing**, its seed on a pixel already set: the original
  does nothing there either, and it is always a mistake.

And what the picture costs in bytes of the database, which on the 464 is
counted.  How long it takes to draw is not guessed here: regac draw measures
it on the machine, in an emulator -- see measure.py.
"""

from .gfx import Renderer, SOURCE_WIDTH
from .opcodes import GFX_CMDS

FILLS = ("FILL", "BGFILL", "SHADE")
RAY = 8                         # how far a row has to stick out to be a ray


class Recording:
    """A device that remembers, for every fill, the row it laid at every
    height: the stretch from the first pixel to the last that the run could
    cover, found before it is laid, the way the fill itself finds it."""

    def __init__(self, device):
        self.device = device
        self.fills = {}         # step -> {y: (left, right)}
        self.now = None

    def __getattr__(self, name):
        return getattr(self.device, name)

    def start(self, step):
        self.now = self.fills.setdefault(step, {})

    def fill_run(self, x, y, pattern):
        if self.now is not None:
            left = x
            while left > 0 and not self.device.is_blocked(left - 1, y):
                left -= 1
            right = x
            while right < SOURCE_WIDTH - 1 and not self.device.is_blocked(right + 1, y):
                right += 1
            self.now[y] = (left, right)
        return self.device.fill_run(x, y, pattern)


def fills_of(ddb, picture, machine):
    """The rows every fill of a picture laid, by the step it is in the walk
    regac draw makes of the picture: {step: {y: (left, right)}}."""
    from .devices import device_for
    from .viewer import steps_of

    gfx = ddb.get("gfx") or {}
    device = Recording(device_for(machine, gfx, int(picture), ddb))
    renderer = Renderer({}, device)
    for step, (_, _, _, order) in enumerate(steps_of(gfx, int(picture))):
        if order[0] in FILLS:
            device.start(step)
        else:
            device.now = None
        if order[0] != "CALL":
            renderer.gfx = {"order": [order]}
            renderer.run("order")
    return device.fills


def rays(rows):
    """The rows of one fill that stick out as a ray: (y, left, right, side)."""
    out = []
    for y, (left, right) in sorted(rows.items()):
        near = [rows[n] for n in (y - 1, y + 1) if n in rows]
        if not near:
            continue
        if all(right - their_right >= RAY for _, their_right in near):
            out.append((y, left, right, "right"))
        elif all(their_left - left >= RAY for their_left, _ in near):
            out.append((y, left, right, "left"))
    return out


def picture_bytes(orders):
    """What a picture's orders take in the database: its length, and every
    order's code and numbers -- two bytes for the picture a CALL names, one for
    everything else.  Four more are its place in the index."""
    return 2 + sum(1 + (2 if order[0] == "CALL" else GFX_CMDS[order[0]][1])
                   for order in orders)


def cautions(ddb, picture, machine):
    """Every caution for a picture, as (step, what) -- the step being where in
    the walk of it, or None for the picture as a whole."""
    from .viewer import described, steps_of

    gfx = ddb.get("gfx") or {}
    steps = steps_of(gfx, int(picture))
    out = []
    for step, rows in sorted(fills_of(ddb, picture, machine).items()):
        order = described(steps[step])
        if not rows:
            out.append((step, f"{order}: fills nothing, its seed is on a "
                              f"pixel already set"))
        for y, left, right, side in rays(rows):
            reach = right if side == "right" else left
            out.append((step, f"{order}: got out at y {y}, {side} to x "
                              f"{reach}, by a gap a pixel high"))
    own = gfx.get(str(picture)) or []
    every = sum(picture_bytes(orders) + 4 for orders in gfx.values())
    out.append((None, f"#{picture} takes {picture_bytes(own) + 4} bytes; "
                      f"all the pictures, {every}"))
    return out
