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
# What a noise may come out of, as the fourth byte of its four says it.
TONE, NOISE, BOTH = 0, 1, 2
# What tells the wave of a noise from the stretches between one go of it and
# the next, in samples of the recording: a note's runs are under ten, and the
# shortest stretch of nothing measured is 144.  See runs_of_the_wave.
SHORT = 64

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
             for name in ("ready_flag", "which", "rounds", "how_many",
                          "beep_effects")}
    with open(os.path.join(where_it_is, "ay.bin"), "rb") as f:
        return f.read(), where


def played(which, where, blob, machine, sound, seconds=2.0, out_of=None):
    """Play that over and over, and give back the recording, with whether the
    machine came back from it.

    With `out_of`, the fourth byte of the **first** effect is written in the
    machine before it plays, so the same pitch, length and step can be heard
    as a note, as a hiss and as the two together.  Patching it there rather
    than building three tables keeps what is being compared honestly equal:
    only that one byte differs."""
    if os.path.exists(sound):
        os.remove(sound)
    session = emulator.Session(machine=machine, extra=["--aofile", sound])
    try:
        time.sleep(emulator.longer(3.0))
        assert session.start_code(blob, LOADS_AT, where["ready_flag"],
                                  timeout=10.0), "the build never started"
        if out_of is not None:
            session.command(f"write-memory {where['beep_effects'] + 3} {out_of}")
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
    return heard, went_round


def shapes(heard):
    """How many different values a recording has, which is what silence is
    measured by."""
    return len(set(heard))


def runs(heard):
    """How long each stretch of one value lasts, in a row.

    This is what tells a note from a hiss.  A square wave is the same handful
    of lengths over and over -- a few more than one, because the pitch walks
    -- and a hiss is a scatter of them.  Counting the values themselves says
    nothing: both come out of the same four bit volume, and both measured
    four or five different ones.
    """
    lengths, so_far = [], 1
    for before, after in zip(heard, heard[1:]):
        if before == after:
            so_far += 1
        else:
            lengths.append(so_far)
            so_far = 1
    lengths.append(so_far)
    return lengths


def runs_of_the_wave(heard):
    """The different lengths of run a recording has, of the ones short enough
    to be the noise itself.

    The long ones are the stretches between one go of the effect and the
    next, and where the emulator stopped for a moment.  How long each comes
    out is the emulator's timing and not the chip's -- 156, 158, 160... 312,
    468, a different handful every time -- so counting them made a plain note
    measure anything from 19 to 29, and the test failed whenever the note
    measured high.  Without them a note is 8 to 10, always."""
    return len({length for length in runs(heard) if length < SHORT})


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

    heard, went_round = played(0, where, blob, machine, sound)
    quiet = shapes(heard)
    assert went_round, "it never came back from playing nothing"

    how_many = effects_in(folder)
    assert how_many, "the build has no effects at all"
    for effect in range(1, how_many + 1):
        heard, went_round = played(effect, where, blob, machine, sound)
        many = shapes(heard)
        assert many > quiet, (
            f"effect {effect} made no noise: {many} shapes against "
            f"{quiet} for silence"
        )
        assert went_round, (
            f"effect {effect} started and never finished: an effect has to "
            f"give the machine back"
        )

    heard, _ = played(NOT_AN_EFFECT, where, blob, machine, sound)
    assert shapes(heard) <= quiet, (
        f"an effect the build has not got made a noise: {shapes(heard)} "
        f"shapes against {quiet} for silence"
    )


@needs_tools
@every_machine
def test_the_key_click_comes_out_of_the_chip_too(folder, machine, tmp_path):
    """GAC clicked at every key pressed, and on these machines the click is
    the chip's now and not the speaker's."""
    blob, where = build(folder)
    sound = str(tmp_path / "heard.raw")
    heard, _ = played(0, where, blob, machine, sound)
    quiet = shapes(heard)
    heard, went_round = played(CLICK, where, blob, machine, sound)
    assert shapes(heard) > quiet, (
        f"the click made no noise: {shapes(heard)} shapes against {quiet} "
        f"for silence"
    )
    assert went_round, "the click started and never finished"


@needs_tools
@every_machine
def test_a_noise_is_a_hiss_and_not_a_note(folder, machine, tmp_path):
    """The fourth byte of a noise says what it comes out of -- the tone
    generator, the noise one, or both -- and this is where it is proved that
    the word reaches the chip.

    The same effect is played three ways, with only that byte changed in the
    machine, so nothing else can account for a difference.  What separates
    them is **how many different run lengths** the wave has: a note is a
    square wave, the same handful of lengths over and over, and a hiss is a
    scatter.  Counting the values instead says nothing at all -- both come
    out of the same four bit volume, and both measure four or five.

    **It took three failures to get here.**  The first two were counting how
    often the value changes, which swings by two thirds for a hiss and
    overlaps the note.  The third was counting every run length, the long
    ones too: those are the gaps between one go and the next, and their
    lengths are the emulator's timing, so the note itself measured from 19 to
    29 and the test fell whenever it measured high -- at 1.15 times the note,
    with three other emulators running.  Only the runs of the wave count now,
    the ones under SHORT.  Six goes of each, alone and with three emulators
    beside it:

                 note      noise     both
        Spectrum 8 - 10    24 - 34   19 - 23
        MSX      8         28 - 32   19 - 29
        Next     8 - 9     28 - 34   18 - 24

    Asked as a ratio against the note measured in the same run.  The
    thinnest margin seen is `both` at 1.9 times the note, and `noise` has
    never come in under 2.67; with the engine deaf to the fourth byte all
    three would measure like the note, at most 10 against 8, 1.25.  So 1.5,
    between the two.

    Forcing the pitch to stand still does not sharpen any of this, and it was
    tried: the spread is the recording being resampled, not the note
    sweeping.
    """
    blob, where = build(folder)
    sound = str(tmp_path / "heard.raw")
    told = {}
    for out_of, name in ((TONE, "tone"), (NOISE, "noise"), (BOTH, "both")):
        heard, went_round = played(1, where, blob, machine, sound,
                                   out_of=out_of)
        assert went_round, f"it never came back from playing {name}"
        told[name] = runs_of_the_wave(heard)

    for name in ("noise", "both"):
        assert told[name] > 1.5 * told["tone"], (
            f"{name} came out shaped like a note: {told[name]} different "
            f"run lengths in its wave against {told['tone']} for the note "
            f"itself, and anything the noise generator touches is nearly "
            f"twice as scattered"
        )


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
