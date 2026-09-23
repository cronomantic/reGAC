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
"""Every picture of every adventure, drawn on an Amstrad and timed.

The Spectrum has had this test for a long time and the MSX got one; the
Amstrad had none, and that is how a picture of MegaCorp came to take twenty
seven seconds without anybody noticing.  The machine that had never been
measured is the machine that was eleven times slower than it should be.

So this measures it and keeps it measured, the same round as the others: in
the Z80's own clock cycles turned into seconds of a real Amstrad, with every
picture compared against the reference renderer -- the Spectrum's rules,
as these adventures are drawn here -- a picture that is quick
and wrong is not quick.  It is slow, so it only runs when asked for it:

    REGAC_SLOW=1 pytest tests/test_all_pictures_cpc.py -s

What it asserts about time is not the four or five seconds the project wants
but what this machine does today, adventure by adventure -- which since these
are drawn with the Spectrum's rules is inside the four or five for all eight,
Bangkok2 on the edge.  That is on purpose:
the budget is a conversation and belongs in doc/pendiente.md, and what a test
is good for is catching the day something gets slower than it already was.
Every number below was measured; if one comes down, bring the ceiling with it.

The first time it ran it found three pictures of the hundred and ninety six
drawn wrong, all three of them an ink of eight or more that this machine was
not treating as "leave the colour alone": see doc/pendiente.md.
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

import emulator  # noqa: E402
from regac.devices import device_for  # noqa: E402
from regac.gfx import Renderer  # noqa: E402
from test_all_pictures import adventures  # noqa: E402
from test_graphics_cpc import PICTURE_LEFT, PICTURE_ROWS, pens_of  # noqa: E402

CPC = os.path.join(ROOT, "z80", "cpc")
SOURCE = os.path.join(CPC, "test_picture.asm")
DATABASE = os.path.join(CPC, "picture.rgac")
BINARY = os.path.join(CPC, "picture.bin")
LISTING = os.path.join(CPC, "picture.lst")

CPC_HZ = 4_000_000              # what a machine of this kind really runs at
LOADS_AT = 0x4000
SCREEN = 0xC000
SCREEN_BYTES = 0x4000

# What each adventure's worst picture costs today, rounded up to the second.
# Not a budget -- the budget is four or five and only three of these meet it --
# but a ratchet: the day one of them gets slower, this says so.
# Measured with the Spectrum's rules, which is how these adventures -- all
# eight off a Spectrum -- are drawn on this machine now: see doc/pendiente.md.
CEILING = {
    "Bangkok1": 4.0,            # the worst of its thirty two measured 3.2
    "Bangkok2": 6.0,            # 5.0, on the edge of the budget
    "megacorp1": 3.0,           # 2.8
    "megacorp2": 4.0,           # 3.5
    "quijote1": 3.0,            # 2.9, which was 16.8 with the Amstrad's rules
    "quijote2": 4.0,            # 3.6, which was 25.3
    "vajillas1": 5.0,           # 4.2
    "vajillas2": 4.0,           # 3.7
}

needs = (
    pytest.mark.skipif(
        not emulator.available() or not adventures()
        or not os.environ.get("REGAC_SLOW"),
        reason="set REGAC_SLOW=1, with the tools and the adventures in place",
    )
    if pytest is not None
    else (lambda f: f)
)


def draw_them_all(path):
    """Every picture of one adventure: its number, how many points differ from
    the reference, and what it cost in seconds of a real Amstrad."""
    subprocess.run(
        [sys.executable, "-m", "regac", "build", path, DATABASE, "-m", "cpc"],
        cwd=ROOT, check=True, capture_output=True,
    )
    listing = emulator.assemble(SOURCE, listing=LISTING)
    where = {name: emulator.label_address(listing, name)
             for name in ("redraw", "done_flag", "picture_wanted", "go_flag")}
    with open(BINARY, "rb") as f:
        blob = f.read()
    with open(path, encoding="utf-8") as f:
        ddb = json.load(f)
    gfx = ddb["gfx"]

    out = []
    session = emulator.Session(machine="CPC6128")
    try:
        time.sleep(emulator.longer(3.0))
        assert session.start_code(blob, LOADS_AT, where["done_flag"],
                                  timeout=20.0), "the Amstrad never got going"
        for key in sorted(gfx, key=int):
            number = int(key)
            session.command(f"write-memory {where['picture_wanted']} "
                            f"{number & 255} {number >> 8}")
            session.command(f"write-memory {where['done_flag']} 0")
            # Asked for with a byte and not by writing the program counter,
            # which can land in the middle of an instruction: see
            # z80/cpc/test_picture.asm.
            session.command("reset-tstates-partial")
            session.command(f"write-memory {where['go_flag']} 1")
            seconds = session.seconds_until(where["done_flag"], CPC_HZ)
            if seconds is None:
                out.append((number, None, None))
                continue
            drawn = pens_of(session.read(SCREEN, SCREEN_BYTES))
            theirs = [[drawn[row][PICTURE_LEFT + x] for x in range(256)]
                      for row in range(PICTURE_ROWS)]
            # these are adventures off a Spectrum, drawn with its rules
            device = device_for("cpc", gfx, number, ddb)
            Renderer(gfx, device).run(number)
            wrong = sum(1 for row in range(PICTURE_ROWS) for x in range(256)
                        if theirs[row][x] != device.colours[row * 256 + x])
            out.append((number, wrong, seconds))
    finally:
        session.close()
    return out


@needs
def test_every_picture_matches_and_does_not_get_slower():
    wrong, unfinished, slow = [], [], []
    for path in adventures():
        name = os.path.basename(path)[:-5]
        drawn = draw_them_all(path)
        slowest = max((s for _, _, s in drawn if s is not None), default=0.0)
        wrong += [f"{name} {n} ({m} points)" for n, m, _ in drawn if m]
        unfinished += [f"{name} {n}" for n, m, _ in drawn if m is None]
        allowed = CEILING.get(name)
        if allowed is not None and slowest > allowed:
            worst = max((s, n) for n, _, s in drawn if s is not None)
            slow.append(f"{name} {worst[1]} at {worst[0]:.1f}s, over {allowed}")
        print(f"{name:12} {sum(1 for _, m, _ in drawn if m == 0):3}/{len(drawn):3}"
              f" identicas, la mas lenta {slowest:.1f}s")

    assert not unfinished, "never finished: " + ", ".join(unfinished)
    assert not wrong, "differ from the reference: " + ", ".join(wrong)
    assert not slow, "slower than it was: " + ", ".join(slow)


if __name__ == "__main__":
    test_every_picture_matches_and_does_not_get_slower()
    print("every picture of every adventure comes out right on an Amstrad")
