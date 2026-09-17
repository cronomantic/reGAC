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
"""Typing the way people type, which is not one key let go before the next.

What counts as typing a key is the Spectrum ROM's, because the original read
its keys through the ROM, and it was measured on the original: L, O and K each
pressed before the one before was let go come out as LOK, and a key held two
seconds comes out six times.  Every machine's interpreter does the same now,
in z80/common/keys.asm, and these are the three things its tests type, in
letters every adventure here has a character for:

  - ROLLED, each key down before the last is up, enter included: SOL;
  - TWO_AT_ONCE, a second key pressed and let go while the first stays down:
    only the first, once, because while two are held nothing is decided;
  - HELD, one key held four seconds of ours, which in an emulator running at
    a quarter of the machine's speed is still past the ROM's delay: more than
    one of it.

A step is a key and whether it goes down or up; a number is a pause.
"""

import time

ENTER = chr(13)

ROLLED = [("S", 1), ("O", 1), ("S", 0), ("L", 1), ("O", 0), (ENTER, 1),
          ("L", 0), (ENTER, 0)]
ROLLED_GIVES = "SOL"

TWO_AT_ONCE = [("A", 1), ("E", 1), ("E", 0), ("A", 0), (ENTER, 1), (ENTER, 0)]
TWO_AT_ONCE_GIVES = "A"

HELD = [("R", 1), 4.0, ("R", 0), (ENTER, 1), (ENTER, 0)]
HELD_KEY = "R"


def play(session, steps, events, gap=0.15):
    """Send the steps as key events.  `events` says which of the emulator's key
    numbers a character is where it is not its own ASCII."""
    for step in steps:
        if isinstance(step, (int, float)):
            time.sleep(step)
            continue
        char, down = step
        code = events.get(char, ord(char.lower()))
        session.command(f"send-keys-event {code} {down}")
        time.sleep(gap)
