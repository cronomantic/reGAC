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
"""The three opcodes that make a noise, written in the source and obeyed.

`MUSIC n` starts a tune of the build, `SOUND n` makes an effect of its bank
and `QUIET` stops the music.  They are written in a condition like anything
else, compiled by the project's own compiler and run on the machine, and what
is looked at afterwards is the player's own state: what is playing, which tune
it is, and whether the interrupt is still moving it on long after the
conditions have finished.

The last test is the one that matters most for a tool that builds the same
adventure for five machines: the very same conditions are run on a build with
no music in it at all, where the three opcodes must read their argument, do
nothing, and let the rest of the line carry on.  An adventure has one shape
whatever it is played on.

The tune and the effects are somebody's music and are not this project's to
carry, so this asks for them in music/ and steps aside when they are not
there.
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
from test_conditions_z80 import DATABASE, SOURCE, adventure  # noqa: E402
from test_conditions_z80 import run as run_without_music  # noqa: E402
from test_music_z80 import TUNE, word  # noqa: E402

SPECTRUM = os.path.join(ROOT, "z80", "spectrum")
SNAPSHOT = os.path.join(SPECTRUM, "conditions_music.sna")
LISTING = os.path.join(SPECTRUM, "conditions_music.lst")
EFFECTS = os.path.join(ROOT, "music", "effects.asm")

CHANNEL = 2                     # the one music.asm lays effects on
CHANNEL_BYTES = 8

WATCHED = ("done_flag", "music_playing", "music_tune", "tune", "effects",
           "last", "vm_music", "PLY_AKM_Track1_PtTrack",
           "PLY_AKM_Channel1_SoundEffectData")

if pytest is not None:
    needs_tools = pytest.mark.skipif(
        not emulator.available()
        or not os.path.exists(TUNE)
        or not os.path.exists(EFFECTS),
        reason="sjasmplus and ZEsarUX must be in tools/, with a tune and a bank"
               " of effects in music/",
    )
else:

    def needs_tools(func):
        return func


class Watch:
    """A build of the conditions with music in it, run and then watched."""

    def __init__(self, session, where):
        self.session = session
        self.where = where

    def playing(self):
        return self.session.read(self.where["music_playing"], 1)[0]

    def tune(self):
        return self.session.read(self.where["music_tune"], 1)[0]

    def reading(self):
        """Where in memory the player has got to, or None before it has run."""
        at = word(self.session, self.where["PLY_AKM_Track1_PtTrack"])
        return at or None

    def in_the_tune(self):
        at = self.reading()
        return at is not None and self.where["tune"] <= at < self.where["last"]

    def effect(self, channel=CHANNEL):
        return word(self.session,
                    self.where["PLY_AKM_Channel1_SoundEffectData"]
                    + channel * CHANNEL_BYTES)


def run(conditions):
    """Build those conditions into an adventure, play it on a 128 with the
    music in, and hand back the running machine to be looked at."""
    with open(DATABASE, "wb") as f:
        f.write(Database(adventure(conditions)).build())
    listing = emulator.assemble(SOURCE, listing=LISTING, defines=("WITH_MUSIC",))
    where = {name: emulator.label_address(listing, name) for name in WATCHED}

    session = emulator.Session(machine="128k")
    try:
        session.load(SNAPSHOT)
        assert session.wait_for(where["done_flag"], 0xFF, timeout=20.0,
                                every=0.05), "the conditions never finished"
    except Exception:
        session.close()
        raise
    return Watch(session, where)


@needs_tools
def test_music_starts_a_tune_and_the_interrupt_keeps_it_going():
    watch = run(["MUSIC 0 END"])
    try:
        time.sleep(0.3)
        assert watch.playing() == 1, "MUSIC did not start anything"
        assert watch.tune() == 0
        assert watch.in_the_tune(), (
            f"the player is not reading the tune: {watch.reading()}"
        )
        # The conditions are long over; only the interrupt is left to move it.
        was = watch.reading()
        deadline = time.time() + 5.0
        while time.time() < deadline and watch.reading() == was:
            time.sleep(0.2)
        assert watch.reading() != was, (
            "the tune stopped once the conditions had finished"
        )
    finally:
        watch.session.close()


@needs_tools
def test_quiet_stops_it():
    watch = run(["MUSIC 0 QUIET END"])
    try:
        time.sleep(0.3)
        assert watch.playing() == 0, "QUIET left it playing"
        assert watch.tune() == 0xFF, "and left it thinking a tune was on"
    finally:
        watch.session.close()


@needs_tools
def test_sound_lays_an_effect_over_the_tune():
    watch = run(["MUSIC 0 SOUND 2 END"])
    try:
        time.sleep(0.3)
        at = watch.effect()
        assert watch.where["effects"] <= at < watch.where["last"], (
            f"SOUND did not start an effect of the bank: ${at:04X}"
        )
        assert watch.playing() == 1 and watch.in_the_tune(), (
            "the effect stopped the tune"
        )
    finally:
        watch.session.close()


@needs_tools
def test_a_tune_the_build_has_not_got_is_let_alone():
    watch = run(["MUSIC 9 END"])
    try:
        time.sleep(0.3)
        assert watch.playing() == 0, (
            "it played something for a tune that is not in the build"
        )
    finally:
        watch.session.close()


@needs_tools
def test_a_saved_game_remembers_what_was_playing():
    """What music was on is part of a game and not of the machine, so SAVE
    writes it out with the flags and the counters.

    Only the writing can be watched here: the emulator plays tapes and does
    not record them, so there is no reading a game back on this machine --
    which is why what LOAD does with the byte is three instructions and a
    routine of four, and why they are kept that small.
    """
    watch = run(["MUSIC 0 SAVE END"])
    try:
        time.sleep(0.3)
        assert watch.session.read(watch.where["vm_music"], 1)[0] == 1, (
            "a game saved while the first tune played should say so: what is"
            " written is the tune and one, so that nought can mean silence"
        )
        assert watch.playing() == 1, (
            "the music was hushed for the tape and never came back"
        )
    finally:
        watch.session.close()

    watch = run(["MUSIC 0 QUIET SAVE END"])
    try:
        time.sleep(0.3)
        assert watch.session.read(watch.where["vm_music"], 1)[0] == 0, (
            "a game saved in silence should say that too"
        )
        assert watch.playing() == 0, "and should still be silent afterwards"
    finally:
        watch.session.close()


@needs_tools
def test_a_machine_without_music_reads_them_and_carries_on():
    """The same conditions on a build with no sound chip and no player: the
    three opcodes must take their argument and get out of the way."""
    state = run_without_music([
        "MUSIC 0 SET 13 END",
        "SOUND 2 SET 14 END",
        "QUIET 7 CSET 5 END",
    ])
    assert state["flags"] == {13, 14}, (
        f"a line with a noise in it stopped where it should not: {state}"
    )
    assert state["counters"][5] == 7, "and the numbers after it went astray"


if __name__ == "__main__":
    test_music_starts_a_tune_and_the_interrupt_keeps_it_going()
    print("MUSIC starts a tune and the interrupt keeps it going")
    test_quiet_stops_it()
    print("QUIET stops it")
    test_sound_lays_an_effect_over_the_tune()
    print("SOUND lays an effect over the tune")
    test_a_tune_the_build_has_not_got_is_let_alone()
    print("a tune the build has not got is let alone")
    test_a_saved_game_remembers_what_was_playing()
    print("a saved game remembers what was playing")
    test_a_machine_without_music_reads_them_and_carries_on()
    print("a machine without music reads them and carries on")
