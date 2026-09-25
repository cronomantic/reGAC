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
"""The map of an adventure, drawn from its ways out.

`regac map aventura.gac mapa.svg` lays the rooms out on a grid by the compass
and writes the picture as SVG, which any browser shows.  Which way a way out
goes is read in the vocabulary: a verb one of whose words is NORTE, N, NORTH
and the like goes up the page, and so on round the eight points.  What is not
a point of the compass -- SUBE, ENTRA, SALTA -- is drawn as an arrow with its
word on it, from wherever the two rooms ended up.

The laying out starts where the player starts and walks out from there, each
room put one step from the one it was reached from, in the direction it was
reached by.  When that place is taken it goes further along the same line,
and failing that, anywhere near.  A room nothing leads to by a way out --
reached by a GOTO, or by nothing at all -- is laid out apart, to the right.

A way that goes both ways is one line; one that goes only one way has an
arrow at the end it goes to.
"""

import collections
import html

from .i18n import _
from .text import expand, plain, typed

# The points of the compass, as the words that name them, and which way each
# goes on the page: x to the right, y down.
COMPASS = {
    "N": (0, -1), "NORTE": (0, -1), "NORTH": (0, -1),
    "S": (0, 1), "SUR": (0, 1), "SOUTH": (0, 1),
    "E": (1, 0), "ESTE": (1, 0), "EAST": (1, 0), "DERECHA": (1, 0),
    "O": (-1, 0), "OESTE": (-1, 0), "W": (-1, 0), "WEST": (-1, 0),
    "IZQUIERDA": (-1, 0),
    "NE": (1, -1), "NORESTE": (1, -1), "NORTHEAST": (1, -1),
    "NOROESTE": (-1, -1), "NW": (-1, -1), "NORTHWEST": (-1, -1),
    "SE": (1, 1), "SURESTE": (1, 1), "SUDESTE": (1, 1), "SOUTHEAST": (1, 1),
    "SO": (-1, 1), "SUROESTE": (-1, 1), "SUDOESTE": (-1, 1), "SW": (-1, 1),
    "SOUTHWEST": (-1, 1),
}
# Words that are a point of the compass only beside the whole of it: NO is
# north west next to NOROESTE, and on its own is more likely to be a no.
ONLY_BESIDE = {"NO": "NOROESTE"}

CELL_X, CELL_Y = 170, 96        # a room and the room beside it, in pixels
BOX_W, BOX_H = 132, 56
MARGIN = 40
LINE_CHARS = 20                 # what fits on a line of a box


def directions(ddb):
    """Which way on the page each verb that is a point of the compass goes,
    by the verb's number."""
    words = collections.defaultdict(set)
    for word, number in (ddb.get("verbs") or {}).items():
        words[number].add(typed(word).upper())
    out = {}
    for number, said in words.items():
        for word in sorted(said):
            if word in COMPASS:
                out[number] = COMPASS[word]
                break
            if word in ONLY_BESIDE and ONLY_BESIDE[word] in said:
                out[number] = COMPASS[ONLY_BESIDE[word]]
                break
    return out


def verb_word(ddb, number):
    """The longest word a verb is known by, which is the one that reads."""
    said = [word for word, n in (ddb.get("verbs") or {}).items() if n == number]
    return max(said, key=len) if said else str(number)


def exits_of(ddb):
    """Every way out, as (from, verb, to), of rooms that are there."""
    rooms = {int(k) for k in ddb.get("locations") or {}}
    out = []
    for key, room in (ddb.get("locations") or {}).items():
        for way in room.get("exits", []):
            if int(way["dest"]) in rooms:
                out.append((int(key), way["dir"], int(way["dest"])))
    return out


def lay_out(ddb):
    """Where every room goes on the grid, as {room: (x, y)}."""
    rooms = sorted(int(k) for k in ddb.get("locations") or {})
    compass = directions(ddb)
    # every way, from either end, with the step it takes on the page: the
    # other end of a way north is south of where it leads
    ways = collections.defaultdict(list)
    for origin, verb, dest in exits_of(ddb):
        step = compass.get(verb)
        ways[origin].append((step, dest))
        ways[dest].append(((-step[0], -step[1]) if step else None, origin))
    place = {}
    taken = {}

    def put(room, at):
        place[room] = at
        taken[at] = room

    def free_near(at):
        for radius in range(1, 50):
            for dy in range(-radius, radius + 1):
                for dx in range(-radius, radius + 1):
                    spot = (at[0] + dx, at[1] + dy)
                    if max(abs(dx), abs(dy)) == radius and spot not in taken:
                        return spot
        raise RuntimeError(_("no room left on the map"))

    def walk(start, at):
        put(start, at)
        queue = collections.deque([start])
        while queue:
            room = queue.popleft()
            here = place[room]
            # the compass first, so that a room goes where its way says
            for step, dest in sorted(ways[room], key=lambda w: w[0] is None):
                if dest in place:
                    continue
                spot = None
                if step:
                    for k in range(1, 4):
                        want = (here[0] + step[0] * k, here[1] + step[1] * k)
                        if want not in taken:
                            spot = want
                            break
                if spot is None:
                    spot = free_near(here)
                put(dest, spot)
                queue.append(dest)

    start = int(ddb.get("init_loc", rooms[0] if rooms else 0))
    if start in rooms:
        walk(start, (0, 0))
    # what nothing reaches, apart and to the right, a group at a time
    right = max((x for x, _ in place.values()), default=-2) + 2
    for room in rooms:
        if room not in place:
            walk(room, (right, 0))
            right = max(x for x, _ in place.values()) + 2
    return place


