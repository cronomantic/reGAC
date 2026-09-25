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
"""regac draw --trace: an image over the picture, to draw on top of.

Decided by the user: the image is made as big as it fits without being put
out of shape, and centred; and it is one image for every picture, or a
folder with one to each, named by the picture's number."""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from regac.viewer import TRACE_ALPHA, Viewer, fitted  # noqa: E402

EXAMPLE = os.path.join(ROOT, "ejemplo", "faro.gac")


def test_an_image_fits_without_being_put_out_of_shape():
    assert fitted(512, 256, 768, 384) == (0, 0, 768, 384)
    assert fitted(100, 100, 768, 384) == (192, 0, 384, 384)      # square
    assert fitted(400, 100, 768, 384) == (0, 96, 768, 192)       # too wide


def test_one_image_for_all_or_one_to_each(tmp_path):
    single = tmp_path / "boceto.png"
    single.write_bytes(b"")
    viewer = Viewer(EXAMPLE, 1, "spectrum", str(single))
    assert viewer.trace_file() == str(single)
    viewer.other_picture(1)
    assert viewer.trace_file() == str(single)

    folder = tmp_path / "bocetos"
    folder.mkdir()
    for name in ("1.PNG", "2.jpg", "12.png", "notes.txt"):
        (folder / name).write_bytes(b"")
    viewer = Viewer(EXAMPLE, 1, "spectrum", str(folder))
    assert viewer.trace_file() == str(folder / "1.PNG")
    viewer.other_picture(1)                 # picture 2
    assert viewer.trace_file() == str(folder / "2.jpg")
    viewer.other_picture(1)                 # picture 3: none of its own
    assert viewer.trace_file() is None
    assert "nothing for #3" in viewer.trace_said()


def test_how_much_of_it_is_seen():
    viewer = Viewer(EXAMPLE, 1, "spectrum", "x.png")
    assert viewer.trace_alpha == TRACE_ALPHA
    for _ in range(9):
        viewer.stronger_trace(0.1)
    assert viewer.trace_alpha == 0.9
    for _ in range(12):
        viewer.stronger_trace(-0.1)
    assert viewer.trace_alpha == 0.1
    viewer.trace_on = False
    assert "hidden" in viewer.trace_said()
    assert Viewer(EXAMPLE, 1, "spectrum").trace_said() == ""


def test_the_window_lays_it_over_the_picture(tmp_path, monkeypatch):
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    import pygame

    from regac import viewer

    pygame.init()
    red = pygame.Surface((100, 100))        # square: it leaves the sides alone
    red.fill((255, 0, 0))
    image = str(tmp_path / "rojo.png")
    pygame.image.save(red, image)

    screens = []
    flip = pygame.display.flip

    def kept():
        flip()
        screens.append(pygame.display.get_surface().copy())

    monkeypatch.setattr(pygame.display, "flip", kept)
    key = lambda name: pygame.event.Event(pygame.KEYDOWN, key=name, mod=0)  # noqa: E731
    handed = iter([[], [key(pygame.K_t)], [key(pygame.K_t)],
                   [key(pygame.K_PLUS)], [key(pygame.K_q)]])
    monkeypatch.setattr(pygame.event, "get", lambda: next(handed))
    viewer.run(EXAMPLE, 1, "spectrum", scale=3, trace=image)

    shown, hidden, again, more = screens[-4:]
    middle, side = (384, 300), (20, 300)
    assert hidden.get_at(side) == shown.get_at(side), "the sides were touched"
    a, b, c = shown.get_at(middle), hidden.get_at(middle), more.get_at(middle)
    assert again.get_at(middle) == a
    assert a.r > b.r and abs(a.r - (255 + b.r) / 2) <= 2, (a, b)
    assert c.r > a.r, "more of it is not more red"
