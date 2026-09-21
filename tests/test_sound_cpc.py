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
effects, the same numbers, the same lengths.

What is listened to is the recording the emulator will write of everything it
plays, because a chip's output cannot be watched at a port the way a flipped
bit can.  Silence is a recording that never moves.

And it is built **twice**, because this is the one machine where what travels
is not all of a piece.  The table of effects and the player that walks a
pitch go in only when the build asked for them, with -DNOISES; the key click
goes in always, because GAC clicked at every key pressed and none of the
eight adventures of 1986 asks for a noise.  So the second build is the one
those eight get, and what it has to prove is that it still clicks.
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
CLICK = 200                     # what the build calls the key click

# How much a recording of silence moves is the machine's own business, so
# each test takes its own silence first and asks every noise to beat it: see
# test_sound_ay.py, where a number written down here was wrong for three
# machines out of three.

if pytest is not None:
    needs_tools = pytest.mark.skipif(
        not emulator.available(), reason="sjasmplus and ZEsarUX must be in tools/"
    )
else:

    def needs_tools(func):
        return func


NAMES = ("ready_flag", "done_flag", "which", "rounds", "how_many",
         "play_many", "beep_effects", "REPEATS")


def built(with_noises):
    """Assemble the build one way or the other, and say where it keeps what
    it is doing."""
    listing = emulator.assemble(SOURCE, listing=LISTING,
                                defines=("NOISES",) if with_noises else ())
    where = {}
    for name in NAMES:
        try:
            where[name] = emulator.label_address(listing, name)
        except KeyError:
            pass                # the table is not in a build with no noises
    with open(BINARY, "rb") as f:
        return f.read(), where


def table_of(blob, where, how_many):
    """The effects as the build carries them: pitch, waves and step."""
    at = where["beep_effects"] - LOADS_AT
    return [tuple(blob[at + n * 3:at + n * 3 + 3]) for n in range(how_many)]


def waves_of(effect):
    """How long that effect is, counted the way both engines count it: the
    sum of the pitches it goes through, each of which is one wait of that
    many turns round a sixteen cycle loop.  The pitch walks and stops at the
    ends rather than going round, exactly as the engines do."""
    pitch, waves, step = effect
    if step > 127:
        step -= 256
    total = 0
    for _ in range(waves):
        total += pitch or 1
        if step:
            walked = pitch + step
            pitch = 255 if walked > 255 else (1 if walked < 1 else walked)
    return total


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
    blob, where = built(with_noises=True)
    sound = str(tmp_path / "heard.raw")

    quiet, went_round, how_many = played(0, where, blob, sound)
    assert went_round, "it never came back from playing nothing"
    assert how_many, "the build has no effects at all"

    for effect in range(1, how_many + 1):
        shapes, went_round, _ = played(effect, where, blob, sound)
        assert shapes > quiet, (
            f"effect {effect} made no noise: {shapes} shapes against "
            f"{quiet} for silence"
        )
        assert went_round, (
            f"effect {effect} started and never finished: an effect has to "
            f"give the machine back"
        )

    shapes, _, _ = played(NOT_AN_EFFECT, where, blob, sound)
    assert shapes <= quiet, (
        f"an effect the build has not got made a noise: {shapes} shapes "
        f"against {quiet} for silence"
    )


@needs_tools
def test_it_clicks_in_a_build_that_asked_for_no_noises(tmp_path):
    """Which is the build the eight adventures of 1986 get.  GAC clicked at
    every key pressed -- read in its code, the one call to the ROM's beeper
    there is -- and on this machine the only thing that can click is the same
    chip an effect would come out of.  So the chip access travels in every
    build and the table does not."""
    blob, where = built(with_noises=False)
    sound = str(tmp_path / "heard.raw")

    quiet, went_round, how_many = played(0, where, blob, sound)
    assert went_round, "it never came back from playing nothing"
    assert how_many == 0, (
        f"a build that asked for no noises carries {how_many} of them"
    )

    shapes, went_round, _ = played(CLICK, where, blob, sound)
    assert shapes > quiet, (
        f"it did not click: {shapes} shapes against {quiet} for silence"
    )
    assert went_round, "the click started and never finished"


