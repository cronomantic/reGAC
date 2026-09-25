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
"""regac draw as an editor: what is drawn goes into the source.

Decided by the user: the same window as the viewer; a new order goes after
the one the cursor is on; the points of an order can be dragged, and the
numbers of its line are written again.  What is looked at here is the file:
the window shows what the source says, so the source is what has to be
right.
"""

import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from regac.gfxedit import Picture, moved, points_of  # noqa: E402
from regac.viewer import SELECT, Viewer  # noqa: E402

EXAMPLE = os.path.join(ROOT, "ejemplo")


def a_copy(tmp_path):
    """The example, somewhere it can be written into."""
    for name in os.listdir(EXAMPLE):
        path = os.path.join(EXAMPLE, name)
        if os.path.isfile(path):
            shutil.copy(path, tmp_path)
    return str(tmp_path / "faro.gac")


def lines_of(path):
    with open(path, encoding="utf-8", newline="") as f:
        return f.read().splitlines()


def the_picture(path, number):
    """The lines of a picture's entry, the header first."""
    lines = lines_of(path)
    at = lines.index(f"#{number}")
    out = [lines[at]]
    for line in lines[at + 1:]:
        if line.strip().startswith("#") or line.strip().startswith("/"):
            break
        out.append(line)
    return [line for line in out if line.strip()]


# -- the lines of the source ---------------------------------------------------

SOURCE = "/GFX\n#1\n  INK 0            ; the ink\n  LINE 1 60 9 60\n\n#2\n  PLOT 5 60\n"


def written(tmp_path, text, name="p.gac"):
    path = tmp_path / name
    path.write_bytes(text.encode("utf-8"))
    return str(path)


def test_a_line_goes_in_with_the_indent_of_its_neighbours(tmp_path):
    picture = Picture(written(tmp_path, SOURCE), 1)
    assert picture.why_not is None
    assert picture.inserted(1, "PLOT 3 70").splitlines()[1:5] == [
        "#1", "  INK 0            ; the ink", "  PLOT 3 70", "  LINE 1 60 9 60"]
    assert picture.inserted(0, "PAPER 5").splitlines()[1:3] == ["#1", "  PAPER 5"]


def test_a_line_rewritten_keeps_its_comment(tmp_path):
    picture = Picture(written(tmp_path, SOURCE), 1)
    assert picture.rewritten(0, "INK 2").splitlines()[2] == (
        "  INK 2            ; the ink")


def test_a_line_taken_out(tmp_path):
    picture = Picture(written(tmp_path, SOURCE), 1)
    assert "LINE" not in picture.deleted(1)


def test_the_ends_of_line_are_the_files(tmp_path):
    path = written(tmp_path, SOURCE.replace("\n", "\r\n"))
    text = Picture(path, 1).inserted(2, "PLOT 1 50")
    assert "\r\n  PLOT 1 50\r\n" in text and "\n" not in text.replace("\r\n", "")


def test_where_it_does_not_write(tmp_path):
    assert Picture(written(tmp_path, "{}", "a.json"), 1).why_not
    kept = SOURCE.replace("  LINE 1 60 9 60\n",
                          ".if cpc\n  LINE 1 60 9 60\n.end\n")
    assert ".if" in Picture(written(tmp_path, kept), 1, "cpc").why_not
    written(tmp_path, "#1\n  PLOT 1 60\n", "otro.gac")
    path = written(tmp_path, '/GFX\n.include "otro.gac"\n')
    assert "otro.gac" in Picture(path, 1).why_not
    assert Picture(written(tmp_path, SOURCE), 9).why_not


def test_the_points_of_an_order():
    assert points_of(["LINE", 1, 2, 3, 4]) == [(1, 2), (3, 4)]
    assert points_of(["ELLIPSE", 10, 60, 20, 70]) == [(10, 60), (20, 70)]
    assert points_of(["INK", 3]) == []
    assert moved(["RECT", 1, 50, 9, 60], 1, (20, 70)) == ["RECT", 1, 50, 20, 70]


# -- drawing in the viewer -------------------------------------------------------

