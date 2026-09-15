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
"""A sound effect laid over the music, without either of them stopping.

An effect is a little instrument that the player lays over one of the three
channels the next time the interrupt calls it: asking for one writes five
bytes and returns, the tune goes on underneath with a channel missing, and
when the effect has run out that channel goes back to the tune.  All three of
those are what is looked at here, in the player's own state: the channel the
effect was put on is busy and moving, the other two are not, and it lets go by
itself.

It is done on a Spectrum and on no other machine because there is nothing
machine-dependent about it -- the same player does it from the same interrupt
everywhere, and the machines' own part of music is tested one machine at a
time in test_music_*.py.

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
from test_music_z80 import TUNE, word  # noqa: E402

SPECTRUM = os.path.join(ROOT, "z80", "spectrum")
SOURCE = os.path.join(SPECTRUM, "test_sound.asm")
SNAPSHOT = os.path.join(SPECTRUM, "sound.sna")
LISTING = os.path.join(SPECTRUM, "sound.lst")
EFFECTS = os.path.join(ROOT, "music", "effects.asm")

AN_EFFECT = 3                   # any of them; the bank starts at one
CHANNEL = 2                     # the one music.asm lays them on
CHANNEL_BYTES = 8               # what the player keeps for each

WATCHED = ("playing_flag", "spins", "effect_wanted",
           "PLY_AKM_Channel1_SoundEffectData", "PLY_AKM_Track1_PtTrack")

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


def effect_on(session, where, channel):
    """How far into its effect a channel is, or nothing at all."""
    return word(session,
                where["PLY_AKM_Channel1_SoundEffectData"]
                + channel * CHANNEL_BYTES)


@needs_tools
def test_an_effect_plays_over_the_tune_and_lets_go():
    listing = emulator.assemble(SOURCE, listing=LISTING)
    where = {name: emulator.label_address(listing, name) for name in WATCHED}

    session = emulator.Session(machine="128k")
    try:
        session.load(SNAPSHOT)
        time.sleep(1.0)
        assert session.read(where["playing_flag"], 1)[0] == 0xFF, (
            "the build never got past starting the tune"
        )
        assert not any(effect_on(session, where, c) for c in range(3)), (
            "something was playing an effect before anything asked for one"
        )

        was = word(session, where["PLY_AKM_Track1_PtTrack"])
        session.command(f"write-memory {where['effect_wanted']} {AN_EFFECT}")
        time.sleep(0.2)

        # While it lasts: the effect's channel walks through it and the other
        # two are left alone.  An effect of this bank runs for about a second,
        # so the looking is done in a fraction of one.
        walked, others = set(), set()
        for _ in range(4):
            walked.add(effect_on(session, where, CHANNEL))
            others.add(tuple(effect_on(session, where, c)
                             for c in range(3) if c != CHANNEL))
            time.sleep(0.15)

        assert 0 not in walked and len(walked) > 1, (
            f"the effect never played, or never moved: {walked}"
        )
        assert others == {(0, 0)}, (
            f"an effect landed on a channel of the tune's: {others}"
        )

        # And when it has run out, the channel is the tune's again -- which by
        # then has moved on, as it has been doing underneath all along.
        deadline = time.time() + 5.0
        while time.time() < deadline and effect_on(session, where, CHANNEL):
            time.sleep(0.2)
        assert not effect_on(session, where, CHANNEL), (
            "the effect finished and never gave its channel back"
        )
        assert word(session, where["PLY_AKM_Track1_PtTrack"]) != was, (
            "the tune stopped when the effect started"
        )
    finally:
        session.close()


if __name__ == "__main__":
    test_an_effect_plays_over_the_tune_and_lets_go()
    print("an effect plays over the tune and lets go")
