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
"""The project file: what is of the machine rather than of the adventure.

An adventure says nothing about banks, loading screens or how big its pictures
should be drawn; those are decisions about where it is going, and they belong
together in one file rather than scattered through a dozen command lines.  So:

    name   = "megacorp"
    source = "megacorp.json"

    [targets.spectrum128]
    screen = "carga.scr"

    [targets.pcw]
    screen = "carga.pcw"
    scale  = [2, 1]

and `regac make` does the rest: builds the database each machine wants, in the
banks it asked for, assembles the interpreter for it, and puts the media where
the output says.

What is *not* in the project file is anything the machine decides for itself.
Which of a Spectrum's pages the banks go in, where the interpreter loads, how
big a screen dump is: those are facts about the machine, and they live in the
table below or in the machine's own source.
"""

import os
import shutil
import subprocess
import sys

try:
    import tomllib
except ImportError:                     # pragma: no cover - Python below 3.11
    tomllib = None

from .media import MSX_SCREEN_BYTES, msx_screen


class ProjectError(Exception):
    pass


class Target:
    """One machine, and everything it takes to build for it.

    `database` and `defs` are where that machine's own source expects to find
    them, so they are written into the tree next to it and not into the
    output: they are part of the build, not of what is handed over.
    """

    def __init__(self, machine, folder, source, database, banks="none",
                 defs=None, media=(), release=None, binary=None, boot=None,
                 screen_bytes=0, screen_when="release", scales=(1,)):
        self.machine = machine          # what regac build calls it
        self.folder = folder            # where its interpreter lives
        self.source = source            # and which file of it to assemble
        self.database = database
        self.banks = banks              # the default, which a project may change
        self.defs = defs                # the include regac build writes
        self.media = media              # what the assembler leaves behind
        self.release = release          # or the machine regac release knows
        self.binary = binary            # what it puts on the medium
        self.boot = boot                # and the loader that goes in front
        self.screen_bytes = screen_bytes
        self.screen_when = screen_when  # "assembly" or "release"
        self.scales = scales            # the widths a picture may be drawn at

    def at(self, *names):
        return os.path.join(self.folder, *names)


SPECTRUM = os.path.join("z80", "spectrum")
CPC = os.path.join("z80", "cpc")
PCW = os.path.join("z80", "pcw")
MSX = os.path.join("z80", "msx")

# What each machine needs.  A tape is written by the assembler itself, because
# on a Spectrum the medium is blocks of the very thing being assembled; a disk
# is put together afterwards by regac release.
TARGETS = {
    "spectrum48": Target(
        machine="spectrum48", folder=SPECTRUM, source="game.asm",
        database="game.rgac", media=("game.tap",),
        screen_bytes=6912, screen_when="assembly",
    ),
    "spectrum128": Target(
        machine="spectrum128", folder=SPECTRUM, source="game128.asm",
        database="game128.rgac", banks="16k", defs="banks.inc",
        media=("game128.tap",),
        screen_bytes=6912, screen_when="assembly",
    ),
    "plus3": Target(
        machine="spectrum128", folder=SPECTRUM, source="game3.asm",
        database="game3.rgac", banks="16k", defs="banks3.inc",
        release="plus3", binary="game3_code.bin", boot="game3_boot.bin",
        screen_bytes=6912, screen_when="assembly",
    ),
    "cpc": Target(
        machine="cpc", folder=CPC, source="game.asm", database="game.rgac",
        release="cpc", binary="game.bin",
        screen_bytes=0x4000,
    ),
    "msx": Target(
        machine="msx", folder=MSX, source="game.asm", database="game.rgac",
        release="msx", binary="game.bin",
        screen_bytes=MSX_SCREEN_BYTES,
    ),
    "pcw": Target(
        machine="pcw", folder=PCW, source="game.asm", database="game.rgac",
        banks="16k", defs="banks.inc",
        release="pcw", binary="game_code.bin", boot="boot.bin",
        screen_bytes=2 * 16 * 720, scales=(1, 2),
    ),
}

# What a target may say for itself, and nothing else: a name that is not here
# is a mistake, and saying so beats building the wrong thing quietly.
TARGET_KEYS = {"banks", "screen", "scale", "music-buffer"}
PROJECT_KEYS = {"name", "source", "output", "targets"}


def read(path):
    """Read a project file and check it says things that exist."""
    if tomllib is None:
        raise ProjectError("reading a project file needs Python 3.11 or later")
    with open(path, "rb") as f:
        project = tomllib.load(f)
    strange = set(project) - PROJECT_KEYS
    if strange:
        raise ProjectError(f"{path}: {', '.join(sorted(strange))} means nothing here")
    for wanted in ("name", "source"):
        if wanted not in project:
            raise ProjectError(f"{path}: it does not say what {wanted} is")
    targets = project.get("targets") or {}
    if not targets:
        raise ProjectError(f"{path}: it does not say which machines to build for")
    for name, settings in targets.items():
        if name not in TARGETS:
            raise ProjectError(
                f"{path}: there is no {name}; try one of {', '.join(sorted(TARGETS))}"
            )
        strange = set(settings) - TARGET_KEYS
        if strange:
            raise ProjectError(
                f"{path}: {name} says {', '.join(sorted(strange))}, which means nothing"
            )
        scale = settings.get("scale")
        if scale is not None:
            across, down = wide(scale)
            if across not in TARGETS[name].scales or down != 1:
                raise ProjectError(
                    f"{path}: {name} cannot draw at {across} by {down}; "
                    f"it draws at {', '.join(str(s) for s in TARGETS[name].scales)} "
                    "across and one down"
                )
    project.setdefault("output", "release")
    return project


def wide(scale):
    """A scale as a pair, whether it was written as one number or as two."""
    if isinstance(scale, int):
        return scale, 1
    if len(scale) != 2:
        raise ProjectError(f"a scale is one number or two, not {scale}")
    return int(scale[0]), int(scale[1])


def find_assembler():
    """sjasmplus, in tools/ as the tests keep it, or wherever the path has it."""
    here = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "tools", "sjasmplus.exe")
    if os.path.isfile(here):
        return here
    found = shutil.which("sjasmplus")
    if not found:
        raise ProjectError("sjasmplus is not in tools/ and not on the path")
    return found


def assemble(target, root, defines=()):
    """Assemble one machine's interpreter where it sits."""
    folder = os.path.join(root, target.folder)
    listing = os.path.splitext(target.source)[0] + ".lst"
    result = subprocess.run(
        [find_assembler(), f"--lst={listing}"]
        + [f"-D{name}" for name in defines]
        + [target.source],
        cwd=folder, capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise ProjectError(
            f"{target.source} did not assemble:\n{result.stdout}\n{result.stderr}"
        )
    return os.path.join(folder, listing)


def screen_for(target, path, root):
    """Read a loading screen and make sure it is that machine's own."""
    with open(os.path.join(root, path), "rb") as f:
        screen = f.read()
    if target.machine == "msx":
        screen = msx_screen(screen)
    if len(screen) != target.screen_bytes:
        raise ProjectError(
            f"{path} is {len(screen)} bytes and a {target.machine} screen is "
            f"{target.screen_bytes}"
        )
    return screen
