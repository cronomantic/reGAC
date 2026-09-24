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
"""The example adventure, ejemplo/faro.gac, played from end to end.

It is the only thing here that walks the road an author walks -- a source of
their own, a project file, and the machines that come out of it -- rather than
starting from one of the eight decompiled adventures of 1986.  Which is the
point of it: what those cannot exercise, because it is ours and not theirs,
this does.  Words of its own that part an order, accented text, noises, names
for numbers.

Three things are checked, cheapest first: that it compiles and nothing in it
points anywhere it should not; that the pieces every machine needs come out of
a build; and that it can be played from the path outside to the lit lamp, on a
real Spectrum.
"""

import json
import os
import subprocess
import sys
import time

try:
    import pytest
except ImportError:
    pytest = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import dosbox  # noqa: E402
import emulator  # noqa: E402
import pc_game  # noqa: E402
from regac.binary import Database  # noqa: E402
from test_game_z80 import glyph_table, screen, wait_screen  # noqa: E402

EXAMPLE = os.path.join(ROOT, "ejemplo", "faro.gac")
PROJECT = os.path.join(ROOT, "ejemplo", "faro.toml")
SPECTRUM = os.path.join(ROOT, "z80", "spectrum")
DATABASE = os.path.join(SPECTRUM, "game.rgac")
SNAPSHOT = os.path.join(SPECTRUM, "game.sna")
LISTING = os.path.join(SPECTRUM, "game.lst")
ENTER = chr(13)

# The whole of it: the key, the door, the light, and the stairs.  The first
# one is two orders on one line, which is what this adventure's own separator
# is there to show.
WALKTHROUGH = ["COGE LLAVE Y NORTE", "ABRE PUERTA", "NORTE", "COGE CANDIL",
               "ENCIENDE CANDIL", "SUBE", "SUBE", "ENCIENDE LENTE"]

if pytest is not None:
    needs_tools = pytest.mark.skipif(
        not emulator.available(), reason="sjasmplus and ZEsarUX must be in tools/"
    )
    needs_dosbox = pytest.mark.skipif(
        not dosbox.available(), reason="NASM and DOSBox-X must be on the path"
    )
else:

    def needs_tools(func):
        return func

    needs_dosbox = needs_tools


def regac(*words):
    return subprocess.run([sys.executable, "-m", "regac"] + list(words),
                          cwd=ROOT, check=True, capture_output=True, text=True)


def compiled(tmp_path):
    """The adventure as a database, by way of its own source."""
    path = str(tmp_path / "faro.json")
    regac("compile", EXAMPLE, path)
    with open(path, encoding="utf-8") as f:
        return path, json.load(f)


def test_it_compiles_and_says_nothing_is_missing(tmp_path):
    """What an author runs before building anything: the round trip, and
    whether every number that points at something points at something that is
    there."""
    path, ddb = compiled(tmp_path)
    said = regac("check", path).stdout
    assert "round trip exact" in said, said
    assert "nothing points anywhere it should not" in said, said
    assert len(ddb["locations"]) == 5
    assert ddb["separators"] == ["Y", "LUEGO"], (
        "the words that part an order are the adventure's own"
    )
    assert any(b for b in ddb["font"]), "an adventure without a font prints blanks"


def test_every_machine_it_names_comes_out(tmp_path):
    """The project file names nine; a build writes nine media, and not one
    of them is empty."""
    where = str(tmp_path / "salida")
    regac("make", PROJECT, "--output", where)
    made = {}
    for folder in sorted(os.listdir(where)):
        for name in os.listdir(os.path.join(where, folder)):
            made[folder] = os.path.getsize(os.path.join(where, folder, name))
    assert set(made) == {"spectrum48", "spectrum128", "plus3", "cpc464",
                         "cpc6128", "msx", "next", "pcw", "pc"}, made
    assert all(size > 1024 for size in made.values()), made


@needs_tools
def test_it_can_be_played_to_the_end(tmp_path):
    """The walkthrough, typed at a Spectrum: the last order lights the lamp
    and the adventure says so."""
    path, ddb = compiled(tmp_path)
    regac("build", path, DATABASE, "-m", "spectrum48")
    emulator.assemble(os.path.join(SPECTRUM, "game.asm"), listing=LISTING,
                      defines=("NOISES",))
    glyphs = glyph_table(Database(ddb))
    won = ddb["messages"]["18"].split(".")[-1].strip()[:10]

    session = emulator.Session()
    try:
        session.load(SNAPSHOT)
        opening = wait_screen(session, glyphs, "sendero", timeout=60.0)
        assert any("sendero" in line for line in opening), (
            f"it never described where it starts: {opening}"
        )
        for order in WALKTHROUGH:
            session.type(order + ENTER)
            time.sleep(emulator.longer(3.0))
        end = screen(session, glyphs)
    finally:
        session.close()
    assert any(won in line for line in end), (
        f"the lamp was never lit: {end}"
    )


@needs_dosbox
def test_it_can_be_played_to_the_end_on_a_pc(tmp_path):
    """The same walkthrough, typed at a PC."""
    path, ddb = compiled(tmp_path)
    won = ddb["messages"]["18"].split(".")[-1].strip()[:10]
    folder = str(tmp_path / "pc")
    os.makedirs(folder)
    pc_game.build(ddb, folder)
    # The game goes on after the lamp is lit, so it is stopped from outside
    # once the walkthrough has had its time.
    said, _ = pc_game.play(folder, "".join(order + ENTER
                                           for order in WALKTHROUGH),
                           stop=True)
    assert "sendero" in said, f"it never described where it starts: {said}"
    assert won in said, f"the lamp was never lit: {said}"


if __name__ == "__main__":
    import pathlib
    import tempfile

    folder = pathlib.Path(tempfile.mkdtemp())
    test_it_compiles_and_says_nothing_is_missing(folder)
    print("it compiles and nothing is missing")
    test_every_machine_it_names_comes_out(folder)
    print("every machine it names comes out")
    test_it_can_be_played_to_the_end(folder)
    print("it can be played to the end")
