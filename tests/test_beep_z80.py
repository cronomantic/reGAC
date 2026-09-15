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
"""The speaker, watched at the port it hangs off.

A Spectrum's speaker cannot be read back, but the emulator keeps the last
value written to the port it is on, and looking at that often enough while a
noise is being made shows the bit going up and down.  Three things are asked
of it: that it moves while something is playing, that it is still when nothing
is, and that the three bits of border sharing the port come through untouched
-- which is the whole reason the interpreter keeps the border in memory rather
than trusting the port.

A number the build has no effect for makes no noise at all, rather than
reading past the end of the table, which is the same rule the tunes follow.
"""

import os
import re
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

SPECTRUM = os.path.join(ROOT, "z80", "spectrum")
SOURCE = os.path.join(SPECTRUM, "test_beep.asm")
SNAPSHOT = os.path.join(SPECTRUM, "beep.sna")
LISTING = os.path.join(SPECTRUM, "beep.lst")

SPEAKER = 0x10                  # the bit of the port the speaker is on
BORDER = 7                      # and the three the border is on
A_BORDER = 5                    # what the build sets it to
CLICK = 200                     # what to poke to hear the key click
NOT_AN_EFFECT = 99
LOOKS = 60                      # how many looks at the port are enough

if pytest is not None:
    needs_tools = pytest.mark.skipif(
        not emulator.available(), reason="sjasmplus and ZEsarUX must be in tools/"
    )
else:

    def needs_tools(func):
        return func


PORT = re.compile(r"FE port: ([0-9A-Fa-f]{2})")


def watch(session, which, where, looks=LOOKS):
    """Play that, and give back every value the port was seen holding."""
    session.command(f"write-memory {where['which']} {which}")
    time.sleep(0.2)
    seen = set()
    for _ in range(looks):
        found = PORT.search(session.command("get-io-ports"))
        assert found, "the emulator did not say what is on the port"
        seen.add(int(found.group(1), 16))
        if len(seen) > 1:               # both states: nothing more to learn
            break
    return seen


@needs_tools
def test_the_speaker_moves_and_the_border_does_not():
    listing = emulator.assemble(SOURCE, listing=LISTING)
    where = {name: emulator.label_address(listing, name)
             for name in ("ready_flag", "which", "rounds")}

    session = emulator.Session(machine="48k")
    try:
        session.load(SNAPSHOT)
        assert session.wait_for(where["ready_flag"], 0xFF, timeout=10.0), (
            "the build never started"
        )

        quiet = watch(session, 0, where, looks=20)
        assert quiet == {A_BORDER}, (
            f"the speaker moved with nothing playing: {quiet}"
        )

        for which, what in ((3, "an effect"), (CLICK, "the key click")):
            seen = watch(session, which, where)
            assert len(seen) > 1, f"{what} never moved the speaker: {seen}"
            assert {value & SPEAKER for value in seen} == {0, SPEAKER}, (
                f"{what} left the speaker where it was: {seen}"
            )
            assert {value & BORDER for value in seen} == {A_BORDER}, (
                f"{what} changed the border as well: {seen}"
            )

        silent = watch(session, NOT_AN_EFFECT, where, looks=20)
        assert silent == {A_BORDER}, (
            f"an effect the build has not got made a noise: {silent}"
        )
    finally:
        session.close()


@needs_tools
def test_every_effect_of_the_table_sounds():
    """Each of the five in turn, so that a badly written one -- a length of
    nought, a pitch that walks off the end -- is not left to be found by ear."""
    listing = emulator.assemble(SOURCE, listing=LISTING)
    where = {name: emulator.label_address(listing, name)
             for name in ("ready_flag", "which", "rounds", "how_many")}

    session = emulator.Session(machine="48k")
    try:
        session.load(SNAPSHOT)
        assert session.wait_for(where["ready_flag"], 0xFF, timeout=10.0)
        how_many = session.read(where["how_many"], 1)[0]
        assert how_many, "the build has no effects at all"
        for effect in range(1, how_many + 1):
            seen = watch(session, effect, where)
            assert len(seen) > 1, f"effect {effect} made no noise: {seen}"
    finally:
        session.close()


if __name__ == "__main__":
    test_the_speaker_moves_and_the_border_does_not()
    print("the speaker moves and the border does not")
    test_every_effect_of_the_table_sounds()
    print("every effect of the table sounds")
