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
goes and the screen to SCREEN.BIN when the game ends, and read when DOSBox-X
has gone.  The database is laid out as regac make lays it, in banks of sixty
four kilobytes, so the banks are exercised by every test that plays.

The keys come from a script, KEYS.BIN, a frame at a time, underneath the
interpreter's own next_key: see x86/script.asm.  Frames go by only while the
game waits for a key, so a key comes when the game is asking, and a game is
played the same way every time.  They used to be typed at the machine's own
keyboard with DOSBox-X's AUTOTYPE, which does it from a thread of its own
with nothing to keep it in step, and now and then stopped sending keys
altogether: a game that was waiting for them never got them.  The machine's
own keyboard is still played at, by one test and with AUTOTYPE, and there a
build counts every code the keyboard sends, in WATCH.BIN, so that the test
can tell which of the two stopped.
"""

import os
import struct
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
# A scripted key: down this many frames, and the next one this many after.
# More than the five frames a key let go takes to be forgotten, so that the
# same letter twice is typed twice.
HOLD_FRAMES = 3
EVERY_FRAMES = 10
START_FRAMES = 10               # before the first, with the game asking


def build(ddb, folder, source=GAME, defines=None, real_keyboard=False):
    """The interpreter with the adventure inside it, as GAME.EXE in
    `folder`, which is the drive DOSBox-X is given; played from a script,
    or with `real_keyboard` at the machine's own."""
    database = os.path.join(folder, "game.rgac")
    with open(database, "wb") as f:
        f.write(Database(ddb, machine="pc", page_bits=PAGE_BITS).build())
    wanted = {"DATABASE": '"' + database.replace(os.sep, "/") + '"',
              "TRANSCRIPT": 1}
    if from_an_amstrad(ddb):
        wanted["AMSTRAD_PICTURES"] = 1
    if not real_keyboard:
        wanted["SCRIPTED_KEYS"] = 1
    wanted.update(defines or {})
    image = dosbox.assemble(source, os.path.join(folder, "game.bin"),
                            include=X86, defines=wanted)
    with open(image, "rb") as f:
        exe = mz_exe(f.read(), stack=STACK)
    with open(os.path.join(folder, PROGRAM), "wb") as f:
        f.write(exe)


def script(typed, start=START_FRAMES):
    """The keys of `typed` as a script: each character a key, down and then
    up, in capitals as the keyboard hands them over.  A key is its character's
    code, which is as good a number for a key as any."""
    out = b""
    frame = start
    for character in typed:
        code = ord(character.upper())
        key = code & 0x7F
        out += struct.pack("<HBB", frame, key, code)
        out += struct.pack("<HBB", frame + HOLD_FRAMES, key, 0)
        frame += EVERY_FRAMES
    return out + struct.pack("<H", 0xFFFF)


def play(folder, typed, seconds=None, stop=False, start=START_FRAMES):
    """Type `typed` at the game in `folder` -- an order a line, each ended with
    an enter -- from a script, and give back what it printed, and the screen
    at the end if the game got there.  `start` is how many frames the game
    asks before the first key comes.  With `stop`, a game that does not end is
    stopped after `seconds`; what it printed until then is still there,
    because the transcript goes to the disk a character at a time."""
    clean(folder)
    with open(os.path.join(folder, "KEYS.BIN"), "wb") as f:
        f.write(script(typed, start))
    dosbox.run(folder, PROGRAM, cycles="max", seconds=seconds, stop=stop)
    return transcript(folder), screen(folder)


def play_at_the_keyboard(folder, typed, wait=3, pauses=6):
    """Type `typed` at the machine's own keyboard with AUTOTYPE, and give back
    what the game printed, the screen at the end if it got there, how many
    codes the keyboard sent, and how many were sent it."""
    clean(folder)
    keys = dosbox.keys(typed, pauses)
    pauses_typed = keys.count(dosbox.PAUSE)
    # As long as the typing takes, and then some: a key is PACE, and a pause
    # was measured at twice that.
    seconds = (wait + PACE * (len(keys) - pauses_typed)
               + 2 * PACE * pauses_typed + MARGIN)
    dosbox.run(folder, PROGRAM, cycles="max", typed=keys, wait=wait,
               pace=PACE, seconds=seconds)
    sent = 2 * (len(keys) - pauses_typed)       # down and up, every key
    came = 0
    path = os.path.join(folder, "WATCH.BIN")
    if os.path.exists(path):
        with open(path, "rb") as f:
            counts = f.read()
        if len(counts) >= 2:
            came = struct.unpack_from("<H", counts, len(counts) - 2)[0]
    return transcript(folder), screen(folder), came, sent


def clean(folder):
    for name in ("TRANSCR.TXT", "SCREEN.BIN", "WATCH.BIN", "KEYS.BIN"):
        path = os.path.join(folder, name)
        if os.path.exists(path):
            os.remove(path)


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
