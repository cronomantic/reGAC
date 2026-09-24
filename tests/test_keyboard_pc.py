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
"""The keyboard of a PC, by the Spectrum ROM's rules as on every machine.

What counts as typing a key was measured on the original and is written in
z80/common/keys.asm and tests/keystrokes.py.  DOSBox-X can press a key and let
it go and nothing else, so the keys here come from a script instead, a frame
at a time, underneath the interpreter's own next_key and wait_or_key: see
x86/test_keys.asm.  The frames are the timer's, fiftieths of a second of it.

That the keys of a real keyboard get there -- the interrupt, the BIOS, the
characters -- is what the games played in test_game_pc.py show.
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
import keystrokes  # noqa: E402
from regac.media import mz_exe  # noqa: E402

X86 = os.path.join(ROOT, "x86")
SOURCE = os.path.join(X86, "test_keys.asm")
CLOCKS_A_SECOND = 1193182
FRAMES_A_SECOND = 50
GAP = 5                         # frames between two steps of a script
START = 10                      # and before the first

if pytest is not None:
    needs_tools = pytest.mark.skipif(
        not dosbox.available(), reason="NASM and DOSBox-X must be on the path"
    )
else:

    def needs_tools(func):
        return func


def built(folder, *defines):
    wanted = {"SCRIPTED_KEYS": 1}
    for define in defines:
        name, _, value = define.partition("=")
        wanted[name] = value or 1
    image = dosbox.assemble(SOURCE, os.path.join(folder, "keys.bin"),
                            include=X86, defines=wanted)
    with open(image, "rb") as f:
        exe = mz_exe(f.read())
    with open(os.path.join(folder, "KEYS.EXE"), "wb") as f:
        f.write(exe)


def script(steps):
    """The steps of keystrokes.py as events a frame at a time: a key down or
    up every GAP frames, and a pause as that many frames more."""
    frame = START
    out = b""
    for step in steps:
        if isinstance(step, (int, float)):
            frame += round(step * FRAMES_A_SECOND)
            continue
        character, down = step
        out += struct.pack("<HBB", frame, ord(character) & 0x7F,
                           ord(character) if down else 0)
        frame += GAP
    return out + struct.pack("<H", 0xFFFF)


def at_frames(events):
    """A script of (frame, character, down) as they come."""
    out = b""
    for frame, character, down in events:
        out += struct.pack("<HBB", frame, ord(character) & 0x7F,
                           ord(character) if down else 0)
    return out + struct.pack("<H", 0xFFFF)


def typed(tmp_path, steps=None, events=None):
    """What next_key gave for the script, as (character, frame) pairs."""
    os.makedirs(tmp_path, exist_ok=True)
    folder = str(tmp_path)
    built(folder, "KEYS_TEST")
    with open(os.path.join(folder, "KEYS.BIN"), "wb") as f:
        f.write(script(steps) if steps is not None else at_frames(events))
    dosbox.run(folder, "KEYS.EXE", cycles="max")
    with open(os.path.join(folder, "KEYS.OUT"), "rb") as f:
        out = f.read()
    return [(chr(out[at]), struct.unpack_from("<H", out, at + 1)[0])
            for at in range(0, len(out), 3)]


def line(keys):
    return "".join(character for character, _ in keys).split(chr(13))[0]


@needs_tools
def test_keys_typed_over_each_other_all_arrive(tmp_path):
    assert line(typed(tmp_path, keystrokes.ROLLED)) == keystrokes.ROLLED_GIVES


@needs_tools
def test_a_key_pressed_while_another_is_held_types_nothing_twice(tmp_path):
    assert (line(typed(tmp_path, keystrokes.TWO_AT_ONCE))
            == keystrokes.TWO_AT_ONCE_GIVES)


@needs_tools
def test_a_key_held_down_repeats_after_thirty_five_frames_and_every_five(
        tmp_path):
    keys = [frame for character, frame in typed(tmp_path, keystrokes.HELD)
            if character == keystrokes.HELD_KEY]
    assert len(keys) > 2, keys
    gaps = [after - before for before, after in zip(keys, keys[1:])]
    assert gaps[0] == 35 and set(gaps[1:]) == {5}, gaps


@needs_tools
def test_a_key_that_bounces_is_typed_once(tmp_path):
    """A key let go is forgotten five frames later: pressed again sooner it is
    the same press, and later it is a new one."""
    def pressed_twice(apart):
        return [(10, "R", 1), (20, "R", 0), (20 + apart, "R", 1),
                (30 + apart, "R", 0)]
    assert line(typed(tmp_path / "a", events=pressed_twice(3))) == "R"
    assert line(typed(tmp_path / "b", events=pressed_twice(8))) == "RR"


@needs_tools
def test_a_hold_lasts_as_long_as_it_says(tmp_path):
    """A wait like HOLD's, a hundred frames with nothing pressed, timed on the
    BIOS's clock and the timer's count."""
    folder = str(tmp_path)
    built(folder, "HOLD_TEST", "HOLD_FRAMES=100")
    with open(os.path.join(folder, "KEYS.BIN"), "wb") as f:
        f.write(struct.pack("<H", 0xFFFF))
    dosbox.run(folder, "KEYS.EXE", cycles="max")
    with open(os.path.join(folder, "HOLD.OUT"), "rb") as f:
        clocks = struct.unpack("<I", f.read())[0]
    seconds = clocks / CLOCKS_A_SECOND
    assert 1.98 < seconds < 2.04, f"a hold of two seconds took {seconds:.3f}"
