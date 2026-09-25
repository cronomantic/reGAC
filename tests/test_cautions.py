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
"""The cautions regac draw gives while a picture is drawn: a fill that got
out, a fill that does nothing, the bytes; and the time, measured on the
machine, which the user decided is measured and not guessed."""

import os
import sys

try:
    import pytest
except ImportError:
    pytest = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import emulator  # noqa: E402
from regac.cautions import cautions, picture_bytes, rays  # noqa: E402
from regac.measure import TOO_SLOW, measure, why_not  # noqa: E402
from regac.viewer import Viewer, read_adventure  # noqa: E402

EXAMPLE = os.path.join(ROOT, "ejemplo", "faro.gac")


def a_box(gap=False, seed=(50, 100)):
    """A box of four lines, its left wall with a hole of one pixel at y 100
    if asked, and a fill inside it."""
    left = ([["LINE", 20, 60, 20, 99], ["LINE", 20, 101, 20, 140]] if gap
            else [["LINE", 20, 60, 20, 140]])
    return {"gfx": {"1": left + [["LINE", 20, 140, 90, 140],
                                 ["LINE", 90, 140, 90, 60],
                                 ["LINE", 90, 60, 20, 60],
                                 ["FILL", *seed]]}}


def said(ddb):
    return [what for step, what in cautions(ddb, 1, "spectrum")
            if step is not None]


def test_a_fill_through_a_gap_is_said():
    notes = said(a_box(gap=True))
    assert len(notes) == 1 and "got out at y 100" in notes[0], notes
    assert "left to x 0" in notes[0], notes
    assert said(a_box()) == [], "a whole box said something"


def test_a_fill_that_fills_nothing_is_said():
    notes = said(a_box(seed=(20, 100)))         # on the wall
    assert len(notes) == 1 and "fills nothing" in notes[0], notes


def test_a_ray_is_a_row_that_sticks_out_of_both_its_neighbours():
    box = {y: (21, 89) for y in range(61, 140)}
    assert rays(box) == []
    box[100] = (0, 89)
    assert rays(box) == [(100, 0, 89, "left")]
    # a wall that leans a little each row is not a ray
    leaning = {y: (21 + (y - 61) // 2, 89) for y in range(61, 140)}
    assert rays(leaning) == []


def test_the_example_says_nothing_but_its_bytes():
    ddb = read_adventure(EXAMPLE, "spectrum48")
    for picture in ddb["gfx"]:
        notes = cautions(ddb, picture, "spectrum")
        assert [step for step, _ in notes] == [None], (picture, notes)


def test_the_bytes_of_a_picture():
    # PAPER 5, INK 0, LINE of four, PAPER 4, BGFILL of two: 2 + 2+2+5+2+3
    assert picture_bytes([["PAPER", 5], ["INK", 0], ["LINE", 0, 96, 255, 96],
                          ["PAPER", 4], ["BGFILL", 128, 60]]) == 16
    assert picture_bytes([["CALL", 10]]) == 5    # the picture called is two


def test_the_cursor_goes_to_the_next_caution(tmp_path):
    source = tmp_path / "caja.gac"
    source.write_text("/LOC #1\nUNA CAJA\n/GFX\n#1\n" + "".join(
        "  " + " ".join(str(p) for p in order) + "\n"
        for order in a_box(gap=True)["gfx"]["1"]), encoding="utf-8")
    viewer = Viewer(str(source), 1, "spectrum")
    viewer.first()
    viewer.next_caution()
    assert viewer.steps.steps[viewer.steps.count - 1][3][0] == "FILL"


def test_where_it_cannot_be_timed():
    assert "pcw" in why_not("pcw")
    assert "next" in why_not("next")


needs_tools = (pytest.mark.skipif(not emulator.available(),
                                  reason="sjasmplus and ZEsarUX must be in tools/")
               if pytest is not None else (lambda f: f))


@needs_tools
def test_it_is_timed_on_the_machine():
    """The example's first picture on a Spectrum: seconds of the real
    machine, and well inside the budget.  And the viewer's key, which does
    the same and says it."""
    ddb = read_adventure(EXAMPLE, "spectrum48")
    seconds = measure(ddb, 1, "spectrum")
    assert seconds is not None and 0 < seconds < TOO_SLOW, seconds
    viewer = Viewer(EXAMPLE, 1, "spectrum")
    viewer.start_measuring(threaded=False)
    text, bad = viewer.time_said()
    assert "within the budget" in text and bad == 0, text
