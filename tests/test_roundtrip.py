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
"""The round trip is the acceptance test for the source format.

Decompiling a database to source and compiling it back must reproduce the
database exactly.  Anything the source format cannot express shows up here.
"""

import glob
import json
import os
import sys

try:
    import pytest
except ImportError:  # the suite also runs standalone, see the bottom of the file
    pytest = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from regac.conds import compile_block, render_block  # noqa: E402
from regac.devices import SpectrumDevice, make  # noqa: E402
from regac.gfx import SOURCE_ROWS, Renderer  # noqa: E402
CHAR_WIDTH = SpectrumDevice.char_width
PICTURE_ROWS = SOURCE_ROWS
from regac.srcgen import generate  # noqa: E402
from regac.srcparse import parse  # noqa: E402
from regac.binary import Database, Reader  # noqa: E402
from regac.text import Packer, TextStore  # noqa: E402

DATABASES = sorted(glob.glob(os.path.join(ROOT, "snapshots", "*.json")))


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def through_json(value):
    """Normalise integer keys and tuples the way a saved database is stored."""
    return json.loads(json.dumps(value))


def ids(paths):
    return [os.path.basename(p) for p in paths]


if pytest is not None:
    needs_databases = pytest.mark.skipif(
        not DATABASES, reason="no decompiled databases available"
    )
    parametrized = pytest.mark.parametrize("path", DATABASES, ids=ids(DATABASES))
else:

    def needs_databases(func):
        return func

    def parametrized(func):
        return func


@needs_databases
@parametrized
def test_database_round_trip(path):
    original = load(path)
    name = os.path.basename(path)
    rebuilt = through_json(parse(generate(original, name), name))
    assert rebuilt == original


@needs_databases
@parametrized
def test_condition_blocks_round_trip(path):
    ddb = load(path)
    blocks = [ddb["hpcs"], ddb["lpcs"]] + list(ddb["lcs"].values())
    for block in blocks:
        assert compile_block(render_block(block)) == through_json(block)


def test_left_to_right_evaluation():
    """GAC has no operator precedence, so a nested right operand must keep the
    brackets the renderer puts around it."""
    code = [["PUSH", 1], ["PUSH", 2], ["PUSH", 3], ["+"], ["+"]]
    line = render_block(code)[0]
    assert line == "1 + ( 2 + 3 )"
    assert compile_block([line]) == code


def test_prefix_operand_is_not_greedy():
    """NOT VERB 1 AND NOUN 2 must negate only the verb test."""
    code = compile_block(["NOT VERB 1 AND NOUN 2"])
    assert code == [
        ["PUSH", 1],
        ["VERB"],
        ["NOT"],
        ["PUSH", 2],
        ["NOUN"],
        ["AND"],
    ]


def test_dangling_value_is_preserved():
    """A value the original bytecode pushes but never consumes keeps its place."""
    code = [["PUSH", 0], ["PUSH", 6], ["VERB"], ["IF"], ["WAIT"], ["END"]]
    assert render_block(code)[0] == "0 IF ( VERB 6 ) WAIT END"
    assert compile_block(render_block(code)) == code


@needs_databases
@parametrized
def test_every_picture_draws(path):
    """Every picture of every adventure draws without falling over."""
    gfx = load(path)["gfx"]
    marks = {"PLOT", "LINE", "RECT", "ELLIPSE", "SHADE"}

    def marks_pixels(pid, depth=0):
        """Whether a picture, or one it calls, puts anything on the bitmap.
        Some pictures only set the border or wash the screen with a colour."""
        commands = gfx.get(str(pid)) or []
        if depth > 8:
            return False
        for command in commands:
            if command[0] in marks:
                return True
            if command[0] == "CALL" and marks_pixels(command[1], depth + 1):
                return True
        return False

    for pid in gfx:
        picture = Renderer(gfx).run(int(pid))
        assert len(picture.attrs) == CHAR_WIDTH * 24
        if marks_pixels(pid):
            assert any(picture.pixels), f"picture {pid} came out blank"


def test_the_origin_is_at_the_bottom():
    """GAC counts y upwards from the bottom of the screen, as BASIC did."""
    picture = Renderer({1: [["PLOT", 0, 175], ["PLOT", 255, 48]]}).run(1)
    assert picture.is_boundary(0, 0), "y=175 should be the top row"
    assert picture.is_boundary(255, PICTURE_ROWS - 1), "y=48 should be the bottom row"


def test_a_fill_covers_the_same_ground_on_every_machine():
    """The whole point of the device split.  Every machine that keeps the
    original 256 pixels across must fill exactly the same ground, whether it
    carries colour per cell, per row of eight, or per pixel."""
    gfx = {1: [["RECT", 64, 100, 120, 60], ["PAPER", 2], ["BGFILL", 80, 80],
               ["SHADE", 80, 80]]}
    spectrum = Renderer(gfx, make("spectrum"))
    spectrum.run(1)
    for machine in ("sam", "next", "msx", "msx2", "cpc", "pcw"):
        target = Renderer(gfx, make(machine))
        target.run(1)
        assert spectrum.fill_coverage == target.fill_coverage, machine


def test_every_machine_draws_the_same_picture():
    """A picture drawn on each machine must come out the same size as that
    machine's screen, and never blank."""
    gfx = {1: [["RECT", 40, 160, 200, 60], ["PAPER", 4], ["BGFILL", 120, 110]]}
    for machine in ("spectrum", "sam", "next", "msx", "msx2", "cpc", "pcw"):
        device = Renderer(gfx, make(machine)).run(1)
        rows = device.to_rgb()
        assert len(rows) == device.height, machine
        assert len(rows[0]) == device.width, machine
        assert len({tuple(p) for row in rows for p in row}) > 1, machine


