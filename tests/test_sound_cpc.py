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
"""The Amstrad's own noises, which come out of its sound chip.

This machine has no speaker of one bit, so what every other machine does by
flipping a port it does by asking the chip for a note -- the same table of
effects, the same numbers, the same lengths.  A build with music does not use
any of this: there the effects are the tracker's.

What is listened to is the recording the emulator will write of everything it
plays, because a chip's output cannot be watched at a port the way a flipped
bit can.  Silence is a recording that never moves.
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

CPC = os.path.join(ROOT, "z80", "cpc")
SOURCE = os.path.join(CPC, "test_sound.asm")
BINARY = os.path.join(CPC, "sound.bin")
LISTING = os.path.join(CPC, "sound.lst")
LOADS_AT = 0x4000

NOT_AN_EFFECT = 99
QUIET = 2                       # how many shapes a recording of nothing has

if pytest is not None:
    needs_tools = pytest.mark.skipif(
        not emulator.available(), reason="sjasmplus and ZEsarUX must be in tools/"
    )
else:

    def needs_tools(func):
        return func


def played(which, where, blob, sound, seconds=2.0):
    """Play that over and over, and say how much the recording moves and
    whether the machine came back from it."""
    if os.path.exists(sound):
        os.remove(sound)
    session = emulator.Session(machine="CPC6128", extra=["--aofile", sound])
    try:
        time.sleep(emulator.longer(3.0))
        assert session.start_code(blob, LOADS_AT, where["ready_flag"],
                                  timeout=10.0), "the build never started"
        session.command(f"write-memory {where['which']} {which}")
        time.sleep(0.5)
        was = session.read(where["rounds"], 2)
        time.sleep(seconds)
        now = session.read(where["rounds"], 2)
        many = session.read(where["how_many"], 1)[0]
    finally:
        session.close()
    with open(sound, "rb") as f:
        heard = f.read()
    went_round = (now[1] << 8 | now[0]) != (was[1] << 8 | was[0])
    return len(set(heard)), went_round, many


@needs_tools
def test_the_chip_makes_the_same_noises(tmp_path):
    listing = emulator.assemble(SOURCE, listing=LISTING)
    where = {name: emulator.label_address(listing, name)
             for name in ("ready_flag", "which", "rounds", "how_many")}
    with open(BINARY, "rb") as f:
        blob = f.read()
    sound = str(tmp_path / "heard.raw")

    shapes, went_round, how_many = played(0, where, blob, sound)
    assert shapes <= QUIET, f"it made a noise with nothing playing: {shapes}"
    assert went_round, "it never came back from playing nothing"
    assert how_many, "the build has no effects at all"

    for effect in range(1, how_many + 1):
        shapes, went_round, _ = played(effect, where, blob, sound)
        assert shapes > QUIET, f"effect {effect} made no noise: {shapes} shapes"
        assert went_round, (
            f"effect {effect} started and never finished: an effect has to "
            f"give the machine back"
        )

    shapes, _, _ = played(NOT_AN_EFFECT, where, blob, sound)
    assert shapes <= QUIET, (
        f"an effect the build has not got made a noise: {shapes}"
    )


if __name__ == "__main__":
    import pathlib
    import tempfile
    test_the_chip_makes_the_same_noises(pathlib.Path(tempfile.mkdtemp()))
    print("the chip makes the same noises")