@needs_tools
def test_an_effect_lasts_as_long_as_the_table_says():
    """Which nothing asked before, and it was not true.

    The recording says that something sounded; it cannot say for how long.
    So every effect was played and came back and the tests were happy, while
    on this machine **the length in the table was being thrown away**: B
    holds how many waves an effect is, and the three writes that get the chip
    ready corrupt BC, so what was counted down was whatever the last of them
    left there -- the same number for all five, whatever the table said.

    Measured in the processor's own cycles.  What an effect costs is a wave's
    worth of getting at the chip, which is the same every time, plus sixteen
    cycles for every turn of the waiting loop, which is what the pitch
    counts.  Two unknowns, so two of the effects are used to solve for them
    -- the two whose shapes are least alike -- and **the rest have to fall in
    line**.  Measured both ways: with the fault, what a wave costs comes out
    **negative**, which is not a thing, and the others are out by seventy per
    cent; without it, all of them land inside three.
    """
    blob, where = built(with_noises=True)
    session = emulator.Session(machine="CPC6128")
    spent = []
    try:
        time.sleep(emulator.longer(3.0))
        assert session.start_code(blob, LOADS_AT, where["ready_flag"],
                                  timeout=10.0), "the build never started"
        how_many = session.read(where["how_many"], 1)[0]
        table = table_of(blob, where, how_many)
        for effect in range(1, how_many + 1):
            session.command(f"write-memory {where['which']} {effect}")
            session.command(f"write-memory {where['done_flag']} 0")
            session.command("reset-tstates-partial")
            session.jump(where["play_many"])
            assert session.wait_for(where["done_flag"], 0xFF, timeout=60.0,
                                    every=0.05), f"effect {effect} never ended"
            spent.append(int(session.command("get-tstates-partial")
                             .splitlines()[0].strip()))
    finally:
        session.close()

    assert how_many >= 3, "there is nothing to predict with fewer than three"
    waves = [one[1] for one in table]
    turns = [waves_of(one) for one in table]

    # The two least alike, by how many waves they spend per turn of the
    # waiting loop: solving from those two and not from any two keeps the
    # arithmetic away from the edge where both are nearly the same shape.
    order = sorted(range(how_many), key=lambda n: waves[n] / turns[n])
    a, b = order[0], order[-1]
    bottom = waves[a] * turns[b] - waves[b] * turns[a]
    assert bottom, "the two effects used to solve are the same shape"
    a_wave = (spent[a] * turns[b] - spent[b] * turns[a]) / bottom
    a_turn = (spent[a] - waves[a] * a_wave) / turns[a]
    assert a_wave > 0 and a_turn > 0, (
        f"a wave costs {a_wave:.0f} cycles and a turn of the wait {a_turn:.0f}"
        f", and neither can be less than nothing: the lengths in the table "
        f"are not the lengths being played.  {spent} cycles for {waves} waves"
    )
    for n in range(how_many):
        if n in (a, b):
            continue            # these two are what the two were solved from
        should = waves[n] * a_wave + turns[n] * a_turn
        assert abs(spent[n] - should) < 0.10 * should, (
            f"effect {n + 1} took {spent[n]} cycles where the table asks for "
            f"about {should:.0f}: {spent} against {waves} waves and {turns} "
            f"turns of the wait"
        )


if __name__ == "__main__":
    import pathlib
    import tempfile
    test_the_chip_makes_the_same_noises(pathlib.Path(tempfile.mkdtemp()))
    print("the chip makes the same noises")
    test_it_clicks_in_a_build_that_asked_for_no_noises(
        pathlib.Path(tempfile.mkdtemp()))
    print("it clicks in a build that asked for no noises")
    test_an_effect_lasts_as_long_as_the_table_says()
    print("an effect lasts as long as the table says")
