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
"""regac map: the rooms laid out by the compass, as SVG."""

import os
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from regac.mapper import directions, lay_out, svg  # noqa: E402

SVG = "{http://www.w3.org/2000/svg}"
VERBS = {"N": 1, "NORTE": 1, "S": 2, "SUR": 2, "E": 3, "ESTE": 3,
         "O": 4, "OESTE": 4, "SUBE": 5, "NO": 6}


def rooms(*ways, start=1, count=None):
    """An adventure of rooms and nothing else: `ways` are (from, verb, to)."""
    count = count or max(max(a, b) for a, _, b in ways)
    locations = {str(n): {"graphic_id": 0, "exits": [], "desc": f"SALA {n}"}
                 for n in range(1, count + 1)}
    for origin, verb, dest in ways:
        locations[str(origin)]["exits"].append({"dir": verb, "dest": dest})
    return {"verbs": dict(VERBS), "locations": locations, "init_loc": start}


def test_the_compass_is_read_in_the_vocabulary():
    found = directions({"verbs": VERBS})
    assert found == {1: (0, -1), 2: (0, 1), 3: (1, 0), 4: (-1, 0)}, found
    # NO is north west only beside NOROESTE; on its own it is a no
    found = directions({"verbs": {"NO": 6, "NOROESTE": 6}})
    assert found == {6: (-1, -1)}


def test_a_cross_is_a_cross():
    place = lay_out(rooms((1, 1, 2), (1, 2, 3), (1, 3, 4), (1, 4, 5)))
    assert place == {1: (0, 0), 2: (0, -1), 3: (0, 1), 4: (1, 0), 5: (-1, 0)}


def test_a_room_reached_only_the_other_way_is_where_its_way_says():
    """Room 2 has a way south into the start and none back: it is north."""
    assert lay_out(rooms((2, 2, 1)))[2] == (0, -1)


def test_a_place_taken_sends_the_room_further_along_the_line():
    place = lay_out(rooms((1, 1, 2), (1, 3, 3), (3, 1, 4), (4, 4, 5)))
    # 5 is west of 4, which is where 2 already is: it goes one further west
    assert place[2] == (0, -1) and place[4] == (1, -1)
    assert place[5] == (-1, -1)


def test_what_nothing_leads_to_is_laid_out_apart():
    place = lay_out(rooms((1, 1, 2), count=3))
    assert place[3][0] > max(place[1][0], place[2][0])


def lines_of(picture):
    tree = ET.fromstring(picture)
    return (tree.findall(f"{SVG}line"), tree.findall(f"{SVG}path"),
            [t.text for t in tree.findall(f"{SVG}text")])


def test_a_way_both_ways_is_one_line_and_one_way_has_an_arrow():
    both, _, _ = lines_of(svg(rooms((1, 1, 2), (2, 2, 1))))
    assert len(both) == 1 and "marker-end" not in both[0].attrib
    one, _, _ = lines_of(svg(rooms((1, 1, 2))))
    assert len(one) == 1 and "marker-end" in one[0].attrib


def test_what_is_not_the_compass_bends_and_says_its_word():
    _, paths, texts = lines_of(svg(rooms((1, 5, 2))))
    assert len(paths) == 1, "SUBE is not a way on the page"
    assert "SUBE" in texts


def test_every_room_is_in_a_box_with_its_number():
    _, _, texts = lines_of(svg(rooms((1, 1, 2), count=3)))
    for n in (1, 2, 3):
        assert f"#{n}" in texts and f"SALA {n}" in texts


def test_the_example_comes_out(tmp_path):
    out = str(tmp_path / "faro.svg")
    subprocess.run([sys.executable, "-m", "regac", "map",
                    os.path.join(ROOT, "ejemplo", "faro.gac"), out],
                   cwd=ROOT, check=True, capture_output=True)
    _, _, texts = lines_of(open(out, encoding="utf-8").read())
    assert sum(1 for t in texts if t and t.startswith("#")) == 5
