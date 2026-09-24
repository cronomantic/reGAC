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

And one written on an Amstrad, played through with the Amstrad's rules: La
guerra de las vajillas, off its disk in juegos/.
"""

import json
import os
import re
import sys

try:
    import pytest
except ImportError:
    pytest = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import amstrad_games  # noqa: E402
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
    needs_amstrad_games = pytest.mark.skipif(
        not dosbox.available() or not amstrad_games.available(),
        reason="NASM and DOSBox-X on the path, with the Amstrad disks in juegos/",
    )
else:

    def needs_tools(func):
        return func

    needs_amstrad_games = needs_tools


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
                                + "FIN" + ENTER + "S" + ENTER + "X")
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
                             + ENTER + "X")
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


def squeezed(text):
    """Text with every space and every end of line taken out: where the lines
    break is the screen's business, and what is said is this test's."""
    return "".join(text.split())


@needs_amstrad_games
def test_an_adventure_off_an_amstrad_is_played_through_on_a_pc(tmp_path):
    """La guerra de las vajillas, first part, played on a PC: out of the
    desert into the house, which has no picture and so gives the text the
    whole screen; the tin taken, which is worth two points; the inventory; back
    out and into the desert, which has a picture again; a word it does not
    know; the points; and QUIT, which asks, and at a yes ends the game with
    the score.  The last picture on the screen is then held to the
    reference, drawn with the Amstrad's rules as the game drew it."""
    from regac.devices import cga_screen, device_for
    from regac.gfx import Renderer
    ddb = amstrad_games.amstrad_adventure("vajillas1")
    assert ddb["model"] == "CPC"
    folder = str(tmp_path)
    pc_game.build(ddb, folder)
    said, screen = pc_game.play(folder, "N" + ENTER + "COGE LATA" + ENTER
                                + "INVENTARIO" + ENTER + "S" + ENTER + "S"
                                + ENTER + "XYZZY" + ENTER + "PUNTOS" + ENTER
                                + "QUIT" + ENTER + "S" + ENTER + "X")
    assert screen is not None, f"the game never ended: {said}"
    rooms = ddb["locations"]
    messages = ddb["messages"]
    heard = squeezed(said)
    wanted = [
        rooms["1"]["desc"],                             # where it starts
        "N", rooms["4"]["desc"], messages["253"],       # the house
        "AUTOPELADOR", "LATA DE ACEITE",
        "COGELATA", messages["254"],                    # taken
        "INVENTARIO", messages["239"], "LATA DE ACEITE",
        "S", rooms["1"]["desc"],
        "S", rooms["3"]["desc"],                        # the desert
        "XYZZY", messages["242"],
        "PUNTOS", messages["249"],
        "QUIT", messages["244"],
        messages["249"],                                # the score
    ]
    at = 0
    for piece in wanted:
        found = heard.find(squeezed(piece), at)
        assert found >= 0, f"after {heard[:at][-80:]!r}, no {piece!r}: {said}"
        at = found + len(squeezed(piece))
    assert heard.endswith(squeezed(messages["255"])), said
    # and the score it tells at the end is the one it told when asked: the
    # tin is worth two and what else the adventure adds is its own business
    asked = re.search(re.escape("PUNTOS" + squeezed(messages["249"])) + "([0-9]+)",
                      heard)
    told = re.search(re.escape(squeezed(messages["249"])) + "([0-9]+)"
                     + re.escape(squeezed(messages["250"])), heard)
    assert asked and told and asked.group(1) == told.group(1), said
    # the desert's picture, as the reference draws it with the Amstrad's rules
    gfx = ddb["gfx"]
    number = rooms["3"]["graphic_id"]
    drawn = cga_screen(Renderer(gfx, device_for("cga", gfx, number, ddb))
                       .run(number))
    picture = [pc_game.pixel(screen, x, y) for y in range(128)
               for x in range(32, 288)]
    reference = [pc_game.pixel(drawn, x, y) for y in range(128)
                 for x in range(32, 288)]
    apart = sum(1 for a, b in zip(picture, reference) if a != b)
    assert apart == 0, f"{apart} points of picture {number} differ"
    # And the text can be read: pen one on pen nought, as the original prints
    # it, in the values the picture dealt them -- and pen nought is the
    # background, the same colour as the border and the rest of the screen.
    # The letters are Modern DOS, which deGAC gives an adventure off an
    # Amstrad: it printed with the firmware's, which are not ours to carry.
    from regac.devices import cga_amstrad_colours
    _, _, pens = cga_amstrad_colours(gfx, number,
                                     ddb["gfx_inks"].get(str(number)))
    text = {pc_game.pixel(screen, x, y) for y in range(128, 200)
            for x in range(320)}
    assert pens[0] == 0 and text == {0, pens[1]}, (
        f"the text is in values {text}; pen one is {pens[1]}")
