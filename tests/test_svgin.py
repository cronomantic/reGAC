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
"""An SVG brought into a picture with regac draw --import.

Decided by the user: the outlines only, the curves cut into straight lines,
the colours not looked at, and the drawing laid over the picture as --trace
lays an image.  A drawing 256 by 128 lies on the picture pixel for pixel,
which is what most of these use, so that the numbers can be read off.
"""

import math
import os
import shutil
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from regac.svgin import imported  # noqa: E402
from regac.viewer import Viewer  # noqa: E402

EXAMPLE = os.path.join(ROOT, "ejemplo")


def svg(tmp_path, body, box="0 0 256 128", name="d.svg"):
    path = tmp_path / name
    head = f' viewBox="{box}"' if box else ""
    path.write_text(f'<svg xmlns="http://www.w3.org/2000/svg"'
                    f' xmlns:xlink="http://www.w3.org/1999/xlink"{head}>'
                    f"{body}</svg>", encoding="utf-8")
    return str(path)


def orders(tmp_path, body, **kw):
    return imported(svg(tmp_path, body, **kw))[0]


# -- where things go -------------------------------------------------------------

def test_a_drawing_the_size_of_the_picture_lies_on_it_pixel_for_pixel(tmp_path):
    """y goes down in an SVG and up in the orders, from 175 at the top."""
    assert orders(tmp_path, '<line x1="10" y1="0" x2="100" y2="127"/>') == [
        ["LINE", 10, 175, 100, 48]]


def test_it_fits_without_being_put_out_of_shape_and_centred(tmp_path):
    """A square drawing is as tall as the picture and stands in its middle,
    as an image does under --trace."""
    assert orders(tmp_path, '<rect width="100" height="100"/>',
                  box="0 0 100 100") == [["RECT", 64, 175, 191, 48]]


def test_with_no_viewbox_its_width_and_height_are_the_area(tmp_path):
    path = tmp_path / "d.svg"
    path.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="512" '
                    'height="256"><line x1="0" y1="2" x2="511" y2="2"/></svg>',
                    encoding="utf-8")
    assert imported(str(path))[0] == [["LINE", 0, 174, 255, 174]]


def test_with_neither_it_goes_by_what_is_drawn(tmp_path):
    """Its outermost points, laid over the picture as big as they fit."""
    found = orders(tmp_path, '<rect x="1000" y="1000" width="20" height="10"/>',
                   box=None)
    assert found == [["RECT", 0, 175, 255, 48]]


# -- the shapes -------------------------------------------------------------------

def test_a_rectangle_not_turned_is_a_rect_and_a_turned_one_four_lines(tmp_path):
    assert orders(tmp_path, '<rect x="10" y="20" width="30" height="40"/>') == [
        ["RECT", 10, 155, 40, 115]]
    turned = orders(tmp_path, '<rect x="100" y="40" width="30" height="30" '
                              'transform="rotate(45 115 55)"/>')
    assert [o[0] for o in turned] == ["LINE"] * 4


def test_a_circle_is_an_ellipse_and_a_turned_ellipse_is_lines(tmp_path):
    """The second point of an ELLIPSE is as far from the centre as the
    curve reaches."""
    assert orders(tmp_path, '<circle cx="128" cy="64" r="20"/>') == [
        ["ELLIPSE", 128, 111, 148, 131]]
    turned = orders(tmp_path, '<ellipse cx="128" cy="64" rx="30" ry="10" '
                              'transform="rotate(30 128 64)"/>')
    assert len(turned) > 8 and {o[0] for o in turned} == {"LINE"}


