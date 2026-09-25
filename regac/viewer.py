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
"""A picture on the screen while it is being written.

`regac draw aventura.gac 12` opens picture 12 in a window and draws it again
every time the source is saved, so a picture is written in the editor and
looked at here, side by side.  It is drawn by the same renderer `regac render`
uses, the one the interpreters are held to, on the device of the machine
chosen: what is seen is what that machine shows.

It can be walked an order at a time, the pixels the last order laid lit up, so
that a fill that got out through a gap says where it got out.  An order that
calls another picture is opened where it stands, and the orders of the one
called are walked in their turn.  And the pointer says where it is in the
coordinates the orders are written in, x from the left and y from the bottom.

Everything but the window is here without pygame, so that it can be tested
without one: `Steps` is the walking, `Viewer` what the keys do to it, and
`run` the window.
"""

import copy
import json
import os

from .devices import device_for, from_an_amstrad
from .gfx import MAX_Y, SOURCE_ROWS, SOURCE_WIDTH, Renderer

# The machines a picture can be looked at on: the ones there is an
# interpreter for, by the name of their device.  The PC's is its CGA.  An
# adventure off an Amstrad is drawn only where the Amstrad's rules are.
SPECTRUM_MACHINES = ("spectrum", "cpc", "msx", "pcw", "next", "cga")
AMSTRAD_MACHINES = ("cpc", "next", "cga")
# What each is called when the source is read for it, which is what its
# `.if` lines are asked against: the same the build asks with.
SOURCE_LABEL = {"spectrum": "spectrum48", "cpc": "cpc", "msx": "msx",
                "pcw": "pcw", "next": "next", "cga": "pc"}

HIGHLIGHT = (255, 0, 255)       # what the last order laid is lit up in


def machines_for(ddb):
    return AMSTRAD_MACHINES if from_an_amstrad(ddb) else SPECTRUM_MACHINES


def pictures_of(ddb):
    return sorted((ddb.get("gfx") or {}), key=int)


def steps_of(gfx, picture_id, depth=0):
    """Every order a picture runs, in the order it runs them, with the orders
    of a picture it calls opened after the CALL: (depth, picture, number,
    order) each.  How deep a call may go is the renderer's own limit, so what
    this walks is what the renderer draws."""
    orders = gfx.get(str(picture_id))
    if orders is None or depth > Renderer.MAX_DEPTH:
        return []
    out = []
    for number, order in enumerate(orders, start=1):
        out.append((depth, int(picture_id), number, order))
        if order[0] == "CALL":
            out += steps_of(gfx, order[1], depth + 1)
    return out


def gac_point(x, y, width, height):
    """Where a point of a view `width` by `height` falls, in the coordinates
    the orders are written in; None off the picture."""
    if not (0 <= x < width and 0 <= y < height):
        return None
    return x * SOURCE_WIDTH // width, MAX_Y - y * SOURCE_ROWS // height


def read_adventure(path, machine):
    """An adventure out of a source, read for that machine, or out of a
    JSON, which has nothing kept back for any machine."""
    if path.lower().endswith(".json"):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    from .srcparse import parse

    with open(path, encoding="utf-8") as f:
        text = f.read()
    ddb = parse(text, os.path.basename(path),
                os.path.dirname(os.path.abspath(path)),
                machine=SOURCE_LABEL.get(machine, machine))
    # through JSON and back, so that it is the same as one read from a file:
    # a source numbers its pictures with numbers, a JSON with strings
    return json.loads(json.dumps(ddb))


