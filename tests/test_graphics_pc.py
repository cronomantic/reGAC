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
"""Drawing on a PC's CGA, compared against the reference renderer.

The same trade as every other machine: each picture is drawn twice, once by
the reference and once by our own 8086 code running in DOSBox-X, and the two
are compared.  The build draws every picture of its database in turn and
writes the card's memory after each to a file named after it; the test reads
those when the machine has gone, and compares them with `cga_screen`, which is
the same picture as the card's memory would hold it.

What this checks besides the drawing is what is the CGA's own: the rows in two
banks, four pixels to a byte, and the four colours each picture was given --
the colour a pixel is written in is the value its colour comes to among them.
An adventure off an Amstrad is drawn with the Amstrad's rules, its four pens
dealt out among the four values, and the fill that stops where the pen
changes reads them back off the screen.
"""

import glob
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

import amstrad_games  # noqa: E402
import dosbox  # noqa: E402
from regac.binary import Database  # noqa: E402
from regac.devices import cga_screen, device_for, from_an_amstrad  # noqa: E402
from regac.gfx import Renderer  # noqa: E402
from regac.media import mz_exe  # noqa: E402
from test_graphics_next import adventure  # noqa: E402

X86 = os.path.join(ROOT, "x86")
SOURCE = os.path.join(X86, "test_picture.asm")
ADVENTURES = os.path.join(ROOT, "snapshots")

ACROSS = 80                     # bytes to a row of the card
BANK = 0x2000                   # where the odd rows start

if pytest is not None:
    needs_tools = pytest.mark.skipif(
        not dosbox.available(), reason="NASM and DOSBox-X must be on the path"
    )
    needs_adventures = pytest.mark.skipif(
        not dosbox.available()
        or not glob.glob(os.path.join(ADVENTURES, "*.json")),
        reason="NASM and DOSBox-X on the path, with decompiled adventures",
    )
    from test_graphics_next import drawings
    # An adventure off an Amstrad, drawn here with the Amstrad's rules: the
    # same drawings the Amstrad itself is held to in test_graphics_cpc.py.
    from test_graphics_cpc import drawings as amstrad_drawings
    needs_amstrad_games = pytest.mark.skipif(
        not dosbox.available() or not amstrad_games.available()
        or not os.environ.get("REGAC_SLOW"),
        reason="set REGAC_SLOW=1, with NASM, DOSBox-X and the Amstrad disks "
               "in juegos/",
    )
else:

    def needs_tools(func):
        return func

    needs_adventures = needs_tools

    def drawings(func):
        return func

    amstrad_drawings = needs_amstrad_games = drawings


def draw_every_picture(ddb, folder):
    """Build the test build over `ddb`, run it, and give back what the card
    held after each picture, by the picture's number."""
    database = os.path.join(folder, "picture.rgac")
    with open(database, "wb") as f:
        f.write(Database(ddb, machine="pc").build())
    defines = {"DATABASE": '"' + database.replace(os.sep, "/") + '"'}
    if from_an_amstrad(ddb):
        defines["AMSTRAD_PICTURES"] = 1
    image = dosbox.assemble(
        SOURCE, os.path.join(folder, "picture.bin"), include=X86,
        defines=defines)
    with open(image, "rb") as f:
        exe = mz_exe(f.read())
    with open(os.path.join(folder, "PICTURE.EXE"), "wb") as f:
        f.write(exe)
    dosbox.run(folder, "PICTURE.EXE", cycles="max")
    drawn = {}
    for key in ddb["gfx"]:
        name = os.path.join(folder, f"P{int(key):04X}.BIN")
        if os.path.exists(name):
            with open(name, "rb") as f:
                drawn[int(key)] = f.read()
    return drawn


def reference(ddb, number):
    gfx = ddb["gfx"]
    device = device_for("cga", gfx, number, ddb)
    return cga_screen(Renderer(gfx, device).run(number))


