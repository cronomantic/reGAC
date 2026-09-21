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
"""The three fills, asked of GAC itself instead of worked out.

What `FILL`, `BGFILL` and `SHADE` lay down was read out of the original and
then believed; this is the other half, which is running it.  The original's
own code is still in every snapshot, and the three are three entries of the
same routine, one after another at $6364:

    6364  LD HL,0000      ; BGFILL: the pair that wipes
    6367  JR 6371
    6369  LD HL,FFAA      ; SHADE: the half tone
    636C  JR 6371
    636E  LD HL,00FF      ; FILL: solid
    6371  LD (6343),HL    ; the pair in force
    6374  ...             ; and on into the walk up and down the column

and the run itself, at $63A5, takes the low byte of the pair and exclusive ors
the high one into it on odd rows -- counting in the y of the commands, which is
in B.  So the difference between filling and filling with the background is one
sixteen bit constant and nothing else, and the half tone is $AA and $55 by
turns: a chequer of one pixel.

Which is what this checks, by doing it: a box is drawn into the machine's
screen, the seed and the return are set up so that the routine comes back to a
jump of its own, and what it left is compared with what the reference renderer
leaves for the same fill.

Only the pixels are compared.  Entering the routine directly steps over what
sets the colours up -- the original saves and restores the picture's 512
attributes around drawing -- so what lands in the attribute file here says
nothing.  The colours are covered by test_all_pictures, which compares whole
pictures, attributes and all.
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
from regac.devices import SpectrumDevice  # noqa: E402
from regac.gfx import INK, PAPER, SHADE, Renderer  # noqa: E402

SNAPSHOT = os.path.join(ROOT, "snapshots", "megacorp1.sna")

# A box with room inside it, and a seed in the middle of that room.
BOX = {1: [["RECT", 40, 60, 120, 130]]}
SEED = (80, 95)

# And the shapes where a fill is not obvious.  Each is the picture and the
# point the fill starts from; what is being asked of every one of them is not
# "is this right" -- there is no right -- but "does the original do what we
# do".  A wall is drawn side by side rather than with RECT so that a pixel can
# be left out of it.
LEFT, RIGHT, LOW, HIGH = 40, 120, 60, 130


def walls(gap_x, gap_y):
    """A box whose right wall has one pixel missing."""
    return [["LINE", LEFT, LOW, RIGHT, LOW],
            ["LINE", LEFT, HIGH, RIGHT, HIGH],
            ["LINE", LEFT, LOW, LEFT, HIGH],
            ["LINE", gap_x, LOW, gap_x, gap_y - 1],
            ["LINE", gap_x, gap_y + 1, gap_x, HIGH]]


AWKWARD = {
    # x=120 is a multiple of eight, so the hole is exactly where our own walk
    # steps from one byte to the next: the first place two fills disagree.
    "un hueco de un pixel en el borde de un byte":
        ({1: walls(120, 95)}, (80, 95)),
    # and the same hole with the wall inside a byte
    "un hueco de un pixel en mitad de un byte":
        ({1: walls(124, 95)}, (80, 95)),
    # A staircase for a wall.  A fill that steps sideways and up separately
    # cannot get through a diagonal; one that steps cornerwise can, and the
    # two look the same until somebody draws a slope.
    "una diagonal por pared":
        ({1: [["LINE", LEFT, LOW, RIGHT, LOW],
              ["LINE", LEFT, LOW, LEFT, HIGH],
              ["LINE", LEFT, HIGH, RIGHT, HIGH],
              ["LINE", RIGHT, HIGH, RIGHT - 60, LOW]]}, (60, 70)),
    # A corridor one pixel wide, which a fill either walks down or does not.
    "un pasillo de un pixel de ancho":
        ({1: [["LINE", LEFT, LOW, LEFT, HIGH],
              ["LINE", LEFT + 2, LOW, LEFT + 2, HIGH],
              ["LINE", LEFT, LOW, LEFT + 2, LOW],
              ["LINE", LEFT, HIGH, LEFT + 2, HIGH]]}, (LEFT + 1, 95)),
    # The seed standing on the wall itself, which is a question neither of the
    # two was ever asked.  Both answer it the same way: by doing nothing at
    # all, because a fill stops on a lit pixel and it is already standing on
    # one.
    "la semilla encima de la pared":
        ({1: [["RECT", LEFT, LOW, RIGHT, HIGH]]}, (LEFT, 95)),
    # And one that reaches the frame, where the fill has to stop because the
    # picture does and not because anything was drawn.
    "una caja abierta contra el marco":
        ({1: [["LINE", LEFT, LOW, LEFT, 175],
              ["LINE", RIGHT, LOW, RIGHT, 175],
              ["LINE", LEFT, LOW, RIGHT, LOW]]}, (80, 100)),
}

# Where the original keeps things, all read out of the code around $6364.
SEED_AT = 0x6341  # the x and the y it fills from
ENTRY = {PAPER: 0x6364, SHADE: 0x6369, INK: 0x636E}
STOP_AT = 0x5B00  # the printer buffer: nothing in a GAC adventure uses it
STACK_AT = 0x5AF0

SCREEN = 0x4000
SCREEN_BYTES = 6144
ATTRIBUTES = 0x5800
ATTR_P = 0x5C8D  # the ROM's permanent colours, and its temporary ones
ATTR_T = 0x5C8F
PAPER_ON_BLACK = 0x38  # black on white, which is what a picture starts in

if pytest is not None:
    needs_tools = pytest.mark.skipif(
        not emulator.available() or not os.path.exists(SNAPSHOT),
        reason="ZEsarUX must be in tools/, with an adventure's snapshot",
    )
    each_fill = pytest.mark.parametrize("mode", [INK, PAPER, SHADE])
else:

    def needs_tools(func):
        return func

    def each_fill(func):
        return func


def screen_address(row, column):
    return ((row & 0xC0) << 5) + ((row & 7) << 8) + ((row & 0x38) << 2) + column


def to_screen(linear):
    """Our own bitmap, which is row by row, as the machine keeps it."""
    out = bytearray(SCREEN_BYTES)
    for row in range(192):
        for column in range(32):
            out[screen_address(row, column)] = linear[row * 32 + column]
    return bytes(out)


def to_linear(screen):
    out = bytearray(SCREEN_BYTES)
    for row in range(192):
        for column in range(32):
            out[row * 32 + column] = screen[screen_address(row, column)]
    return bytes(out)


def ours(mode, picture=None, seed=None):
    """The picture before the fill, and the bitmap after it."""
    device = SpectrumDevice()
    render = Renderer(picture or BOX, device)
    render.run(1)
    before = (bytes(device.pixels[:SCREEN_BYTES]), bytes(device.attrs[:768]))
    at = seed or SEED
    render.flood(at[0], at[1], mode)
    return before, bytes(device.pixels[:SCREEN_BYTES])


def theirs(session, before, mode, seed=SEED):
    """The same box, filled by the original's own routine."""
    # All of it with the machine held.  The stack pointer used to be set
    # while the adventure ran, and now and then it returned through the two
    # bytes put there for the fill before the fill was ever started -- after
    # which the fill's own return found nothing and never came back.
    with session.held():
        bitmap = to_screen(before[0])
        for at in range(0, SCREEN_BYTES, 512):
            session.command(
                f"write-memory-raw {SCREEN + at} " + bitmap[at:at + 512].hex().upper()
            )
        # The colours are not what is being looked at, but the routine is given a
        # sane world to work in: the attributes the box was drawn with, and the
        # ROM's own idea of what to print in.
        for at in range(0, 768, 256):
            session.command(
                f"write-memory-raw {ATTRIBUTES + at} " + before[1][at:at + 256].hex().upper()
            )
        session.command(f"write-memory {ATTR_P} {PAPER_ON_BLACK} {PAPER_ON_BLACK}")
        session.command(f"write-memory {ATTR_T} {PAPER_ON_BLACK} 0 0")
        session.command(f"write-memory {SEED_AT} {seed[0]} {seed[1]}")
        # A jump to itself for it to come back to, and a stack that points at it.
        session.command(f"write-memory-raw {STOP_AT} 18FE")
        session.command(f"write-memory {STACK_AT} {STOP_AT & 255} {STOP_AT >> 8}")
        session.command(f"set-register SP={STACK_AT:04X}H")
        session.command(f"set-register PC={ENTRY[mode]:04X}H")
    for _ in range(40):
        time.sleep(0.2)
        if session.pc() == STOP_AT:
            break
    else:
        raise AssertionError(f"the original never came back from its {mode} fill")
    return to_linear(bytes(session.read(SCREEN, SCREEN_BYTES)))