class Steps:
    """One picture on one machine, drawn as far as some order and no
    further.

    Going forward draws the next orders on what is there; going back starts
    again from a clean device, because a fill cannot be taken back.  The
    clean device is made once and copied: for a machine short of inks,
    making one means choosing its inks, which draws the whole picture.
    """

    def __init__(self, ddb, picture_id, machine):
        self.gfx = ddb.get("gfx") or {}
        self.picture = int(picture_id)
        self.steps = steps_of(self.gfx, self.picture)
        self.clean = device_for(machine, self.gfx, self.picture, ddb)
        self.count = 0
        self.before = None              # the colours before the last order
        self.restart()

    def restart(self):
        self.renderer = Renderer({}, copy.deepcopy(self.clean))
        self.count = 0
        self.before = None

    def _one(self):
        order = self.steps[self.count][3]
        self.count += 1
        if order[0] != "CALL":          # what it calls comes next, opened
            self.renderer.gfx = {"order": [order]}
            self.renderer.run("order")

    def go(self, count):
        """Drawn as far as that many orders, and the colours before the last
        of them kept, to say what it laid."""
        count = max(0, min(count, len(self.steps)))
        if count < self.count:
            self.restart()
        while self.count < count - 1:
            self._one()
        if self.count < count:
            self.before = self.device.to_rgb()
            self._one()
        elif count == 0:
            self.before = None

    @property
    def device(self):
        return self.renderer.device

    def rgb(self):
        return self.device.to_rgb()

    def laid(self):
        """The points the last order changed, in the device's own pixels."""
        if self.before is None:
            return set()
        now = self.rgb()
        return {(x, y) for y, (was, row) in enumerate(zip(self.before, now))
                for x, (a, b) in enumerate(zip(was, row)) if a != b}


def described(step):
    """An order the way it is written, and where it comes from if it was
    called."""
    depth, picture, number, order = step
    words = " ".join(str(part) for part in order)
    if depth:
        return f"{words}    (#{picture}, order {number}, called {depth} deep)"
    return words


class Viewer:
    """What is being looked at, and what the keys do to it.  Nothing here
    draws: `run` does, from what this says."""

    def __init__(self, path, picture=None, machine=None):
        self.path = path
        self.error = None
        self.ddb = None
        self.machine = machine
        self.picture = picture
        self.highlight = True
        self.stamp = None
        self.steps = None
        self.reload()
        if self.ddb is None:
            raise ValueError(self.error)

    # -- the file ---------------------------------------------------------

    def watched(self):
        """The source and everything beside it that it could have taken in:
        a change to an included file has to redraw as much as one to the
        source."""
        folder = os.path.dirname(os.path.abspath(self.path))
        names = [os.path.abspath(self.path)]
        for name in sorted(os.listdir(folder)):
            if name.lower().endswith(".gac"):
                names.append(os.path.join(folder, name))
        out = []
        for name in names:
            try:
                out.append((name, os.stat(name).st_mtime_ns))
            except OSError:
                pass
        return tuple(out)

    def changed(self):
        """Read it again if it was saved since; whether it was."""
        if self.watched() == self.stamp:
            return False
        self.reload()
        return True

    def reload(self):
        """Read the adventure again, and keep the picture that was there if
        this one does not read: a source half written is the usual case."""
        self.stamp = self.watched()
        machine = self.machine or "spectrum"
        try:
            ddb = read_adventure(self.path, machine)
        except Exception as e:          # whatever the source says is wrong
            self.error = str(e)
            return
        self.error = None
        first = self.ddb is None
        self.ddb = ddb
        if self.machine not in machines_for(ddb):
            self.machine = machines_for(ddb)[0]
            if machine != self.machine:  # read for the one it will be drawn on
                return self.reload()
        pictures = pictures_of(ddb)
        if not pictures:
            self.error = "the adventure has no pictures"
            self.steps = None
            return
        if self.picture is None or str(self.picture) not in pictures:
            if not first and self.picture is not None:
                self.error = f"there is no picture {self.picture} any more"
            self.picture = int(pictures[0])
        at_the_end = first or self.steps is None or \
            self.steps.count == len(self.steps.steps)
        count = None if at_the_end else self.steps.count
        self.show(count)

    def show(self, count=None):
        """The picture on the machine, drawn to that order, or whole."""
        self.steps = Steps(self.ddb, self.picture, self.machine)
        self.steps.go(len(self.steps.steps) if count is None else count)

    # -- the keys ---------------------------------------------------------

    def step(self, by):
        self.steps.go(self.steps.count + by)

    def first(self):
        self.steps.go(0)

    def last(self):
        self.steps.go(len(self.steps.steps))

    def other_picture(self, by):
        pictures = pictures_of(self.ddb)
        at = pictures.index(str(self.picture))
        self.picture = int(pictures[(at + by) % len(pictures)])
        self.show()

    def other_machine(self, by):
        machines = machines_for(self.ddb)
        at = machines.index(self.machine)
        self.machine = machines[(at + by) % len(machines)]
        count = self.steps.count
        try:
            self.ddb = read_adventure(self.path, self.machine)
        except Exception as e:          # what it says for this machine
            self.error = str(e)
        self.show(count)

    # -- what is said about it --------------------------------------------

    def lines(self, pointer=None):
        """What goes under the picture, a line each."""
        steps = self.steps
        out = [f"#{self.picture} on {'pc' if self.machine == 'cga' else self.machine}"
               f"    order {steps.count} of {len(steps.steps)}"]
        if steps.count:
            out.append("last: " + described(steps.steps[steps.count - 1]))
        else:
            out.append("last: nothing drawn yet")
        if steps.count < len(steps.steps):
            out.append("next: " + described(steps.steps[steps.count]))
        else:
            out.append("next: the picture is finished")
        out.append(f"x {pointer[0]}  y {pointer[1]}" if pointer else "")
        return out


