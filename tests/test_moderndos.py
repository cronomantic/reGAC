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
"""Modern DOS 8x8, the letters an adventure gets when it brings none: see
regac/moderndos.py.

What is in the repository is the dump; the source it came from is the
author's and sits in tools/, where it is only there to make the dump again.
"""

import os
import sys

try:
    import pytest
except ImportError:
    pytest = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from regac.moderndos import extract, letters  # noqa: E402

SOURCE = os.path.join(ROOT, "tools", "moderndos", "ModernDOS8x8.sfd")


def rows(character):
    at = 8 * (ord(character) - 32)
    return ["".join("#" if byte & (0x80 >> n) else "." for n in range(8))
            for byte in letters()[at:at + 8]]


def test_ninety_six_letters_and_the_space_is_empty():
    assert len(letters()) == 96 * 8
    assert rows(" ") == ["........"] * 8


def test_a_capital_keeps_its_last_row_free_and_its_hole():
    """regac composes an accented capital by lowering it a row, so a capital
    that takes a mark has to leave the bottom one free -- the Q's tail is the
    only one that does not, and no Q takes a mark; and the A keeps the hole
    its outlines draw round it, which is what counting crossings is for."""
    for capital in "ABCDEFGHIJKLMNOPRSTUVWXYZ":
        assert rows(capital)[7] == "........", capital
    assert rows("A") == [".#####..", "##...##.", "##...##.", "#######.",
                         "##...##.", "##...##.", "##...##.", "........"]


if pytest is not None:
    @pytest.mark.skipif(not os.path.exists(SOURCE),
                        reason="the Modern DOS source is not in tools/")
    def test_the_dump_is_what_the_source_draws():
        assert extract(SOURCE) == bytes(letters())
