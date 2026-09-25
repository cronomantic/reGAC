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
"""regac draw: a picture looked at while it is being written.

What matters most is that what it shows is the picture: walked to the end an
order at a time, or back and forth, it has to come out exactly as the
renderer draws it whole, on every machine, because the renderer is what the
interpreters are held to.  Then that it follows the source when it is saved,
and keeps the last good picture when the source does not read.  And the
window itself is run, with no screen, on keys handed to it.
"""

import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from regac.devices import device_for  # noqa: E402
from regac.gfx import Renderer  # noqa: E402
from regac.viewer import (AMSTRAD_MACHINES, SPECTRUM_MACHINES, Steps,  # noqa: E402
                          Viewer, gac_point, machines_for, read_adventure,
                          steps_of)

FARO = os.path.join(ROOT, "ejemplo", "faro.gac")
# Every order there is, the three fills among them, which the lighthouse of
# the example has one of: a walk that skipped fills passed with it alone.
EVERY_ORDER = {"gfx": {
    "1": [["BORDER", 1], ["PAPER", 6], ["INK", 2], ["BRIGHT", 1],
          ["RECT", 20, 60, 120, 160], ["ELLIPSE", 140, 70, 230, 150],
          ["FILL", 70, 100], ["INK", 4], ["FLASH", 1], ["SHADE", 180, 110],
          ["FLASH", 0], ["CALL", 2], ["PENS", 1, 2], ["BGFILL", 70, 100],
          ["PLOT", 250, 170]],
    "2": [["INK", 1], ["LINE", 0, 50, 255, 58], ["FILL", 10, 170]],
}}


def whole(ddb, picture, machine):
    device = device_for(machine, ddb["gfx"], picture, ddb)
    return Renderer(ddb["gfx"], device).run(int(picture)).to_rgb()


def test_walked_to_the_end_it_is_the_picture_on_every_machine():
    for machine in SPECTRUM_MACHINES:
        for ddb in (read_adventure(FARO, machine), EVERY_ORDER):
            for picture in ddb["gfx"]:
                steps = Steps(ddb, picture, machine)
                for count in range(len(steps.steps) + 1):
                    steps.go(count)
                assert steps.rgb() == whole(ddb, picture, machine), (
                    f"#{picture} on {machine} walked an order at a time is "
                    f"not the picture")


def test_back_and_forth_it_is_still_the_picture():
    ddb, picture = EVERY_ORDER, "1"
    steps = Steps(ddb, picture, "cpc")
    end = len(steps.steps)
    for count in (end, 3, end - 1, 0, end, 5, end):
        steps.go(count)
    assert steps.count == end
    assert steps.rgb() == whole(ddb, picture, "cpc")


def test_a_call_is_opened_where_it_stands():
    gfx = {"1": [["INK", 2], ["CALL", 2], ["PLOT", 5, 60]],
           "2": [["LINE", 0, 50, 10, 50], ["CALL", 3]],
           "3": [["PLOT", 1, 51]]}
    walked = [(depth, picture, number, order[0])
              for depth, picture, number, order in steps_of(gfx, 1)]
    assert walked == [(0, 1, 1, "INK"), (0, 1, 2, "CALL"),
                      (1, 2, 1, "LINE"), (1, 2, 2, "CALL"),
                      (2, 3, 1, "PLOT"), (0, 1, 3, "PLOT")]


def test_a_call_too_deep_is_not_walked_because_it_is_not_drawn():
    gfx = {"1": [["CALL", 1], ["PLOT", 5, 60]]}
    deepest = max(depth for depth, *_ in steps_of(gfx, 1))
    assert deepest == Renderer.MAX_DEPTH


def test_the_last_order_says_what_it_laid():
    ddb = {"gfx": {"1": [["LINE", 10, 100, 19, 100]]}}
    steps = Steps(ddb, 1, "next")
    steps.go(1)
    assert steps.laid() == {(x, 175 - 100) for x in range(10, 20)}
    steps.go(0)
    assert steps.laid() == set()


def test_the_pointer_is_in_the_coordinates_the_orders_are_written_in():
    assert gac_point(0, 0, 768, 384) == (0, 175)
    assert gac_point(767, 383, 768, 384) == (255, 48)
    assert gac_point(384, 192, 768, 384) == (128, 111)
    assert gac_point(768, 10, 768, 384) is None


def test_an_amstrad_adventure_is_drawn_only_where_its_rules_are():
    assert machines_for({"model": "CPC"}) == AMSTRAD_MACHINES
    assert machines_for({}) == SPECTRUM_MACHINES


def test_it_follows_the_source_and_keeps_the_last_picture_that_read(tmp_path):
    folder = str(tmp_path)
    for name in os.listdir(os.path.dirname(FARO)):
        path = os.path.join(os.path.dirname(FARO), name)
        if os.path.isfile(path):
            shutil.copy(path, folder)
    source = os.path.join(folder, "faro.gac")
    viewer = Viewer(source)
    before = len(viewer.steps.steps)
    with open(source, encoding="utf-8") as f:
        text = f.read()
    picture = viewer.picture
    marker = f"#{picture}\n"
    assert marker in text, "the picture is not where this test looks for it"

    def saved(text, stamp):
        with open(source, "w", encoding="utf-8") as f:
            f.write(text)
        os.utime(source, ns=(stamp, stamp))

    saved(text.replace(marker, marker + "  PLOT 1 60\n", 1), 10**18)
    assert viewer.changed()
    assert len(viewer.steps.steps) == before + 1 and viewer.error is None
    drawn = viewer.steps.rgb()

    saved(text.replace(marker, marker + "  PLOT 1\n", 1), 2 * 10**18)
    assert viewer.changed()
    assert viewer.error, "a source that does not read said nothing"
    assert viewer.steps.rgb() == drawn, "the last good picture went"
    assert not viewer.changed(), "it read a file nobody had saved again"


def test_the_window_runs_on_the_keys_it_is_given(monkeypatch):
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    import pygame

    from regac import viewer

    def key(name, mod=0):
        return pygame.event.Event(pygame.KEYDOWN, key=name, mod=mod)

    handed = iter([
        [key(pygame.K_HOME)], [key(pygame.K_RIGHT)],
        [key(pygame.K_RIGHT, pygame.KMOD_SHIFT)], [key(pygame.K_LEFT)],
        [pygame.event.Event(pygame.MOUSEMOTION, pos=(300, 100))],
        [key(pygame.K_m)], [key(pygame.K_h)], [key(pygame.K_PAGEDOWN)],
        [key(pygame.K_END)], [pygame.event.Event(pygame.QUIT)],
    ])
    monkeypatch.setattr(pygame.event, "get", lambda: next(handed))
    viewer.run(FARO)                    # and it returns: QUIT was handed


def test_a_json_reads_as_well(tmp_path):
    ddb = read_adventure(FARO, "spectrum")
    path = str(tmp_path / "faro.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(ddb, f)
    assert read_adventure(path, "spectrum")["gfx"] == ddb["gfx"]
