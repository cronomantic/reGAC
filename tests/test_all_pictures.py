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
"""Every picture of every adventure to hand, drawn on the Z80 and timed.

This is the acceptance test for the two things that matter about the drawing:
that the Spectrum puts down exactly what the reference renderer puts down, and
that the slowest picture stays inside the time a player will wait for it.

It is slow, a quarter of an hour, so it only runs when asked for it:

    REGAC_SLOW=1 pytest tests/test_all_pictures.py -s

The time is counted in the Z80's own clock cycles, read from the emulator, and
turned into seconds of a real Spectrum.  Measuring the wall clock instead
would measure the host: this emulator, on this machine, runs at about 2MHz,
which would make every picture look slower than it is.

Whatever the picture leaves running between finishing and the next look is
counted too, so the flag is looked at often.  Not too often: asking the
emulator anything stops it for a moment, and looking every few hundredths of a
second starves it enough that a picture never seems to end.
"""

import glob
import json
import os
import subprocess
import sys

try:
    import pytest
except ImportError:
    pytest = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import emulator  # noqa: E402
from regac.devices import SpectrumDevice  # noqa: E402
from regac.gfx import Renderer  # noqa: E402

SPECTRUM = os.path.join(ROOT, "z80", "spectrum")
ADVENTURES = os.path.join(ROOT, "snapshots")
SPECTRUM_HZ = 3_500_000
LIMIT_SECONDS = 5.0
PICTURE_ROWS = 128
BYTES_ACROSS = 32


def screen_address(row, column):
    return ((row & 0xC0) << 5) + ((row & 7) << 8) + ((row & 0x38) << 2) + column


def adventures():
    return sorted(glob.glob(os.path.join(ADVENTURES, "*.json")))


def draw_them_all(path):
    """Every picture of one adventure: its name, what differs, and what it cost
    in seconds of a real Spectrum."""
    subprocess.run(
        [sys.executable, "-m", "regac", "build", path,
         os.path.join(SPECTRUM, "picture.rgac"), "-m", "spectrum48"],
        cwd=ROOT, check=True, capture_output=True,
    )
    listing = emulator.assemble(
        os.path.join(SPECTRUM, "test_picture.asm"),
        listing=os.path.join(SPECTRUM, "picture.lst"),
    )
    where = {name: emulator.label_address(listing, name)
             for name in ("redraw", "done_flag", "picture_wanted", "go_flag")}
    gfx = json.load(open(path, encoding="utf-8"))["gfx"]

    out = []
    session = emulator.Session()
    try:
        session.load(os.path.join(SPECTRUM, "picture.sna"))
        # the snapshot draws one picture of its own accord; waiting for that
        # is how we know it has really loaded and run
        assert session.wait_for(where["done_flag"], 0xFF, timeout=60.0),             "the Spectrum never got going"
        for key in sorted(gfx, key=int):
            number = int(key)
            session.command(
                f"write-memory {where['picture_wanted']} {number & 255} {number >> 8}")
            session.command(f"write-memory {where['done_flag']} 0")
            session.command("reset-tstates-partial")
            session.command(f"write-memory {where['go_flag']} 1")
            seconds = session.seconds_until(where["done_flag"], SPECTRUM_HZ)
            if seconds is None:
                out.append((number, None, None))
                continue
            bitmap = session.read(0x4000, 6144)
            attributes = session.read(0x5800, 512)
            reference = Renderer(gfx, SpectrumDevice()).run(number)
            wrong = sum(
                1
                for row in range(PICTURE_ROWS)
                for column in range(BYTES_ACROSS)
                if bitmap[screen_address(row, column)]
                != reference.pixels[row * BYTES_ACROSS + column]
            )
            wrong += sum(1 for n in range(512) if attributes[n] != reference.attrs[n])
            out.append((number, wrong, seconds))
    finally:
        session.close()
    return out


needs = (
    pytest.mark.skipif(
        not emulator.available() or not adventures() or not os.environ.get("REGAC_SLOW"),
        reason="set REGAC_SLOW=1, with the tools and the adventures in place",
    )
    if pytest is not None
    else (lambda f: f)
)


@needs
def test_every_picture_matches_and_stays_quick():
    worst, wrong, unfinished = 0.0, [], []
    for path in adventures():
        name = os.path.basename(path)[:-5]
        drawn = draw_them_all(path)
        slowest = max((s for _, m, s in drawn if s is not None), default=0.0)
        worst = max(worst, slowest)
        wrong += [f"{name} {n} ({m} bytes)" for n, m, _ in drawn if m]
        unfinished += [f"{name} {n}" for n, m, _ in drawn if m is None]
        print(f"{name:12} {sum(1 for _, m, _ in drawn if m == 0):3}/{len(drawn):3}"
              f" identicas, la mas lenta {slowest:.1f}s")

    assert not unfinished, "never finished: " + ", ".join(unfinished)
    assert not wrong, "differ from the reference: " + ", ".join(wrong)
    assert worst <= LIMIT_SECONDS, f"the slowest picture takes {worst:.1f}s"
