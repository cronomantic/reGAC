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
"""The PC interpreter built and played, for the tests.

A PC hands over what it did as files, so a game here is built with
TRANSCRIPT, which makes it write everything it prints to TRANSCR.TXT as it
goes and the screen to SCREEN.BIN when the game ends; typed at through the
machine's own keyboard with AUTOTYPE; and read when DOSBox-X has gone.  The
database is laid out as regac make lays it, in banks of sixty four
kilobytes, so the banks are exercised by every test that plays.
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import dosbox  # noqa: E402
from regac.binary import Database  # noqa: E402
from regac.devices import from_an_amstrad  # noqa: E402
from regac.media import mz_exe  # noqa: E402

X86 = os.path.join(ROOT, "x86")
GAME = os.path.join(X86, "game.asm")
PAGE_BITS = 16                  # regac make's banks for the PC
STACK = 2048                    # and its stack
PROGRAM = "GAME.EXE"
PACE = 0.25                     # seconds between two keys typed
MARGIN = 45                     # and what a game may take beyond its typing
SETTLE = 15                     # or, for one that never ends, to answer the last
ENTER = chr(13)


def build(ddb, folder, source=GAME, defines=None):
    """The interpreter with the adventure inside it, as GAME.EXE in
    `folder`, which is the drive DOSBox-X is given."""
    database = os.path.join(folder, "game.rgac")
    with open(database, "wb") as f:
        f.write(Database(ddb, machine="pc", page_bits=PAGE_BITS).build())
    wanted = {"DATABASE": '"' + database.replace(os.sep, "/") + '"',
              "TRANSCRIPT": 1}
    if from_an_amstrad(ddb):
        wanted["AMSTRAD_PICTURES"] = 1
    wanted.update(defines or {})
    image = dosbox.assemble(source, os.path.join(folder, "game.bin"),
                            include=X86, defines=wanted)
    with open(image, "rb") as f:
        exe = mz_exe(f.read(), stack=STACK)
    with open(os.path.join(folder, PROGRAM), "wb") as f:
        f.write(exe)


def play(folder, typed, wait=3, pauses=6, seconds=None, stop=False):
    """Type `typed` at the game in `folder` -- an order a line, each ended with
    an enter -- and give back what it printed, and the screen at the end if
    the game got there.  With `stop`, a game that does not end is stopped
    after `seconds`; what it printed until then is still there, because the
    transcript goes to the disk a character at a time."""
    for name in ("TRANSCR.TXT", "SCREEN.BIN"):
        path = os.path.join(folder, name)
        if os.path.exists(path):
            os.remove(path)
    keys = dosbox.keys(typed, pauses)
    if seconds is None:
        # As long as the typing takes, and then some: a key is PACE, and a
        # pause was measured at twice that.  A fixed limit was too little for
        # MegaCorp's five orders, which take thirty seconds on their own and
        # more in a busy parallel run.
        pauses_typed = keys.count(dosbox.PAUSE)
        seconds = (wait + PACE * (len(keys) - pauses_typed)
                   + 2 * PACE * pauses_typed
                   + (SETTLE if stop else MARGIN))
    dosbox.run(folder, PROGRAM, cycles="max", typed=keys, wait=wait,
               pace=PACE, seconds=seconds, stop=stop)
    return transcript(folder), screen(folder)


def transcript(folder):
    """What the game printed, as text: a line a line, and a rub out taking
    back the character before it, as it did on the screen."""
    path = os.path.join(folder, "TRANSCR.TXT")
    if not os.path.exists(path):
        return ""
    with open(path, "rb") as f:
        raw = f.read().decode("latin-1")
    out = []
    for character in raw:
        if character == chr(8):
            if out and out[-1] != chr(10):
                out.pop()
        else:
            out.append(character)
    return "".join(out)


def screen(folder):
    path = os.path.join(folder, "SCREEN.BIN")
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return f.read()


def pixel(screen_bytes, x, y):
    """The value of one point of the card's memory, x across the 320 and y
    down the 200."""
    at = (y & 1) * 0x2000 + (y >> 1) * 80 + (x >> 2)
    return (screen_bytes[at] >> (6 - 2 * (x & 3))) & 3
