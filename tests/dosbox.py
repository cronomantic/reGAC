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
"""A PC, run the way the tests of a DOS program can run: to the end.

The Z80 machines are driven while they run -- keys typed, memory read, the
counter pointed somewhere -- and that is the part of the harness that has
given the most trouble.  A DOS has a file system, so a program here hands
over what it did as a file and the test reads it when the machine has gone:
assemble, run, read.

DOSBox-X hangs if it is started without `-fastlaunch`; with it, `-conf` and
`-exit` it runs what it is told and goes away on its own.
"""

import os
import shutil
import subprocess

from emulator import longer

MACHINE = "cga"
# What DOSBox-X calls an XT at 4.77 MHz.  It is near one and not exact to the
# cycle, which is plenty for whether a thing is right and nothing for how long
# it takes: see doc/pendiente.md.
CYCLES = 315
RUN_SECONDS = longer(30)


def find_nasm():
    return shutil.which("nasm")


def find_dosbox():
    return shutil.which("dosbox-x")


def available():
    return bool(find_nasm() and find_dosbox())


def assemble(source, output, include=None, defines=None):
    """A flat binary, which is all NASM is asked for: the container is ours.
    `include` is a folder the source's %include lines are looked for in, and
    `defines` a mapping of names to what they stand for."""
    command = [find_nasm(), "-f", "bin", "-o", output]
    if include:
        command.append("-I" + os.path.join(include, ""))
    for name, value in (defines or {}).items():
        command.append(f"-D{name}={value}")
    result = subprocess.run(command + [source], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"{source} did not assemble:\n{result.stderr}")
    return output


# What DOSBox-X's AUTOTYPE calls the keys that are not a letter or a digit.
KEY_NAMES = {" ": "space", chr(13): "enter", ",": "comma", ".": "period",
             "-": "minus", "/": "slash", ";": "semicolon", chr(8): "bksp"}
# A pause, in AUTOTYPE's own terms: a comma where a key would be.
PAUSE = ","


def keys(text, pauses=6):
    """What AUTOTYPE is told to type for `text`: a key a character, and a
    run of pauses after every enter, for the picture of the room the order
    leads to to be drawn before the next is typed."""
    out = []
    for character in text:
        name = KEY_NAMES.get(character, character.lower())
        out.append(name)
        if character == chr(13):
            out += [PAUSE] * pauses
    return out


def run(folder, program, cycles=CYCLES, typed=None, wait=3, pace=0.25,
        seconds=None, stop=False):
    """Run one program in `folder`, which is drive C, and wait for DOSBox-X
    to go.  Whatever the program wrote is in `folder` afterwards.  `cycles` is
    how fast: a number, or "max" when only what comes out matters.

    `typed` is a list of keys for AUTOTYPE, which presses and lets go of each
    through the machine's own keyboard -- the same interrupt a person's keys
    come in by -- `wait` seconds after the program starts and `pace` seconds
    apart.  A run that types exits with DOSBox-X falling over on its way out,
    every time, after the program has gone and its files are written; so
    there what came out is what says whether it went, and not how it ended.

    With `stop`, a program that has not ended after `seconds` is stopped,
    which is how a game that never ends is looked at."""
    conf = os.path.join(folder, "dosbox.conf")
    speed = cycles if cycles == "max" else f"fixed {cycles}"
    typing = ""
    if typed:
        typing = f"autotype -w {wait} -p {pace} " + " ".join(typed) + "\n"
    with open(conf, "w") as f:
        f.write(f"[dosbox]\nmachine={MACHINE}\n"
                f"[cpu]\ncycles={speed}\n"
                f"[autoexec]\nmount c .\nc:\n{typing}{program}\nexit\n")
    command = [find_dosbox(), "-conf", conf, "-fastlaunch", "-exit"]
    # A program that has not ended when its time is up is stopped from
    # outside, the whole tree of it: what the path calls dosbox-x may be a
    # shim that started the emulator, and killing the shim alone leaves the
    # emulator running.
    process = subprocess.Popen(command, cwd=folder, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
    try:
        process.wait(timeout=seconds or RUN_SECONDS)
    except subprocess.TimeoutExpired:
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(process.pid)],
                       capture_output=True)
        process.wait()
        if not stop:
            raise
        return
    if process.returncode and not typed:
        raise subprocess.CalledProcessError(process.returncode, command)