def test_a_fill_stays_inside_the_lines():
    gfx = {1: [["RECT", 64, 100, 120, 60], ["PAPER", 2], ["BGFILL", 80, 80]]}
    picture = Renderer(gfx).run(1)

    def paper_at(x, y):
        return (picture.attrs[(y >> 3) * CHAR_WIDTH + (x >> 3)] >> 3) & 7

    assert paper_at(80, 95) == 2, "the inside of the box should be filled"
    assert paper_at(8, 8) == 7, "the fill should not escape the box"


def adventure_text(ddb):
    texts = list(ddb["messages"].values())
    texts += [o["name"] for o in ddb["objects"].values()]
    texts += [l["desc"] for l in ddb["locations"].values()]
    return [t for t in texts if t]


@needs_databases
@parametrized
def test_text_survives_packing(path):
    """Every message must come back exactly, and on its own: the interpreter
    prints message 137 without reading the 136 before it."""
    texts = adventure_text(load(path))
    store = TextStore(texts)
    for index, original in enumerate(texts):
        assert store.read(index) == original
    # unpacking out of order must give the same answers
    for index in range(len(texts) - 1, -1, -1):
        assert store.read(index) == texts[index]


@needs_databases
@parametrized
def test_text_packs_to_about_half(path):
    """The scheme is meant to halve the text.  Guard against drifting back.

    It is a little over half now, not a little under: the compressor has a
    fixed 128 pairs rather than whatever codes the alphabet left it, which
    costs about eight per cent and buys an adventure in Catalan the same deal
    as one in English.
    """
    store = TextStore(adventure_text(load(path)))
    assert store.ratio < 0.58, f"{store.ratio:.0%} of the original"
    # the 8 bit routine needs room for the unpacking stack, and not much
    assert store.packer.depth() < 32


def read_back(ddb, **options):
    """Build the binary database and read it the way the 8 bit routine will."""
    database = Database(ddb, **options)
    reader = Reader(database.build())
    first_pair, pairs, packed = reader.text()
    texts = [
        database.store.charset.decode(Packer(pairs, first_pair).unpack(m))
        for m in packed
    ]
    return database, reader, texts


@needs_databases
@parametrized
def test_binary_database_round_trips(path):
    """Everything written must come back: the format is only right if the
    reader can rebuild what went in."""
    ddb = load(path)
    database, reader, texts = read_back(ddb)
    assert texts == database.texts

    high, low, locals_ = reader.conditions()
    assert high == through_json(ddb["hpcs"])
    assert low == through_json(ddb["lpcs"])
    assert locals_ == {k: through_json(v) for k, v in ddb["lcs"].items()}

    objects = reader.objects()
    for key, original in ddb["objects"].items():
        got = objects[key]
        assert got["weight"] == original["weight"]
        assert got["initial_loc"] == original["initial_loc"]
        assert texts[got["name"]] == original["name"]

    locations = reader.locations()
    for key, original in ddb["locations"].items():
        got = locations[key]
        assert got["graphic_id"] == original["graphic_id"]
        assert got["exits"] == original["exits"]
        assert texts[got["desc"]] == original["desc"]

    assert reader.graphics() == {
        k: through_json(v) for k, v in ddb["gfx"].items()
    }


@needs_databases
@parametrized
def test_banking_changes_nothing_but_the_layout(path):
    """The same adventure split into banks must read back the same, and its
    resident part must be a good deal smaller."""
    ddb = load(path)
    flat, _, flat_texts = read_back(ddb)
    banked, reader, banked_texts = read_back(ddb, page_bits=14)
    assert banked_texts == flat_texts
    assert banked.resident_size < flat.resident_size
    assert len(banked.banks) >= 1
    # nothing that is needed at any moment may end up in a bank
    for index in (0, 1, 2, 3, 4, 6):
        assert reader.directory[index][0] == 0xFF


def test_accents_cost_no_more_than_letters():
    """The reason for giving up the original format: an accented character is
    just another character, with no special case anywhere.

    And since the character set is fixed, it costs the compressor nothing at
    all: the same 128 pairs whatever the adventure is written in, which is
    what stops one language being a handicap against another.
    """
    plain = ["El senor esta aqui", "La cabina esta rota", "Un senor mas"]
    accented = ["El señor está aquí", "La cabina está rota", "Un señor más"]
    store = TextStore(accented)
    for index, original in enumerate(accented):
        assert store.read(index) == original
    assert store.charset.spare == TextStore(plain).charset.spare
    assert len(store.messages) == len(TextStore(plain).messages)


if __name__ == "__main__":
    # Runnable without pytest so the round trip can be checked anywhere.
    failures = 0
    for path in DATABASES:
        name = os.path.basename(path)
        for check in (test_database_round_trip, test_condition_blocks_round_trip,
                      test_every_picture_draws, test_text_survives_packing,
                      test_text_packs_to_about_half,
                      test_binary_database_round_trips,
                      test_banking_changes_nothing_but_the_layout):
            try:
                check(path)
            except AssertionError:
                failures += 1
                print(f"FAIL {name} {check.__name__}")
    for check in (
        test_left_to_right_evaluation,
        test_prefix_operand_is_not_greedy,
        test_dangling_value_is_preserved,
        test_the_origin_is_at_the_bottom,
        test_a_fill_stays_inside_the_lines,
        test_a_fill_covers_the_same_ground_on_every_machine,
        test_every_machine_draws_the_same_picture,
        test_accents_cost_no_more_than_letters,
    ):
        try:
            check()
        except AssertionError:
            failures += 1
            print(f"FAIL {check.__name__}")
    total = len(DATABASES) * 7 + 8
    print(f"{total - failures}/{total} checks passed")
    sys.exit(1 if failures else 0)