def room_lines(ddb, room):
    """The number of a room and the start of what it says, to go in its box."""
    text = plain(expand((ddb.get("locations") or {})[str(room)].get("desc", "")))
    words = text.split()
    lines, line = [], ""
    for word in words:
        if len(line) + len(word) + (1 if line else 0) > LINE_CHARS:
            lines.append(line)
            line = word[:LINE_CHARS]
            if len(lines) == 2:
                break
        else:
            line = f"{line} {word}" if line else word
    else:
        if line:
            lines.append(line)
    if len(lines) == 2 and " ".join(lines) != " ".join(words):
        lines[1] = lines[1][:LINE_CHARS - 1] + "…"
    return lines[:2]


def svg(ddb, title="map"):
    """The map, as the text of an SVG file."""
    place = lay_out(ddb)
    compass = directions(ddb)
    if not place:
        return '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="60"/>'
    low_x = min(x for x, _ in place.values())
    low_y = min(y for _, y in place.values())

    def centre(room):
        x, y = place[room]
        return (MARGIN + (x - low_x) * CELL_X + BOX_W / 2,
                MARGIN + (y - low_y) * CELL_Y + BOX_H / 2)

    width = MARGIN * 2 + (max(x for x, _ in place.values()) - low_x) * CELL_X + BOX_W
    height = MARGIN * 2 + (max(y for _, y in place.values()) - low_y) * CELL_Y + BOX_H
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" '
           f'height="{height:.0f}" font-family="sans-serif" font-size="11">',
           f"<title>{html.escape(title)}</title>",
           '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" '
           'markerWidth="8" markerHeight="8" orient="auto-start-reverse">'
           '<path d="M0,0 L10,5 L0,10 z" fill="#444"/></marker></defs>',
           f'<rect width="{width:.0f}" height="{height:.0f}" fill="white"/>']

    ways = exits_of(ddb)
    both = {(o, d) for o, _, d in ways}
    drawn = set()
    for origin, verb, dest in ways:
        if origin == dest:
            continue
        (x0, y0), (x1, y1) = centre(origin), centre(dest)
        step = compass.get(verb)
        straight = step is not None and (
            place[dest][0] - place[origin][0], place[dest][1] - place[origin][1]
        ) in {(step[0] * k, step[1] * k) for k in (1, 2, 3)}
        back = (dest, origin) in both
        if straight:
            pair = (min(origin, dest), max(origin, dest))
            if back and pair in drawn:
                continue
            drawn.add(pair)
            tip = "" if back else ' marker-end="url(#arrow)"'
            x1e, y1e = edge(x0, y0, x1, y1)
            x0e, y0e = edge(x1, y1, x0, y0)
            out.append(f'<line x1="{x0e:.1f}" y1="{y0e:.1f}" x2="{x1e:.1f}" '
                       f'y2="{y1e:.1f}" stroke="#444" stroke-width="1.5"{tip}/>')
        else:
            # anything else bends, with its word on it
            mx, my = (x0 + x1) / 2, (y0 + y1) / 2
            bend_x, bend_y = mx + (y1 - y0) * 0.2, my - (x1 - x0) * 0.2
            x0e, y0e = edge(bend_x, bend_y, x0, y0)
            x1e, y1e = edge(bend_x, bend_y, x1, y1)
            out.append(f'<path d="M{x0e:.1f},{y0e:.1f} Q{bend_x:.1f},'
                       f'{bend_y:.1f} {x1e:.1f},{y1e:.1f}" fill="none" '
                       f'stroke="#2a6fb0" stroke-width="1.2" '
                       f'stroke-dasharray="4 3" marker-end="url(#arrow)"/>')
            out.append(f'<text x="{bend_x:.1f}" y="{bend_y:.1f}" '
                       f'text-anchor="middle" fill="#2a6fb0">'
                       f'{html.escape(verb_word(ddb, verb))}</text>')

    start = int(ddb.get("init_loc", 0))
    for room in sorted(place):
        cx, cy = centre(room)
        x, y = cx - BOX_W / 2, cy - BOX_H / 2
        thick = 3 if room == start else 1.2
        out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{BOX_W}" '
                   f'height="{BOX_H}" rx="6" fill="#fdf8e8" stroke="#333" '
                   f'stroke-width="{thick}"/>')
        out.append(f'<text x="{x + 6:.1f}" y="{y + 15:.1f}" '
                   f'font-weight="bold">#{room}</text>')
        for n, line in enumerate(room_lines(ddb, room)):
            out.append(f'<text x="{x + 6:.1f}" y="{y + 30 + 13 * n:.1f}">'
                       f'{html.escape(line)}</text>')
    out.append("</svg>")
    return "\n".join(out) + "\n"


def edge(x_from, y_from, x_to, y_to):
    """Where a line from one point towards the centre of a box meets the
    box, so that lines stop at the boxes and not under them."""
    dx, dy = x_to - x_from, y_to - y_from
    if dx == 0 and dy == 0:
        return x_to, y_to
    scale = min((BOX_W / 2) / abs(dx) if dx else float("inf"),
                (BOX_H / 2) / abs(dy) if dy else float("inf"))
    return x_to - dx * scale, y_to - dy * scale
