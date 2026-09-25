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
"""How long a picture takes to draw on the machine, measured, not guessed.

Decided by the user: regac draw does not estimate the time a picture takes,
it measures it, when it is asked to.  The picture goes to the interpreter
itself -- the build of each machine that draws one picture and stops,
test_picture.asm -- in ZEsarUX, and what is counted is the Z80's own clock
cycles, turned into seconds of the real machine.  That is how the slow tests
measure all the pictures of the eight adventures (tests/test_all_pictures*.py)
and what the budget of four or five seconds is held to.

Three machines have that build: the Spectrum, the CPC and the MSX.  It needs
the tools the tests need, in tools/, and it takes as long as the emulator
takes to come up: seconds, not a moment.  The harness is the tests' own,
tests/emulator.py, loaded from where it is.
"""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time

from .devices import from_an_amstrad

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# What four or five seconds are: a picture over the first is slow, and one
# over the second is more than a player will wait for.
SLOW, TOO_SLOW = 4.0, 5.0

# How each machine is brought up with the build that draws a picture: see the
# slow test of each.
MACHINES = {
    "spectrum": {"folder": "spectrum", "build": "spectrum48", "hz": 3_500_000,
                 "emulator": None, "snapshot": "picture.sna"},
    "cpc": {"folder": "cpc", "build": "cpc", "hz": 4_000_000,
            "emulator": "CPC6128", "binary": "picture.bin", "at": 0x4000,
            "settle": 3.0, "timeout": 20.0},
    "msx": {"folder": "msx", "build": "msx", "hz": 3_579_545,
            "emulator": "MSX1", "binary": "picture.bin", "at": 0x8000,
            "settle": 7.0, "timeout": 60.0},
}


def harness():
    spec = importlib.util.spec_from_file_location(
        "emulator", os.path.join(ROOT, "tests", "emulator.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def why_not(machine):
    """Why a picture cannot be measured on that machine, or None."""
    if machine not in MACHINES:
        return (f"the time is measured on spectrum, cpc and msx, which have a "
                f"build that draws one picture, and not on {machine}")
    if not harness().available():
        return "measuring needs sjasmplus and ZEsarUX in tools/"
    return None


def measure(ddb, picture, machine):
    """Seconds of the real machine the picture takes to draw, or None if it
    never finished."""
    emulator = harness()
    spec = MACHINES[machine]
    folder = os.path.join(ROOT, "z80", spec["folder"])
    with tempfile.TemporaryDirectory() as scratch:
        adventure = os.path.join(scratch, "adventure.json")
        with open(adventure, "w", encoding="utf-8") as f:
            json.dump(ddb, f)
        subprocess.run(
            [sys.executable, "-m", "regac", "build", adventure,
             os.path.join(folder, "picture.rgac"), "-m", spec["build"]],
            cwd=ROOT, check=True, capture_output=True)
    defines = ("AMSTRAD_PICTURES",) if machine == "cpc" and from_an_amstrad(ddb) else ()
    listing = emulator.assemble(os.path.join(folder, "test_picture.asm"),
                                listing=os.path.join(folder, "picture.lst"),
                                defines=defines)
    where = {name: emulator.label_address(listing, name)
             for name in ("done_flag", "picture_wanted", "go_flag")}
    session = (emulator.Session(machine=spec["emulator"]) if spec["emulator"]
               else emulator.Session())
    try:
        if "snapshot" in spec:
            session.load(os.path.join(folder, spec["snapshot"]))
            # it draws one picture of its own accord, which says it is up
            if not session.wait_for(where["done_flag"], 0xFF, timeout=60.0):
                raise RuntimeError(f"the {machine} never got going")
        else:
            time.sleep(emulator.longer(spec["settle"]))
            with open(os.path.join(folder, spec["binary"]), "rb") as f:
                blob = f.read()
            if not session.start_code(blob, spec["at"], where["done_flag"],
                                      timeout=spec["timeout"]):
                raise RuntimeError(f"the {machine} never got going")
        number = int(picture)
        session.command(f"write-memory {where['picture_wanted']} "
                        f"{number & 255} {number >> 8}")
        session.command(f"write-memory {where['done_flag']} 0")
        session.command("reset-tstates-partial")
        session.command(f"write-memory {where['go_flag']} 1")
        return session.seconds_until(where["done_flag"], spec["hz"])
    finally:
        session.close()
