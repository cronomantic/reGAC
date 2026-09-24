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
# The interpreters in z80/ and x86/ are not part of this program and are given
# under the MIT licence instead: see z80/LICENSE and x86/LICENSE.
#
"""SAVE and LOAD on a PC: one file beside the program, named after it.

MegaCorp saves with SAVE and loads with LOAD, and looks after either.  A game
saved one street along comes back there in a game started afresh; and a LOAD
with nothing to load leaves the game where it was.  The file is the block
every machine saves, byte for byte the same size, starting with the room.
"""

import os
import struct
import sys

try:
    import pytest
except ImportError:
    pytest = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pc_game  # noqa: E402
from pc_game import ENTER  # noqa: E402
from test_game_pc import PASSWORD, megacorp, needs_tools  # noqa: E402

SAVED = "GAME.SAV"              # the program is GAME.EXE
# What a game is, on every machine: see z80/common/conditions.asm.
GAME_BYTES = 2 + 1 + 1 + 2 + 1 + 32 * 2 + 32 + 128 + 512


def test_the_block_is_the_one_every_machine_saves():
    """743 bytes, which is what the others save since obj_entry left it."""
    assert GAME_BYTES == 743


@needs_tools
def test_a_game_saved_comes_back_in_another(tmp_path):
    ddb = megacorp()
    folder = str(tmp_path)
    pc_game.build(ddb, folder)
    street = ddb["locations"]["6"]["desc"][:30]
    first = ddb["locations"]["1"]["desc"][:30]

    said, screen = pc_game.play(folder, PASSWORD + ENTER + "N" + ENTER
                                + "SAVE" + ENTER + "FIN" + ENTER + "S" + "X")
    assert screen is not None, f"the first game never ended: {said}"
    path = os.path.join(folder, SAVED)
    assert os.path.exists(path), "SAVE wrote nothing beside the program"
    with open(path, "rb") as f:
        game = f.read()
    assert len(game) == GAME_BYTES
    assert struct.unpack_from("<H", game)[0] == 6, "not the room it was in"

    said, screen = pc_game.play(folder, PASSWORD + ENTER + "LOAD" + ENTER
                                + "FIN" + ENTER + "S" + "X")
    assert screen is not None, f"the second game never ended: {said}"
    after = said[said.index("LOAD"):]
    assert street in after, f"LOAD did not bring the game back: {after}"
    assert first not in after


@needs_tools
def test_a_load_with_nothing_to_load_leaves_the_game_alone(tmp_path):
    ddb = megacorp()
    folder = str(tmp_path)
    pc_game.build(ddb, folder)
    said, screen = pc_game.play(folder, PASSWORD + ENTER + "LOAD" + ENTER
                                + "FIN" + ENTER + "S" + "X")
    assert screen is not None, f"the game never ended: {said}"
    after = said[said.index("LOAD"):]
    assert ddb["locations"]["1"]["desc"][:30] in after, after
    assert not os.path.exists(os.path.join(folder, SAVED))