def first_difference(ours, theirs):
    """Where the first pixel that differs is, as (x, row), and the two
    values there."""
    for at, (a, b) in enumerate(zip(ours, theirs)):
        if a != b:
            bank, offset = divmod(at, BANK)
            row = (offset // ACROSS) * 2 + bank
            byte = offset % ACROSS
            for pixel in range(4):
                shift = 6 - 2 * pixel
                if (a >> shift) & 3 != (b >> shift) & 3:
                    x = (byte - 8) * 4 + pixel
                    return x, row, (a >> shift) & 3, (b >> shift) & 3
    return None


def pixels_apart(ours, theirs):
    return sum(1 for a, b in zip(ours, theirs) if a != b
               for pixel in range(4) if (a >> 2 * pixel) & 3 != (b >> 2 * pixel) & 3)


def draw_on_both(name, commands, folder, off_an_amstrad=False):
    ddb = adventure(commands)
    if off_an_amstrad:
        ddb["model"] = "CPC"
    drawn = draw_every_picture(ddb, folder)
    assert 1 in drawn, f"{name}: the PC never wrote the picture"
    theirs = reference(ddb, 1)
    ours = drawn[1]
    assert len(ours) == len(theirs), f"{name}: {len(ours)} bytes written"
    where = first_difference(ours, theirs)
    assert where is None, (
        f"{name}: {pixels_apart(ours, theirs)} pixels differ, the first at "
        f"({where[0]}, {where[1]}): ours {where[2]}, theirs {where[3]}"
    )


@needs_tools
@drawings
def test_the_pc_draws_what_the_reference_draws(name, commands, tmp_path):
    draw_on_both(name, commands, str(tmp_path))


@needs_tools
@amstrad_drawings
def test_a_picture_off_an_amstrad_is_drawn_with_the_amstrads_rules(
        name, commands, tmp_path):
    draw_on_both(name, commands, str(tmp_path), off_an_amstrad=True)


def pictures_that_differ(adventures, folder):
    """Draw every picture of each adventure on the PC and say which differ
    from the reference."""
    wrong = {}
    for name, ddb in adventures:
        where = folder / name.split(".")[0]
        where.mkdir()
        drawn = draw_every_picture(ddb, str(where))
        for key in ddb["gfx"]:
            number = int(key)
            if number not in drawn:
                wrong[f"{name} {number}"] = "never written"
                continue
            apart = pixels_apart(drawn[number], reference(ddb, number))
            if apart:
                wrong[f"{name} {number}"] = f"{apart} pixels"
    return wrong


def spectrum_adventures():
    out = []
    for path in sorted(glob.glob(os.path.join(ADVENTURES, "*.json"))):
        with open(path, encoding="utf-8") as f:
            ddb = json.load(f)
        if not from_an_amstrad(ddb):
            out.append((os.path.basename(path), ddb))
    return out


ADVENTURE_NAMES = [os.path.basename(path) for path in
                   sorted(glob.glob(os.path.join(ADVENTURES, "*.json")))]


# One adventure a test, so that a parallel run spreads them: the eight
# together are a minute and a quarter in one worker.
@needs_adventures
@(pytest.mark.parametrize("name", ADVENTURE_NAMES) if pytest else drawings)
def test_every_picture_of_an_adventure_comes_out_the_same(name, tmp_path):
    """The primitives one at a time prove the sums; the adventures prove they
    hold together.  Every picture of each adventure to hand is drawn on the PC
    and compared with the reference."""
    with open(os.path.join(ADVENTURES, name), encoding="utf-8") as f:
        ddb = json.load(f)
    wrong = pictures_that_differ([(name, ddb)], tmp_path)
    assert not wrong, f"{len(wrong)} pictures differ: {wrong}"


@needs_amstrad_games
def test_every_picture_off_an_amstrad_comes_out_the_same(tmp_path):
    """The six adventures written on an Amstrad, every picture of them drawn
    with the Amstrad's rules, against the reference those pictures were
    checked with on the original."""
    adventures = []
    for name, path in amstrad_games.amstrad_adventures():
        with open(path, encoding="utf-8") as f:
            adventures.append((name, json.load(f)))
    wrong = pictures_that_differ(adventures, tmp_path)
    assert not wrong, f"{len(wrong)} pictures differ: {wrong}"