KEYS_HELP = ("left/right an order (shift ten, ctrl a hundred)  home/end  "
             "page up/down a picture  m machine  h light  q quit")


def run(path, picture=None, machine=None, scale=3):
    """The window, until it is closed."""
    import pygame

    viewer = Viewer(path, picture, machine)
    pygame.init()
    pygame.key.set_repeat(300, 40)
    width, height = SOURCE_WIDTH * scale, SOURCE_ROWS * scale
    font = pygame.font.Font(None, 22)
    line = font.get_linesize()
    panel = line * 6 + 8
    screen = pygame.display.set_mode((width, height + panel))
    pygame.display.set_caption(f"regac draw {os.path.basename(path)}")
    clock = pygame.time.Clock()
    pointer = None
    drawn = None                        # what the window was drawn from
    idle = 0
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return
            if event.type == pygame.MOUSEMOTION:
                pointer = gac_point(*event.pos, width, height)
            if event.type != pygame.KEYDOWN:
                continue
            shift = event.mod & pygame.KMOD_SHIFT
            stride = 100 if event.mod & pygame.KMOD_CTRL else 10 if shift else 1
            key = event.key
            if key in (pygame.K_q, pygame.K_ESCAPE):
                pygame.quit()
                return
            elif key == pygame.K_RIGHT:
                viewer.step(stride)
            elif key == pygame.K_LEFT:
                viewer.step(-stride)
            elif key == pygame.K_HOME:
                viewer.first()
            elif key == pygame.K_END:
                viewer.last()
            elif key == pygame.K_PAGEDOWN:
                viewer.other_picture(1)
            elif key == pygame.K_PAGEUP:
                viewer.other_picture(-1)
            elif key == pygame.K_m:
                viewer.other_machine(-1 if shift else 1)
            elif key == pygame.K_h:
                viewer.highlight = not viewer.highlight
            drawn = None
        idle += clock.tick(30)
        if idle >= 300:                 # a look at the file three times a second
            idle = 0
            if viewer.changed():
                drawn = None
        state = (viewer.steps, viewer.steps.count, viewer.highlight, pointer,
                 viewer.error)
        if state == drawn:
            continue
        drawn = state
        screen.fill((0, 0, 0))
        screen.blit(pygame.transform.scale(picture_surface(pygame, viewer),
                                           (width, height)), (0, 0))
        y = height + 4
        for text in viewer.lines(pointer):
            screen.blit(font.render(text, True, (230, 230, 230)), (6, y))
            y += line
        if viewer.error:
            screen.blit(font.render(viewer.error, True, (255, 90, 90)), (6, y))
        y += line
        screen.blit(font.render(KEYS_HELP, True, (140, 140, 140)), (6, y))
        pygame.display.flip()


def picture_surface(pygame, viewer):
    """The picture as the device has it, the last order lit up if asked."""
    rows = viewer.steps.rgb()
    if viewer.highlight:
        laid = viewer.steps.laid()
        if laid:
            rows = [list(row) for row in rows]
            for x, y in laid:
                rows[y][x] = HIGHLIGHT
    wide, high = len(rows[0]), len(rows)
    data = bytes(value for row in rows for pixel in row for value in pixel)
    return pygame.image.frombuffer(data, (wide, high), "RGB")
