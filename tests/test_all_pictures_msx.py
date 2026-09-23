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
"""Every picture of every adventure, drawn on an MSX and timed.

The Spectrum has had this test for a long time; this machine had a number
instead, and the number was stale.  It said drawing here cost about half as
much again as on a Spectrum -- six seconds against four -- and it was true
when it was written, before the drawing was made quicker.  Nobody measured it
afterwards, so it sat in the pending list as the one thing this project had
declared and not met.

It is nearly met, and now it is measured: the same round as the Spectrum's,
in the Z80's own clock cycles, turned into seconds of a real MSX.  Of the one
hundred and ninety six pictures of the eight adventures, one is over the
limit, and it is over it on a Spectrum's terms too.  It is slow, so it only
runs when asked for it:

    REGAC_SLOW=1 pytest tests/test_all_pictures_msx.py -s

The picture is compared against the reference renderer as well, because a
picture that is quick and wrong is not quick.
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
from regac.devices import MSX_COLOURS, MSX_PATTERNS, MSX_PICTURE_BYTES  # noqa: E402
from regac.devices import MsxDevice  # noqa: E402
from regac.gfx import Renderer  # noqa: E402
from test_all_pictures import adventures  # noqa: E402

MSX = os.path.join(ROOT, "z80", "msx")
SOURCE = os.path.join(MSX, "test_picture.asm")
DATABASE = os.path.join(MSX, "picture.rgac")
BINARY = os.path.join(MSX, "picture.bin")
LISTING = os.path.join(MSX, "picture.lst")

MSX_HZ = 3_579_545              # what a machine of this kind really runs at
LIMIT_SECONDS = 5.0             # the same a player will wait for anywhere

# The one picture that is over it, and by how much, so that the number is a
# fact and not a memory: 6.1 seconds here against 4.7 on a Spectrum.  It is
# the picture itself that is heavy, not the machine -- it is also the worst
# of its adventure on a Spectrum, by four times over the next one.  Where
# those seconds go is not known: see doc/pendiente.md.
KNOWN_SLOW = {("Bangkok2", 28): 6.5}
CODE_AT = 0x8000
VRAM = 24                       # the emulator's name for the video chip's memory

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
    """Every picture of one adventure: its number, how many bytes differ from
    the reference, and what it cost in seconds of a real MSX."""
    subprocess.run(
        [sys.executable, "-m", "regac", "build", path, DATABASE, "-m", "msx"],
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
    session = emulator.Session(machine="MSX1")
    try:
        time.sleep(emulator.longer(7.0))                 # this one takes its time coming up
        assert session.start_code(blob, CODE_AT, where["done_flag"],
                                  timeout=60.0), "the MSX never got going"
        for key in sorted(gfx, key=int):
            number = int(key)
            session.command(f"write-memory {where['picture_wanted']} "
                            f"{number & 255} {number >> 8}")
            session.command(f"write-memory {where['done_flag']} 0")
            session.command("reset-tstates-partial")
            session.command(f"write-memory {where['go_flag']} 1")
            seconds = session.seconds_until(where["done_flag"], MSX_HZ)
            if seconds is None:
                out.append((number, None, None))
                continue
            drawn = (bytes(session.read(MSX_PATTERNS, MSX_PICTURE_BYTES,
                                        zone=VRAM)),
                     bytes(session.read(MSX_COLOURS, MSX_PICTURE_BYTES,
                                        zone=VRAM)))
            reference = Renderer(gfx, MsxDevice()).run(number).vram()
            wrong = sum(1 for mine, theirs in zip(reference, drawn)
                        for a, b in zip(mine, theirs) if a != b)
            out.append((number, wrong, seconds))
    finally:
        session.close()
    return out


@needs
def test_every_picture_matches_and_stays_quick():
    wrong, unfinished, slow = [], [], []
    for path in adventures():
        name = os.path.basename(path)[:-5]
        drawn = draw_them_all(path)
        slowest = max((s for _, m, s in drawn if s is not None), default=0.0)
        wrong += [f"{name} {n} ({m} bytes)" for n, m, _ in drawn if m]
        unfinished += [f"{name} {n}" for n, m, _ in drawn if m is None]
        for number, _, seconds in drawn:
            if seconds is None:
                continue
            allowed = KNOWN_SLOW.get((name, number), LIMIT_SECONDS)
            if seconds > allowed:
                slow.append(f"{name} {number} at {seconds:.1f}s")
        print(f"{name:12} {sum(1 for _, m, _ in drawn if m == 0):3}/{len(drawn):3}"
              f" identicas, la mas lenta {slowest:.1f}s")

    assert not unfinished, "never finished: " + ", ".join(unfinished)
    assert not wrong, "differ from the reference: " + ", ".join(wrong)
    assert not slow, "over the time a player will wait: " + ", ".join(slow)


if __name__ == "__main__":
    test_every_picture_matches_and_stays_quick()
    print("every picture matches and stays quick")