def test_curves_are_cut_close_to_the_curve(tmp_path):
    """Every end of every straight piece is within a pixel of the curve
    they stand for -- half a pixel of tolerance and half of rounding -- and
    the pieces join up."""
    found = orders(tmp_path, '<path d="M10 120 C 40 20, 200 20, 240 120"/>')
    assert len(found) > 8
    for a, b in zip(found, found[1:]):
        assert a[3:5] == b[1:3], "the pieces do not join"

    def bezier(t):
        p = [(10, 120), (40, 20), (200, 20), (240, 120)]
        u = 1 - t
        return tuple(u ** 3 * p[0][i] + 3 * u * u * t * p[1][i]
                     + 3 * u * t * t * p[2][i] + t ** 3 * p[3][i]
                     for i in range(2))

    curve = [bezier(i / 2000) for i in range(2001)]
    for order in found:
        for x, y in (order[1:3], order[3:5]):
            row = 175 - y
            nearest = min(math.hypot(x + 0.5 - cx, row + 0.5 - cy)
                          for cx, cy in curve)
            assert nearest <= 1.25, (order, nearest)


def test_an_arc_goes_the_way_its_flags_say(tmp_path):
    """From the left end to the right one, half an ellipse each way: sweep
    nought goes round underneath, sweep one over the top."""
    under = orders(tmp_path, '<path d="M100 60 A20 20 0 0 0 140 60"/>')
    over = orders(tmp_path, '<path d="M100 60 A20 20 0 0 1 140 60"/>')
    lowest = min(y for o in under for y in (o[2], o[4]))
    highest = max(y for o in over for y in (o[2], o[4]))
    assert lowest <= 175 - 79 and highest >= 175 - 41


def test_what_reaches_past_the_picture_is_cut_at_its_edge(tmp_path):
    found, said = imported(svg(tmp_path, '<line x1="128" y1="64" x2="512" '
                                         'y2="64"/>'))
    assert found == [["LINE", 128, 111, 255, 111]]
    assert any("1" in text and "edge" in text for text in said), said


def test_a_line_drawn_twice_is_written_once(tmp_path):
    """Two shapes that share a side, which a drawing program does a lot."""
    found = orders(tmp_path, '<polygon points="10,10 50,10 50,50"/>'
                             '<line x1="50" y1="10" x2="10" y2="10"/>')
    assert len(found) == 3


def test_a_shape_inside_one_pixel_is_a_plot(tmp_path):
    assert orders(tmp_path, '<line x1="5.1" y1="5.1" x2="5.4" y2="5.4"/>') == [
        ["PLOT", 5, 170]]


# -- how a path is written --------------------------------------------------------

def test_a_path_written_tight_reads_as_one_written_loose(tmp_path):
    """Numbers run together where a sign or a second point parts them, arc
    flags with nothing after them, and more points after a moveto are
    lines -- relative after a relative one."""
    tight = orders(tmp_path, '<path d="m10-20 10 0l5.5.5h4v4z" '
                             'transform="translate(0 40)"/>')
    loose = orders(tmp_path, '<path d="M 10 20 L 20 20 L 25.5 20.5 '
                             'L 29.5 20.5 L 29.5 24.5 Z"/>')
    assert tight == loose
    flags = orders(tmp_path, '<path d="M100 60a20 20 0 0110 0"/>')
    spaced = orders(tmp_path, '<path d="M100 60 a 20 20 0 0 1 10 0"/>')
    assert flags == spaced and flags


def test_groups_and_uses_carry_their_transforms(tmp_path):
    """A use is the shape it names, moved by its x and y and by the groups
    round it; a symbol is drawn only where a use puts it."""
    found = orders(tmp_path,
                   '<defs><rect id="r" width="4" height="4"/></defs>'
                   '<symbol id="s"><line x1="0" y1="0" x2="8" y2="0"/></symbol>'
                   '<g transform="translate(100 0)">'
                   '<use href="#r" x="2" y="10"/>'
                   '<use xlink:href="#s" y="20"/></g>')
    assert found == [["RECT", 102, 165, 106, 161], ["LINE", 100, 155, 108, 155]]


# -- what is left out ---------------------------------------------------------------

def test_what_is_not_lines_is_left_out_and_said(tmp_path):
    found, said = imported(svg(tmp_path,
                               '<text x="5" y="5">hola</text>'
                               '<image href="a.png" width="9" height="9"/>'
                               '<line x1="0" y1="0" x2="9" y2="0"/>'))
    assert found == [["LINE", 0, 175, 9, 175]]
    assert any("text" in text for text in said)
    assert any("image" in text for text in said)


