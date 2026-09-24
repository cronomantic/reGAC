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
# The interpreters in z80/ and x86/ are not part of this program and are given
# under the MIT licence instead: see z80/LICENSE and x86/LICENSE.
#
"""The noises of a PC's speaker last what they last on a Spectrum.

The speaker is one bit, like the Spectrum 48's, and x86/sound.asm is that
machine's engine with its waits counted on the timer rather than in the
processor's cycles, which on a PC may be any speed: half a wave of pitch p is
sixteen of the Spectrum's cycles at 3.5 MHz a step, which is p times sixty
elevenths of the timer's clocks.  So the click and every noise of the table
are timed here on the timer and the BIOS's clock, and held to that sum, flip
by flip, the pitch walking as the engine walks it.
"""

import os
import struct
import sys

try:
    import pytest
except ImportError:
    pytest = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import dosbox  # noqa: E402
from test_keyboard_pc import built, needs_tools  # noqa: E402

CLICK = (200, 20, 0)
# The five noises every adventure has when it names none of its own: the
# table in x86/sound.asm, which is z80/common/effects.asm's.
EFFECTS = [(200, 150, -1), (60, 150, 1), (250, 100, 0), (30, 110, 2),
           (60, 200, 0)]


def half_wave(pitch):
    return pitch * 60 // 11


def lasts(pitch, flips, step):
    """The timer's clocks a noise lasts: every flip waits half a wave of the
    pitch as it stands, which then walks by the step and stops at the ends."""
    total = 0
    for _ in range(flips):
        total += half_wave(pitch or 1)
        pitch += step
        pitch = max(1, min(255, pitch))
    return total


def test_the_table_is_the_one_every_machine_plays():
    source = open(os.path.join(ROOT, "x86", "sound.asm"), encoding="utf-8").read()
    table = source[source.index("%else", source.index("beep_effects:")):]
    rows = [line.split(";")[0].replace("db", "").split(",")
            for line in table.splitlines()[1:6]]
    assert [(int(r[0]), int(r[1]), int(r[2])) for r in rows] == EFFECTS


@needs_tools
def test_every_noise_lasts_what_it_lasts_on_a_spectrum(tmp_path):
    folder = str(tmp_path)
    built(folder, "SOUND_TEST")
    with open(os.path.join(folder, "KEYS.BIN"), "wb") as f:
        f.write(struct.pack("<H", 0xFFFF))
    dosbox.run(folder, "KEYS.EXE", cycles="max")
    with open(os.path.join(folder, "SOUND.OUT"), "rb") as f:
        out = f.read()
    measured = [struct.unpack_from("<I", out, at)[0]
                for at in range(0, len(out), 4)]
    wanted = [lasts(*CLICK)] + [lasts(*effect) for effect in EFFECTS]
    assert len(measured) == len(wanted), measured
    for number, (got, should) in enumerate(zip(measured, wanted)):
        # within a hundredth: the flips are timed from the note's start, so
        # a wait that ends late does not make the next one later
        assert should * 0.99 < got < should * 1.01, (
            f"{'the click' if number == 0 else f'noise {number}'} lasted "
            f"{got} clocks, not about {should}")
