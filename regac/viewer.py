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

# What an image to trace can be, and how much of it is seen at first.
TRACE_TYPES = (".png", ".jpg", ".jpeg", ".bmp", ".gif")
TRACE_ALPHA = 0.5


def fitted(wide, high, area_wide, area_high):
    """Where an image goes in an area, as (x, y, wide, high): as big as it
    fits without being put out of shape, and centred."""
    scale = min(area_wide / wide, area_high / high)
    out_wide, out_high = round(wide * scale), round(high * scale)
    return ((area_wide - out_wide) // 2, (area_high - out_high) // 2,
            out_wide, out_high)

# What a click does: moves a point, or draws one of these.  The keys that
# choose them are their initials, and B for the fill that wipes.
SELECT = "select"
ONE_POINT = ("PLOT", "FILL", "BGFILL", "SHADE")
TWO_POINTS = ("LINE", "RECT", "ELLIPSE")


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

    def __init__(self, path, picture=None, machine=None, trace=None):
        self.path = path
        self.trace = trace              # an image, or a folder of them
        self.trace_on = True
        self.trace_alpha = TRACE_ALPHA
        self.error = None
        self.ddb = None
        self.machine = machine
        self.picture = picture
        self.highlight = True
        self.stamp = None
        self.steps = None
        self.tool = SELECT              # what a click does
        self.pending = None             # the first point of a two point order
        self.dragging = None            # (step, which point) being dragged
        self.snap = False               # points to the corners of cells
        self.taken_back = []            # (before, after) of every edit
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

    # -- drawing ------------------------------------------------------------
    #
    # What is drawn is written into the source at once, as a line of the
    # picture's entry, and the source read again: the window shows what the
    # source says and nothing else.  A new order goes after the one the
    # cursor is on -- a fill depends on what is drawn before it -- and belongs
    # to the picture being looked at, even when the cursor is inside one it
    # calls: that goes after the CALL.  Only the picture's own orders can be
    # dragged or taken out; one of a picture it calls is changed in that one.

    def editable(self):
        from .gfxedit import Picture

        return Picture(self.path, self.picture,
                       SOURCE_LABEL.get(self.machine, self.machine))

    def at_cursor(self):
        """How many of the picture's own orders are drawn at the cursor,
        which is where a new one goes."""
        drawn = 0
        for depth, _, number, _ in self.steps.steps[:self.steps.count]:
            if depth == 0:
                drawn = number
        return drawn

    def cursor_to(self, number):
        """The cursor just after the picture's own order `number`."""
        for at, (depth, _, n, _) in enumerate(self.steps.steps):
            if depth == 0 and n == number:
                self.steps.go(at + 1)
                return
        self.steps.go(0)

    def write(self, make):
        """Write what `make` makes of the picture's lines into the source,
        keep it to be taken back, and read the source again."""
        picture = self.editable()
        if picture.why_not:
            self.error = picture.why_not
            return False
        text = make(picture)
        self.taken_back.append((picture.text, text))
        picture.write(text)
        self.reload()
        return self.error is None

    def add(self, text):
        """An order, as it is written, after the one at the cursor."""
        at = self.at_cursor()
        if self.write(lambda p: p.inserted(at, text)):
            self.cursor_to(at + 1)

    def delete(self):
        """Take out the order at the cursor, if it is the picture's own."""
        if not self.steps.count:
            return
        depth, _, number, _ = self.steps.steps[self.steps.count - 1]
        if depth:
            self.error = ("that order is the picture's it calls: take it out "
                          "of that one")
            return
        if self.write(lambda p: p.deleted(number - 1)):
            self.cursor_to(number - 1)

    def move(self, step, which, point):
        """Put point `which` of the order of step `step` at `point`."""
        from .gfxedit import moved, written

        depth, _, number, order = self.steps.steps[step]
        count = self.steps.count
        if self.write(lambda p: p.rewritten(
                number - 1, written(moved(order, which, point)))):
            self.steps.go(count)

    def take_back(self):
        """Undo the last edit, if the source is still what it left."""
        if not self.taken_back:
            return
        before, after = self.taken_back.pop()
        with open(self.path, encoding="utf-8", newline="") as f:
            now = f.read()
        if now != after:
            self.error = "the source was changed since: nothing taken back"
            self.taken_back.clear()
            return
        with open(self.path, "w", encoding="utf-8", newline="") as f:
            f.write(before)
        count = self.steps.count
        self.reload()
        self.steps.go(count)

    def handles(self):
        """The points that can be dragged: (step, which, point), of the
        picture's own orders drawn so far."""
        from .gfxedit import points_of

        out = []
        for at, (depth, _, _, order) in enumerate(
                self.steps.steps[:self.steps.count]):
            if depth == 0:
                out += [(at, which, point)
                        for which, point in enumerate(points_of(order))]
        return out

    def handle_at(self, point, reach=4):
        """The handle nearest `point`, the latest order first, within
        `reach` of it in the coordinates of the orders."""
        best = None
        for handle in reversed(self.handles()):
            far = max(abs(handle[2][0] - point[0]), abs(handle[2][1] - point[1]))
            if far <= reach and (best is None or far < best[0]):
                best = (far, handle)
        return best[1] if best else None

    def snapped(self, point):
        """A point, to the corner of its cell of eight if snapping."""
        x, y = point
        if self.snap:
            x = min(SOURCE_WIDTH - 1, round(x / 8) * 8)
            y = MAX_Y - min(SOURCE_ROWS - 1, round((MAX_Y - y) / 8) * 8)
        return x, y

    def choose(self, tool):
        self.tool = tool
        self.pending = None
        self.dragging = None

    def press(self, point):
        """The button went down on `point`."""
        x, y = self.snapped(point)
        if self.tool == SELECT:
            self.dragging = self.handle_at(point)
        elif self.tool in ONE_POINT:
            self.add(f"{self.tool} {x} {y}")
        elif self.pending is None:
            self.pending = (x, y)
        else:
            x0, y0 = self.pending
            self.pending = None
            self.add(f"{self.tool} {x0} {y0} {x} {y}")

    def release(self, point):
        """The button came up on `point`: the end of a drag."""
        if self.dragging is None:
            return
        step, which, was = self.dragging
        self.dragging = None
        point = self.snapped(point)
        if point != was:
            self.move(step, which, point)

    def cancel(self):
        self.pending = None
        self.dragging = None

    # -- tracing ------------------------------------------------------------
    #
    # An image laid over the picture, half seen through, to draw on top of:
    # a sketch, a photo, the picture of the original.  One image for every
    # picture, or a folder with one to each, named by its number.

    def trace_file(self):
        """The image laid over this picture, or None."""
        if not self.trace:
            return None
        if os.path.isdir(self.trace):
            for name in sorted(os.listdir(self.trace)):
                stem, ext = os.path.splitext(name)
                if stem == str(self.picture) and ext.lower() in TRACE_TYPES:
                    return os.path.join(self.trace, name)
            return None
        return self.trace

    def stronger_trace(self, by):
        self.trace_alpha = min(0.9, max(0.1, round(self.trace_alpha + by, 1)))

    def trace_said(self):
        if not self.trace:
            return ""
        if not self.trace_on:
            return "trace: hidden (t shows it)"
        found = self.trace_file()
        if found is None:
            return f"trace: nothing for #{self.picture} in {self.trace}"
        return (f"trace: {os.path.basename(found)} at "
                f"{round(self.trace_alpha * 100)}%  (t hides it, +/- more "
                f"or less of it)")

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


