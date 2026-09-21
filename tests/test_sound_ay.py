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
"""The noises of the three machines that have a sound chip and a speaker both.

A Spectrum 128, a +3, an MSX and a Next can all flip a bit of a port fast
enough to be a note, and all four have an AY as well.  The chip is the better
instrument -- a cleaner note, and it leaves alone what shares the speaker's
port: the border on a Spectrum, the cassette motor and the caps lamp on an
MSX -- so where there is a chip the chip is what sounds.  Only a 48, which has
none, still flips the bit, and that is what test_beep_z80.py watches.

What is listened to is the recording the emulator will write of everything it
plays, because a chip's two ports are write only and there is nothing to watch
at them.  Silence is a recording that never moves.  It is the same oracle
test_sound_cpc.py uses, and it was proved against a Spectrum beeping before it
was trusted here.

Each machine is asked on its own and not taken on trust from the Spectrum's,
because the chip is not reached the same way twice and, on an MSX, register
seven is not even only the mixer: its top two bits say which way the chip's
own ports face, and those ports are the joysticks.  A build that got that
wrong would still make a noise.
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

LOADS_AT = 0x8000
CLICK = 200                     # what the build calls the key click
NOT_AN_EFFECT = 99

# How much a recording of silence moves is the machine's own business and not
# a number to be guessed: measured, it is three shapes on a Spectrum and a
# Next and one on an MSX, against five and three with an effect playing.  So
# each test takes its own silence first and asks every noise to beat it.  A
# threshold written down here would be right for one machine and wrong for
# the next, which is how the Amstrad's two came to be wrong for these three.

# The three of them, and what the emulator calls each one.
MACHINES = [
    ("spectrum", "128k"),
    ("msx", "MSX1"),
    ("next", "TBBlue"),
]

if pytest is not None:
    needs_tools = pytest.mark.skipif(
        not emulator.available(), reason="sjasmplus and ZEsarUX must be in tools/"
    )
else:

    def needs_tools(func):
        return func


def build(folder):
    """Assemble that machine's noise build and say where it keeps what it is
    doing."""
    where_it_is = os.path.join(ROOT, "z80", folder)
    listing = emulator.assemble(os.path.join(where_it_is, "test_ay.asm"),
                                listing=os.path.join(where_it_is, "ay.lst"))
    where = {name: emulator.label_address(listing, name)
             for name in ("ready_flag", "which", "rounds", "how_many")}
    with open(os.path.join(where_it_is, "ay.bin"), "rb") as f:
        return f.read(), where


def played(which, where, blob, machine, sound, seconds=2.0):
    """Play that over and over, and say how much the recording moves and
    whether the machine came back from it."""
    if os.path.exists(sound):
        os.remove(sound)
    session = emulator.Session(machine=machine, extra=["--aofile", sound])
    try:
        time.sleep(emulator.longer(3.0))
        assert session.start_code(blob, LOADS_AT, where["ready_flag"],
                                  timeout=10.0), "the build never started"
        session.command(f"write-memory {where['which']} {which}")
        time.sleep(0.5)
        was = session.read(where["rounds"], 2)
        time.sleep(seconds)
        now = session.read(where["rounds"], 2)
    finally:
        session.close()
    with open(sound, "rb") as f:
        heard = f.read()
    went_round = (now[1] << 8 | now[0]) != (was[1] << 8 | was[0])
    return len(set(heard)), went_round


if pytest is not None:
    every_machine = pytest.mark.parametrize("folder,machine", MACHINES,
                                            ids=[f for f, _ in MACHINES])
else:

    def every_machine(func):
        return func


@needs_tools
@every_machine
def test_the_chip_makes_every_noise_of_the_table(folder, machine, tmp_path):
    blob, where = build(folder)
    sound = str(tmp_path / "heard.raw")

    quiet, went_round = played(0, where, blob, machine, sound)
    assert went_round, "it never came back from playing nothing"

    how_many = effects_in(folder)
    assert how_many, "the build has no effects at all"
    for effect in range(1, how_many + 1):
        shapes, went_round = played(effect, where, blob, machine, sound)
        assert shapes > quiet, (
            f"effect {effect} made no noise: {shapes} shapes against "
            f"{quiet} for silence"
        )
        assert went_round, (
            f"effect {effect} started and never finished: an effect has to "
            f"give the machine back"
        )

    shapes, _ = played(NOT_AN_EFFECT, where, blob, machine, sound)
    assert shapes <= quiet, (
        f"an effect the build has not got made a noise: {shapes} shapes "
        f"against {quiet} for silence"
    )


@needs_tools
@every_machine
def test_the_key_click_comes_out_of_the_chip_too(folder, machine, tmp_path):
    """GAC clicked at every key pressed, and on these machines the click is
    the chip's now and not the speaker's."""
    blob, where = build(folder)
    sound = str(tmp_path / "heard.raw")
    quiet, _ = played(0, where, blob, machine, sound)
    shapes, went_round = played(CLICK, where, blob, machine, sound)
    assert shapes > quiet, (
        f"the click made no noise: {shapes} shapes against {quiet} for silence"
    )
    assert went_round, "the click started and never finished"


def effects_in(folder):
    """How many effects that build has, which it writes down for us."""
    listing = os.path.join(ROOT, "z80", folder, "ay.lst")
    at = emulator.label_address(listing, "how_many")
    with open(os.path.join(ROOT, "z80", folder, "ay.bin"), "rb") as f:
        return f.read()[at - LOADS_AT]


if __name__ == "__main__":
    import pathlib
    import tempfile
    for folder, machine in MACHINES:
        test_the_chip_makes_every_noise_of_the_table(
            folder, machine, pathlib.Path(tempfile.mkdtemp()))
        print(f"{folder}: every noise of the table")