def test_what_is_hidden_is_not_drawn_and_not_said(tmp_path):
    found, said = imported(svg(tmp_path,
                               '<g style="display:none"><line x1="0" y1="0" '
                               'x2="9" y2="9"/></g>'
                               '<line visibility="hidden" x1="0" y1="0" '
                               'x2="9" y2="9"/>'))
    assert found == [] and said == []


def test_a_size_in_other_units_is_said_and_the_rest_comes_in(tmp_path):
    found, said = imported(svg(tmp_path,
                               '<rect x="1" y="1" width="10mm" height="5"/>'
                               '<line x1="0" y1="0" x2="9" y2="0"/>'))
    assert found == [["LINE", 0, 175, 9, 175]]
    assert any("10mm" in text for text in said), said


def test_a_file_that_is_not_an_svg_says_so(tmp_path):
    other = tmp_path / "no.svg"
    other.write_text("<html></html>", encoding="utf-8")
    with pytest.raises(ValueError):
        imported(str(other))
    broken = tmp_path / "roto.svg"
    broken.write_text("<svg", encoding="utf-8")
    with pytest.raises(ValueError):
        imported(str(broken))


# -- into the source ------------------------------------------------------------------

def a_copy(tmp_path):
    for name in os.listdir(EXAMPLE):
        path = os.path.join(EXAMPLE, name)
        if os.path.isfile(path):
            shutil.copy(path, tmp_path)
    return str(tmp_path / "faro.gac")


def test_it_goes_in_at_the_cursor_and_ctrl_z_takes_it_all_out(tmp_path):
    path = a_copy(tmp_path)
    with open(path, encoding="utf-8", newline="") as f:
        before = f.read()
    viewer = Viewer(path, 1, "spectrum")
    drawn = len(viewer.steps.steps)
    drawing = svg(tmp_path, '<rect x="10" y="20" width="30" height="40"/>'
                            '<line x1="0" y1="0" x2="9" y2="0"/>'
                            '<text>no</text>')
    said = viewer.import_svg(drawing)
    assert viewer.error is None and len(said) == 1
    assert len(viewer.steps.steps) == drawn + 2
    assert viewer.steps.count == drawn + 2, "the cursor is not after them"
    assert [s[3] for s in viewer.steps.steps[-2:]] == [
        ["RECT", 10, 155, 40, 115], ["LINE", 0, 175, 9, 175]]
    assert "2" in viewer.imported
    viewer.take_back()
    with open(path, encoding="utf-8", newline="") as f:
        assert f.read() == before
    assert viewer.imported is None


def test_nothing_to_draw_writes_nothing(tmp_path):
    path = a_copy(tmp_path)
    with open(path, encoding="utf-8", newline="") as f:
        before = f.read()
    viewer = Viewer(path, 1, "spectrum")
    viewer.import_svg(svg(tmp_path, "<text>sólo texto</text>"))
    assert viewer.error and viewer.imported is None
    with open(path, encoding="utf-8", newline="") as f:
        assert f.read() == before


def test_the_window_opens_with_it_in(tmp_path, monkeypatch, capsys):
    """regac draw --import: in before the window opens, and said on the
    terminal, what was left out first."""
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    import pygame

    from regac import viewer

    path = a_copy(tmp_path)
    drawing = svg(tmp_path, '<line x1="0" y1="0" x2="9" y2="0"/><text>t</text>')
    key = lambda name: pygame.event.Event(pygame.KEYDOWN, key=name, mod=0)  # noqa: E731
    handed = iter([[], [key(pygame.K_q)]])
    monkeypatch.setattr(pygame.event, "get", lambda: next(handed))
    viewer.run(path, 1, "spectrum", scale=2, svg=drawing)
    out = [text for text in capsys.readouterr().out.splitlines()
           if not text.startswith("pygame")]   # its greeting, on first import
    assert "text" in out[0] and "1" in out[-1], out
    with open(path, encoding="utf-8") as f:
        assert "LINE 0 175 9 175" in f.read()
