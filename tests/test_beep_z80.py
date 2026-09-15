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
"""The speaker, listened to rather than looked at.

The emulator will write everything it plays to a file, which makes the plainest
oracle there is: did that make a noise?  Silence is a recording that never
moves; a note is one that does.  It was worth finding, and not only for this --
it is what settled that the PCW has no sound to be found here at all.

Watching the port instead, which is what this did first, turned out to be a
race: the bit goes up and down thousands of times a second and looking at it a
few dozen times can honestly miss it.  The recording cannot: it is every sample
the machine played, whether anybody was looking or not.

The port is still worth one look, for the other half of the question.  The
speaker of a Spectrum is a bit of the same port as the border, so a beep that
forgot the border would leave it black; the three bits of it have to come
through whatever the speaker is doing.
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
QUIET = 2                       # how many shapes a recording of nothing has

PORT = re.compile(r"FE port: ([0-9A-Fa-f]{2})")

if pytest is not None:
    needs_tools = pytest.mark.skipif(
        not emulator.available(), reason="sjasmplus and ZEsarUX must be in tools/"
    )
else:

    def needs_tools(func):
        return func


def played(which, where, sound, seconds=1.5):
    """Play that, and give back how much the recording moves and what the
    port was seen holding."""
    if os.path.exists(sound):
        os.remove(sound)
    session = emulator.Session(machine="48k", extra=["--aofile", sound])
    ports = set()
    try:
        session.load(SNAPSHOT)
        assert session.wait_for(where["ready_flag"], 0xFF, timeout=10.0), (
            "the build never started"
        )
        session.command(f"write-memory {where['which']} {which}")
        for _ in range(6):
            time.sleep(seconds / 6)
            found = PORT.search(session.command("get-io-ports"))
            assert found, "the emulator did not say what is on the port"
            ports.add(int(found.group(1), 16))
    finally:
        session.close()
    with open(sound, "rb") as f:
        heard = f.read()
    return len(set(heard)), ports


@needs_tools
def test_it_makes_a_noise_and_leaves_the_border_alone(tmp_path):
    where = {name: emulator.label_address(emulator.assemble(SOURCE,
                                                            listing=LISTING),
                                          name)
             for name in ("ready_flag", "which", "rounds", "how_many")}
    sound = str(tmp_path / "heard.raw")

    shapes, ports = played(0, where, sound)
    assert shapes <= QUIET, f"it made a noise with nothing playing: {shapes}"
    assert ports == {A_BORDER}, f"the speaker moved with nothing playing: {ports}"

    for which, what in ((3, "an effect"), (CLICK, "the key click")):
        shapes, ports = played(which, where, sound)
        assert shapes > QUIET, f"{what} made no noise at all: {shapes} shapes"
        assert {value & BORDER for value in ports} == {A_BORDER}, (
            f"{what} changed the border as well: {ports}"
        )
        assert {value & SPEAKER for value in ports} <= {0, SPEAKER}

    shapes, _ = played(NOT_AN_EFFECT, where, sound)
    assert shapes <= QUIET, (
        f"an effect the build has not got made a noise: {shapes}"
    )


@needs_tools
def test_every_effect_of_the_table_sounds(tmp_path):
    """Each of the five in turn, so that a badly written one -- a length of
    nought, a pitch that walks off the end -- is not left to be found by ear."""
    listing = emulator.assemble(SOURCE, listing=LISTING)
    where = {name: emulator.label_address(listing, name)
             for name in ("ready_flag", "which", "rounds", "how_many")}
    sound = str(tmp_path / "heard.raw")

    session = emulator.Session(machine="48k")
    try:
        session.load(SNAPSHOT)
        assert session.wait_for(where["ready_flag"], 0xFF, timeout=10.0)
        how_many = session.read(where["how_many"], 1)[0]
    finally:
        session.close()
    assert how_many, "the build has no effects at all"

    for effect in range(1, how_many + 1):
        shapes, _ = played(effect, where, sound, seconds=1.0)
        assert shapes > QUIET, f"effect {effect} made no noise: {shapes} shapes"


if __name__ == "__main__":
    import tempfile
    import pathlib
    folder = pathlib.Path(tempfile.mkdtemp())
    test_it_makes_a_noise_and_leaves_the_border_alone(folder)
    print("it makes a noise and leaves the border alone")
    test_every_effect_of_the_table_sounds(folder)
    print("every effect of the table sounds")
