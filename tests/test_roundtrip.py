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
    """The whole point of the device split: a picture must come out the same
    on a machine that stores colour per pixel as on the original."""
    gfx = {1: [["RECT", 64, 100, 120, 60], ["PAPER", 2], ["BGFILL", 80, 80],
               ["SHADE", 80, 80]]}
    spectrum = Renderer(gfx, make("spectrum"))
    spectrum.run(1)
    sam = Renderer(gfx, make("sam"))
    sam.run(1)
    assert spectrum.fill_coverage == sam.fill_coverage


def test_a_fill_stays_inside_the_lines():
    gfx = {1: [["RECT", 64, 100, 120, 60], ["PAPER", 2], ["BGFILL", 80, 80]]}
    picture = Renderer(gfx).run(1)

    def paper_at(x, y):
        return (picture.attrs[(y >> 3) * CHAR_WIDTH + (x >> 3)] >> 3) & 7

    assert paper_at(80, 95) == 2, "the inside of the box should be filled"
    assert paper_at(8, 8) == 7, "the fill should not escape the box"


if __name__ == "__main__":
    # Runnable without pytest so the round trip can be checked anywhere.
    failures = 0
    for path in DATABASES:
        name = os.path.basename(path)
        for check in (test_database_round_trip, test_condition_blocks_round_trip,
                      test_every_picture_draws):
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
    ):
        try:
            check()
        except AssertionError:
            failures += 1
            print(f"FAIL {check.__name__}")
    total = len(DATABASES) * 3 + 6
    print(f"{total - failures}/{total} checks passed")
    sys.exit(1 if failures else 0)
