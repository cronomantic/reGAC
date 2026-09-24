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
"""The whole interpreter playing a real adventure on a PC.

MegaCorp, as on the Amstrad: it opens asking for its password, takes it, and
answers what it is asked -- a word it knows and one it does not -- until the
player says to stop, and then the game ends and the machine goes back to DOS
at a key.  Typed through the keyboard's own interrupt, which is what the
interpreter reads; see tests/pc_game.py.
"""

import json
import os
import sys

try:
    import pytest
except ImportError:
    pytest = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import dosbox  # noqa: E402
import pc_game  # noqa: E402
from pc_game import ENTER  # noqa: E402

ADVENTURE = os.path.join(ROOT, "snapshots", "megacorp2.json")
# Its own code, which is in its own vocabulary: room 5000 takes verb 29,
# and verb 29 of MegaCorp is REBECA.
PASSWORD = "REBECA"

if pytest is not None:
    needs_tools = pytest.mark.skipif(
        not dosbox.available() or not os.path.exists(ADVENTURE),
        reason="NASM and DOSBox-X on the path, with a decompiled adventure",
    )
else:

    def needs_tools(func):
        return func


def megacorp():
    with open(ADVENTURE, encoding="utf-8") as f:
        return json.load(f)


@needs_tools
def test_it_asks_and_answers_on_a_pc(tmp_path):
    ddb = megacorp()
    folder = str(tmp_path)
    pc_game.build(ddb, folder)
    said, screen = pc_game.play(folder, PASSWORD + ENTER + "I" + ENTER
                                + "XYZZY" + ENTER + "JARRO" + ENTER
                                + "FIN" + ENTER + "S" + "X")
    messages = ddb["messages"]
    assert said.startswith("INTRODUZCA LA CLAVE"), said
    assert messages["240"] + PASSWORD in said, "it never asked, or never read"
    assert "Una ancha calle de la Ciudad" in said, (
        f"the password took it nowhere: {said}")
    assert "Llevo conmigo:un disco metalico" in said, said
    # a word it does not know, and one it knows with nothing to do about it
    assert messages["240"] + "XYZZY" + chr(10) + messages["242"] in said, said
    assert messages["240"] + "JARRO" + chr(10) + messages["241"] in said, said
    assert said.rstrip().endswith(messages["244"]), said
    assert screen is not None, "the game never ended"


@needs_tools
def test_the_text_is_under_the_picture_in_the_pictures_colours(tmp_path):
    """The text is written in the values its colours come to in the picture
    on the screen: the ink white and the paper black, each to whichever of
    the four values the picture gave it.  Read off the last picture's head in
    the database, and off the card when the game has ended."""
    from regac.binary import Reader
    ddb = megacorp()
    folder = str(tmp_path)
    pc_game.build(ddb, folder)
    _, screen = pc_game.play(folder, PASSWORD + ENTER + "FIN" + ENTER + "S"
                             + "X")
    assert screen is not None, "the game never ended"
    with open(os.path.join(folder, "game.rgac"), "rb") as f:
        heads = Reader(f.read()).picture_inks()
    # the password leads to the street, room one, which shows picture one
    head = heads[str(ddb["locations"]["1"]["graphic_id"])]
    values = [(head[2 + n // 4] >> (2 * (n % 4))) & 3 for n in range(16)]
    ink, paper = values[7], values[0]
    # the bottom text row, the question of the quit, has both in it
    seen = {pc_game.pixel(screen, x, y)
            for y in range(192, 200) for x in range(320)}
    assert seen <= {ink, paper}, (
        f"the text has values {seen}, and white comes to {ink} and black to "
        f"{paper} in the picture")
    assert ink in seen and paper in seen