KEYS_HELP = (
    "left/right an order (shift ten, ctrl a hundred)  home/end  "
    "page up/down a picture  m machine  h light  q quit",
    "draw: l line  r rect  e ellipse  p plot  f fill  b bgfill  s shade  "
    "v move points",
    "g snap to cells  del take out  enter write an order  ctrl-z undo  "
    "right button or esc: let go",
)
TOOL_KEYS = {"l": "LINE", "r": "RECT", "e": "ELLIPSE", "p": "PLOT",
             "f": "FILL", "b": "BGFILL", "s": "SHADE", "v": SELECT}
WHAT_NEXT = {SELECT: "drag a point to move it",
             "LINE": "click the two ends", "RECT": "click two corners",
             "ELLIPSE": "click the centre, then how far it reaches",
             "PLOT": "click the point", "FILL": "click where it starts",
             "BGFILL": "click where it starts", "SHADE": "click where it starts"}
# and once the first point is down
SECOND = {"LINE": "click the other end", "RECT": "click the other corner",
          "ELLIPSE": "click how far it reaches"}
RUBBER = (255, 220, 0)          # what is being drawn, before it is
HANDLE = (0, 200, 255)


def run(path, picture=None, machine=None, scale=3, trace=None):
    """The window, until it is closed."""
    import pygame

    viewer = Viewer(path, picture, machine, trace)
    pygame.init()
    pygame.key.set_repeat(300, 40)
    width, height = SOURCE_WIDTH * scale, SOURCE_ROWS * scale
    font = pygame.font.Font(None, 22)
    line = font.get_linesize()
    panel = line * 11 + 8
    screen = pygame.display.set_mode((width, height + panel))
    pygame.display.set_caption(f"regac draw {os.path.basename(path)}")
    clock = pygame.time.Clock()
    pointer = None
    images = {}                         # an image to trace, by its file
    typing = None                       # an order being written, or None
    drawn = None                        # what the window was drawn from
    idle = 0

    def traced(found):
        """The image, sized to lie over the picture, or None if it will
        not read."""
        if found not in images:
            try:
                whole = pygame.image.load(found)
            except (pygame.error, OSError) as e:
                images[found] = e
            else:
                x, y, wide, high = fitted(*whole.get_size(), width, height)
                images[found] = (pygame.transform.smoothscale(
                    whole.convert(), (wide, high)), (x, y))
        return images[found]

    def on_screen(point):
        x, y = point
        return (int((x + 0.5) * width / SOURCE_WIDTH),
                int((MAX_Y - y + 0.5) * height / SOURCE_ROWS))

    while True:
        for event in pygame.event.get():
            drawn = None
            if event.type == pygame.QUIT:
                pygame.quit()
                return
            if event.type == pygame.MOUSEMOTION:
                pointer = gac_point(*event.pos, width, height)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                at = gac_point(*event.pos, width, height)
                if event.button == 3:
                    viewer.cancel()
                elif event.button == 1 and at:
                    viewer.press(at)
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                at = gac_point(*event.pos, width, height)
                if at:
                    viewer.release(at)
                else:
                    viewer.cancel()
            elif event.type == pygame.TEXTINPUT and typing is not None:
                typing += event.text.upper()
            elif event.type == pygame.KEYDOWN:
                key = event.key
                if typing is not None:
                    if key == pygame.K_RETURN:
                        if typing.strip():
                            viewer.add(typing)
                        typing = None
                    elif key == pygame.K_ESCAPE:
                        typing = None
                    elif key == pygame.K_BACKSPACE:
                        typing = typing[:-1]
                    continue
                shift = event.mod & pygame.KMOD_SHIFT
                ctrl = event.mod & pygame.KMOD_CTRL
                stride = 100 if ctrl else 10 if shift else 1
                name = pygame.key.name(key)
                if key == pygame.K_q:
                    pygame.quit()
                    return
                elif key == pygame.K_ESCAPE:
                    viewer.cancel()
                    viewer.choose(SELECT)
                elif ctrl and key == pygame.K_z:
                    viewer.take_back()
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
                elif key == pygame.K_g:
                    viewer.snap = not viewer.snap
                elif key == pygame.K_t:
                    viewer.trace_on = not viewer.trace_on
                elif key in (pygame.K_PLUS, pygame.K_KP_PLUS, pygame.K_EQUALS):
                    viewer.stronger_trace(0.1)
                elif key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    viewer.stronger_trace(-0.1)
                elif key == pygame.K_DELETE:
                    viewer.delete()
                elif key == pygame.K_RETURN:
                    typing = ""
                elif name in TOOL_KEYS:
                    viewer.choose(TOOL_KEYS[name])
        idle += clock.tick(30)
        if idle >= 300:                 # a look at the file three times a second
            idle = 0
            if viewer.changed():
                drawn = None
        state = (viewer.steps, viewer.steps.count, viewer.highlight, pointer,
                 viewer.error, viewer.tool, viewer.pending, viewer.dragging,
                 viewer.snap, typing, viewer.picture, viewer.trace_on,
                 viewer.trace_alpha)
        if state == drawn:
            continue
        drawn = state
        screen.fill((0, 0, 0))
        screen.blit(pygame.transform.scale(picture_surface(pygame, viewer),
                                           (width, height)), (0, 0))
        # the image being traced, over the picture and half seen through
        found = viewer.trace_file() if viewer.trace_on else None
        if found:
            image = traced(found)
            if isinstance(image, Exception):
                viewer.error = f"{os.path.basename(found)} will not read: {image}"
            else:
                image[0].set_alpha(round(viewer.trace_alpha * 255))
                screen.blit(image[0], image[1])
        # the points that can be dragged, and what is being drawn
        if viewer.tool == SELECT:
            for _, _, point in viewer.handles():
                x, y = on_screen(point)
                pygame.draw.rect(screen, HANDLE, (x - 3, y - 3, 7, 7), 1)
        if viewer.dragging and pointer:
            pygame.draw.circle(screen, RUBBER,
                               on_screen(viewer.snapped(pointer)), 5, 1)
        if viewer.pending and pointer:
            a, b = on_screen(viewer.pending), on_screen(viewer.snapped(pointer))
            if viewer.tool == "LINE":
                pygame.draw.line(screen, RUBBER, a, b)
            elif viewer.tool == "RECT":
                pygame.draw.rect(screen, RUBBER, (min(a[0], b[0]), min(a[1], b[1]),
                                                  abs(b[0] - a[0]) + 1,
                                                  abs(b[1] - a[1]) + 1), 1)
            elif viewer.tool == "ELLIPSE":
                rx, ry = abs(b[0] - a[0]), abs(b[1] - a[1])
                if rx and ry:
                    pygame.draw.ellipse(screen, RUBBER,
                                        (a[0] - rx, a[1] - ry, 2 * rx, 2 * ry), 1)
        y = height + 4
        for text in viewer.lines(pointer):
            screen.blit(font.render(text, True, (230, 230, 230)), (6, y))
            y += line
        tool = viewer.tool if viewer.tool == SELECT else viewer.tool.lower()
        what = SECOND[viewer.tool] if viewer.pending else WHAT_NEXT[viewer.tool]
        doing = (f"write an order: {typing}_" if typing is not None else
                 f"{tool}: {what}"
                 + ("  (snapping to cells)" if viewer.snap else ""))
        screen.blit(font.render(doing, True, RUBBER), (6, y))
        y += line
        screen.blit(font.render(viewer.trace_said(), True, HANDLE), (6, y))
        y += line
        if viewer.error:
            screen.blit(font.render(viewer.error, True, (255, 90, 90)), (6, y))
        y += line
        for text in KEYS_HELP:
            screen.blit(font.render(text, True, (140, 140, 140)), (6, y))
            y += line
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