@needs_tools
@each_fill
def test_the_original_lays_down_what_we_lay_down(mode):
    session = emulator.Session()
    try:
        session.load(SNAPSHOT)
        time.sleep(emulator.longer(2.0))
        before, wanted = ours(mode)
        got = theirs(session, before, mode)
    finally:
        session.close()
    started = before[0]
    wrong = [n for n in range(SCREEN_BYTES) if wanted[n] != got[n]]
    assert not wrong, (
        f"{mode}: {len(wrong)} bytes differ, the first at row {wrong[0] // 32} "
        f"column {wrong[0] % 32}: ours ${wanted[wrong[0]]:02X}, "
        f"theirs ${got[wrong[0]]:02X}"
    )
    if mode is not PAPER:
        # And it really did something, or two blank boxes would agree.
        assert wanted != started, f"{mode} changed nothing at all"


# The one that is meant to lay nothing, so that "it changed nothing" is a
# failure everywhere else.
LAYS_NOTHING = {"la semilla encima de la pared"}

if pytest is not None:
    each_shape = pytest.mark.parametrize(
        "name,picture,seed",
        [(name, picture, seed) for name, (picture, seed) in AWKWARD.items()])
else:

    def each_shape(func):
        return func


@needs_tools
@each_shape
def test_the_awkward_shapes_fill_the_same(name, picture, seed):
    """Where a fill is not obvious, asked of the original rather than argued.

    A box proves the easy half.  These are the shapes where two flood fills
    written from the same description come apart: a wall with a pixel missing,
    with the hole on a byte boundary and inside one; a staircase, which a fill
    that steps cornerwise gets through and one that does not cannot; a
    corridor one pixel wide; a seed standing on the wall; and a shape that
    reaches the frame, where the fill stops because the picture ends.

    Only the solid fill is asked, because what the three differ in is a
    sixteen bit constant and that is proved above.
    """
    session = emulator.Session()
    try:
        session.load(SNAPSHOT)
        time.sleep(emulator.longer(2.0))
        before, wanted = ours(INK, picture, seed)
        got = theirs(session, before, INK, seed)
    finally:
        session.close()
    wrong = [n for n in range(SCREEN_BYTES) if wanted[n] != got[n]]
    assert not wrong, (
        f"{name}: {len(wrong)} bytes differ, the first at row "
        f"{wrong[0] // 32} column {wrong[0] % 32}: ours "
        f"${wanted[wrong[0]]:02X}, theirs ${got[wrong[0]]:02X}"
    )
    if name not in LAYS_NOTHING:
        assert wanted != before[0], f"{name}: the fill changed nothing at all"


@needs_tools
def test_the_three_are_three_entries_of_one_routine():
    """What is read above, read again: the constants are where the code says
    they are, and each entry runs into the next."""
    session = emulator.Session()
    try:
        session.load(SNAPSHOT)
        time.sleep(emulator.longer(2.0))
        code = bytes(session.read(0x6364, 16))
    finally:
        session.close()
    # LD HL,nn / JR / LD HL,nn / JR / LD HL,nn / LD (6343),HL
    assert code[0] == 0x21 and code[1:3] == bytes((0x00, 0x00)), "BGFILL wipes"
    assert code[5] == 0x21 and code[6:8] == bytes((0xAA, 0xFF)), "SHADE is a chequer"
    assert code[10] == 0x21 and code[11:13] == bytes((0xFF, 0x00)), "FILL is solid"
    assert code[13] == 0x22, "and all three store the pair in the same place"


if __name__ == "__main__":
    for one in (INK, PAPER, SHADE):
        test_the_original_lays_down_what_we_lay_down(one)
        print(f"{one}: the original lays down what we lay down")
