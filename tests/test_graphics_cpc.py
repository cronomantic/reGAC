"""Drawing on an Amstrad, compared against the reference renderer.

The same trade as the Spectrum's: every primitive is drawn twice, once by the
reference the project is built against and once by our own Z80 code running on
a real machine, and the two screens are compared.  Here they are compared as
pen numbers rather than as bytes, which says the same thing without caring
what colours the pens happen to hold.

There is no snapshot to load.  The build is a plain block of bytes, the test
writes it into a running Amstrad and points the processor at the front of it,
which is what a disk loader would have done.  It goes in above $4000 because
the lower ROM covers everything under that until the code turns it off.

What the reference does here was measured on the machine itself, and is
written up in doc/graficos.md.
"""

import os
import sys
import time

try:
    import pytest
except ImportError:
    pytest = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import emulator  # noqa: E402
from regac.binary import Database  # noqa: E402
from regac.devices import CPC_HARDWARE_PALETTE, AmstradDevice  # noqa: E402
from regac.gfx import Renderer  # noqa: E402

CPC = os.path.join(ROOT, "z80", "cpc")
SOURCE = os.path.join(CPC, "test_picture.asm")
DATABASE = os.path.join(CPC, "picture.rgac")
BINARY = os.path.join(CPC, "picture.bin")
LISTING = os.path.join(CPC, "picture.lst")

LOADS_AT = 0x4000
SCREEN = 0xC000
PICTURE_LEFT = 32  # where the picture sits on a screen of 320
PICTURE_ROWS = 128
INKS = [0, 24, 20, 6]  # what the runtime starts with

if pytest is not None:
    needs_tools = pytest.mark.skipif(
        not emulator.available(), reason="sjasmplus and ZEsarUX must be in tools/"
    )
    drawings = pytest.mark.parametrize(
        "name,commands",
        [
            ("a line across", [["LINE", 10, 100, 60, 100]]),
            ("a line down", [["LINE", 10, 60, 10, 120]]),
            ("a line at an angle", [["LINE", 10, 60, 60, 120]]),
            ("a line the other way", [["LINE", 60, 120, 10, 60]]),
            ("a rectangle", [["RECT", 20, 60, 100, 120]]),
            ("a single point", [["PLOT", 40, 100]]),
            ("a small ellipse", [["ELLIPSE", 60, 100, 70, 110]]),
            ("a larger ellipse", [["ELLIPSE", 128, 100, 168, 130]]),
            ("a fill", [["RECT", 20, 60, 100, 120], ["PENS", 2, 2], ["FILL", 60, 90]]),
            (
                "a fill of two pens",
                [["RECT", 20, 60, 100, 120], ["PENS", 1, 3], ["FILL", 60, 90]],
            ),
            ("one picture calling another", [["INK", 2], ["CALL", 2]]),
        ],
    )
else:

    def needs_tools(func):
        return func

    def drawings(func):
        return func


def adventure(commands):
    """The smallest adventure that can hold one picture."""
    return {
        "font": [0] * 1024,
        "verbs": {"N": 1},
        "nouns": {},
        "adverbs": {},
        "pronouns": [],
        "messages": {"1": "x"},
        "objects": {"1": {"weight": 1, "initial_loc": 1, "name": "x"}},
        "locations": {"1": {"graphic_id": 1, "exits": [], "desc": "x"}},
        "hpcs": [],
        "lpcs": [],
        "lcs": {},
        "model": "CPC",
        "punctuation": list("\0 .,-!?:"),
        "separators": [],
        "init_loc": 1,
        "no_objs_msg": "x",
        "gfx": {"1": commands, "2": [["PLOT", 10, 100]]},
    }


def pens_of(screen):
    """The screen as a pen for every pixel.  A byte holds four of them and the
    two bits of one are not next to each other: pixel n takes bit 7-n and bit
    3-n."""
    out = []
    for line in range(200):
        at = (line & 7) * 2048 + (line >> 3) * 80
        row = []
        for column in range(80):
            byte = screen[at + column]
            for pixel in range(4):
                row.append(
                    ((byte >> (7 - pixel)) & 1) | (((byte >> (3 - pixel)) & 1) << 1)
                )
        out.append(row)
    return out


def draw_on_both(commands):
    ddb = adventure(commands)
    with open(DATABASE, "wb") as f:
        f.write(Database(ddb).build())
    listing = emulator.assemble(SOURCE, listing=LISTING)
    done = emulator.label_address(listing, "done_flag")
    with open(BINARY, "rb") as f:
        blob = f.read()

    session = emulator.Session(machine="CPC6128")
    try:
        time.sleep(3.0)  # let the machine finish coming up
        for at in range(0, len(blob), 512):
            piece = blob[at:at + 512]
            session.command(
                f"write-memory-raw {LOADS_AT + at} " + piece.hex().upper()
            )
        session.command(f"set-register PC={LOADS_AT:04X}H")
        finished = session.wait_for(done, 0xFF, timeout=40.0, every=0.1)
        screen = session.read(SCREEN, 0x4000)
    finally:
        session.close()

    drawn = pens_of(screen)
    theirs = [
        [drawn[row][PICTURE_LEFT + x] for x in range(256)] for row in range(PICTURE_ROWS)
    ]
    device = AmstradDevice([CPC_HARDWARE_PALETTE[ink] for ink in INKS])
    Renderer(ddb["gfx"], device).run(1)
    ours = [
        [device.pens[row * 256 + x] for x in range(256)] for row in range(PICTURE_ROWS)
    ]
    return finished, theirs, ours


@needs_tools
@drawings
def test_the_amstrad_draws_what_the_reference_draws(name, commands):
    finished, theirs, ours = draw_on_both(commands)
    assert finished, f"{name}: the Amstrad never finished drawing"
    wrong = [
        (row, x)
        for row in range(PICTURE_ROWS)
        for x in range(256)
        if theirs[row][x] != ours[row][x]
    ]
    assert not wrong, f"{name}: {len(wrong)} points differ, first at {wrong[0]}"


if __name__ == "__main__":
    for case in (
        ("a line across", [["LINE", 10, 100, 60, 100]]),
        ("a rectangle", [["RECT", 20, 60, 100, 120]]),
        ("a fill of two pens",
         [["RECT", 20, 60, 100, 120], ["PENS", 1, 3], ["FILL", 60, 90]]),
    ):
        test_the_amstrad_draws_what_the_reference_draws(*case)
        print(f"{case[0]}: matches the reference")
