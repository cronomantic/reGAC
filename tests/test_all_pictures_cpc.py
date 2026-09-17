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
picture compared against the reference renderer -- a picture that is quick
and wrong is not quick.  It is slow, so it only runs when asked for it:

    REGAC_SLOW=1 pytest tests/test_all_pictures_cpc.py -s

What it asserts about time is not the four or five seconds the project wants
but what this machine does today, adventure by adventure.  That is on purpose:
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
from regac.devices import CPC_HARDWARE_PALETTE, AmstradDevice  # noqa: E402
from regac.gfx import Renderer  # noqa: E402
from test_all_pictures import adventures  # noqa: E402
from test_graphics_cpc import INKS, PICTURE_LEFT, PICTURE_ROWS, pens_of  # noqa: E402

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
CEILING = {
    "Bangkok1": 3.0,            # the worst of its thirty two measured 2.4
    "Bangkok2": 7.0,            # 6.1
    "megacorp1": 3.0,           # 2.3
    "megacorp2": 4.0,           # 2.9
    "quijote1": 18.0,           # 16.8
    "quijote2": 27.0,           # 25.3
    "vajillas1": 9.0,           # 7.8
    "vajillas2": 8.0,           # 6.9
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


def finished_after(session, flag, timeout=120.0):
    """Seconds of a real Amstrad from the counter being cleared to the flag
    going up, or None if it never does.

    The emulator's cycle counter is exact, but nothing stops it: a breakpoint
    on the loop the build parks in was set here for a long time on the belief
    that it froze the counter with the machine, and it does not -- outside the
    emulator's step mode a breakpoint fires and the machine carries on, and in
    step mode it runs hundreds of times slower.  So whatever passes between
    the picture finishing and the flag being looked at is counted too.  That
    was every half second, which added up to three tenths of a second to every
    picture and made different pictures come out at the same count to within
    ten cycles.  Looked at every hundredth of a second instead, what is added
    is about that and no more.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        if session.read(flag, 1)[0] == 0xFF:
            reply = session.command("get-tstates-partial")
            return int(reply.split("\n")[0].strip()) / CPC_HZ
        time.sleep(0.01)
    return None


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
        gfx = json.load(f)["gfx"]

    out = []
    session = emulator.Session(machine="CPC6128")
    try:
        time.sleep(3.0)
        for at in range(0, len(blob), 512):
            session.command(f"write-memory-raw {LOADS_AT + at} "
                            + blob[at:at + 512].hex().upper())
        # Asked three times over, for the same reason every picture is: a
        # program counter written into a processor that is running does not
        # always take, and one round in five or so never got off the ground.
        started = False
        for _ in range(3):
            session.command(f"set-register PC={LOADS_AT:04X}H")
            if session.wait_for(where["done_flag"], 0xFF, timeout=20.0,
                                every=0.1):
                started = True
                break
        assert started, "the Amstrad never got going"
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
            seconds = finished_after(session, where["done_flag"])
            if seconds is None:
                out.append((number, None, None))
                continue
            drawn = pens_of(session.read(SCREEN, SCREEN_BYTES))
            theirs = [[drawn[row][PICTURE_LEFT + x] for x in range(256)]
                      for row in range(PICTURE_ROWS)]
            device = AmstradDevice([CPC_HARDWARE_PALETTE[ink] for ink in INKS])
            Renderer(gfx, device).run(number)
            wrong = sum(1 for row in range(PICTURE_ROWS) for x in range(256)
                        if theirs[row][x] != device.pens[row * 256 + x])
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