def test_a_line_drawn_goes_after_the_order_at_the_cursor(tmp_path):
    """With the cursor inside the horizon picture 1 calls, the line goes after
    the CALL, in picture 1: it is the picture being drawn."""
    path = a_copy(tmp_path)
    viewer = Viewer(path, 1, "spectrum")
    viewer.first()
    viewer.step(3)                          # CALL 10, and two of its orders
    assert viewer.steps.steps[viewer.steps.count - 1][0] == 1
    viewer.choose("LINE")
    viewer.press((10, 60))
    viewer.press((20, 70))
    assert the_picture(path, 1)[1:3] == ["  CALL 10", "  LINE 10 60 20 70"]
    depth, picture, number, order = viewer.steps.steps[viewer.steps.count - 1]
    assert (depth, picture, order) == (0, 1, ["LINE", 10, 60, 20, 70]), (
        "the cursor is not on what was drawn")
    assert viewer.error is None


def test_a_fill_at_the_end_is_the_last_order(tmp_path):
    path = a_copy(tmp_path)
    viewer = Viewer(path, 1, "spectrum")
    viewer.choose("FILL")
    viewer.press((30, 150))
    assert the_picture(path, 1)[-1] == "  FILL 30 150"
    assert viewer.steps.count == len(viewer.steps.steps)


def test_a_point_dragged_rewrites_its_line(tmp_path):
    path = a_copy(tmp_path)
    viewer = Viewer(path, 1, "spectrum")
    assert viewer.tool == SELECT
    viewer.press((71, 101))                 # near PLOT 72 100, the last
    assert viewer.dragging is not None
    viewer.release((80, 90))
    assert the_picture(path, 1)[-1] == "  PLOT 80 90"


def test_the_orders_of_a_picture_called_are_not_handles(tmp_path):
    viewer = Viewer(a_copy(tmp_path), 1, "spectrum")
    own = {step for step, _, _ in viewer.handles()}
    assert all(viewer.steps.steps[step][0] == 0 for step in own)
    # the horizon's line, which picture 10 draws, is not one of them
    assert viewer.handle_at((0, 96)) is None


def test_an_order_taken_out_and_taken_back(tmp_path):
    path = a_copy(tmp_path)
    with open(path, encoding="utf-8", newline="") as f:
        was = f.read()
    viewer = Viewer(path, 1, "spectrum")
    viewer.delete()
    assert "  PLOT 72 100" not in the_picture(path, 1)
    assert viewer.steps.steps[viewer.steps.count - 1][3] == ["PLOT", 56, 104]
    viewer.add("INK 2")
    viewer.take_back()
    viewer.take_back()
    with open(path, encoding="utf-8", newline="") as f:
        assert f.read() == was


def test_nothing_is_taken_back_over_somebody_elses_change(tmp_path):
    path = a_copy(tmp_path)
    viewer = Viewer(path, 1, "spectrum")
    viewer.add("INK 2")
    with open(path, "a", encoding="utf-8") as f:
        f.write("; somebody else\n")
    viewer.take_back()
    assert viewer.error and "INK 2" in "\n".join(the_picture(path, 1))


def test_an_order_of_a_picture_called_is_not_taken_out_here(tmp_path):
    path = a_copy(tmp_path)
    viewer = Viewer(path, 1, "spectrum")
    viewer.first()
    viewer.step(3)
    before = lines_of(path)
    viewer.delete()
    assert viewer.error and lines_of(path) == before


def test_snapping_to_the_cells():
    viewer = Viewer.__new__(Viewer)
    viewer.snap = True
    assert viewer.snapped((13, 101)) == (16, 103)
    assert viewer.snapped((255, 48)) == (255, 48)      # the edges hold
    viewer.snap = False
    assert viewer.snapped((13, 101)) == (13, 101)


def test_the_window_draws_with_the_mouse(tmp_path, monkeypatch):
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    import pygame

    from regac import viewer

    path = a_copy(tmp_path)
    scale = 3

    def at(x, y):
        return (x * scale + 1, (175 - y) * scale + 1)

    def click(x, y):
        return [pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=at(x, y)),
                pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=at(x, y))]

    key = lambda name: pygame.event.Event(pygame.KEYDOWN, key=name, mod=0)  # noqa: E731
    handed = iter([
        [key(pygame.K_r)], click(20, 60), click(40, 80),
        [key(pygame.K_RETURN)], [pygame.event.Event(pygame.TEXTINPUT, text="ink 3")],
        [key(pygame.K_RETURN)],
        [key(pygame.K_q)],
    ])
    monkeypatch.setattr(pygame.event, "get", lambda: next(handed))
    viewer.run(path, 1, "spectrum", scale=scale)
    assert the_picture(path, 1)[-2:] == ["  RECT 20 60 40 80", "  INK 3"]
