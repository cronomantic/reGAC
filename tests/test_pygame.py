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
"""The pygame interpreter's ink, which was mended once without being run.

It had screen attributes like the machine it copies, and put the number of a
colour into one with an or -- and in a Spectrum attribute the bright is bit
six and not part of the colour, so an ink of twelve put its bit three into
the paper.  The mending was written by eye, because there was nothing here to
run pygame with; see doc/pendiente.md.  This runs it, with no window: the
dummy drivers are enough for everything but looking.
"""

import os
import sys

try:
    import pytest
except ImportError:
    pytest = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

try:
    import pygame  # noqa: F401
    HAVE_PYGAME = True
except ImportError:
    HAVE_PYGAME = False

from test_markers_z80 import adventure  # noqa: E402

if pytest is not None:
    needs_pygame = pytest.mark.skipif(not HAVE_PYGAME, reason="pygame is not installed")
else:

    def needs_pygame(func):
        return func


def printed(colour):
    """The attribute a letter gets after a change to `colour`, on a screen
    that starts in the adventure's own white on black."""
    from runGAC_pygame import GAC_Interpreter_Pygame

    screen = GAC_Interpreter_Pygame(adventure())
    try:
        assert screen.start_adventure(), "the adventure did not start"
        while not screen.cmd_queue.empty():  # whatever starting put there
            screen.cmd_queue.get_nowait()
        screen.cmd_queue.put((0x09, colour))
        screen.cmd_queue.put((0x01, "A"))
        screen.on_update()
        screen.on_update()
        return screen.att_screen[0]
    finally:
        import pygame

        pygame.quit()               # on_cleanup would leave the process too


@needs_pygame
def test_an_ink_of_eight_or_more_is_the_colour_bright_and_leaves_the_paper():
    for colour in range(16):
        attr = printed(colour)
        assert attr & 7 == colour & 7, f"ink {colour} came out as ink {attr & 7}"
        assert (attr >> 6) & 1 == colour >> 3, f"ink {colour} got the bright wrong"
        assert (attr >> 3) & 7 == 0, f"ink {colour} changed the paper to {(attr >> 3) & 7}"


if __name__ == "__main__":
    test_an_ink_of_eight_or_more_is_the_colour_bright_and_leaves_the_paper()
    print("the pygame interpreter settles an ink the way the Spectrum does")
