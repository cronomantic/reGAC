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
"""The adventures written on an Amstrad, taken off their disks.

They are not in snapshots/ as the Spectrum's are: they come off the disks in
juegos/, which are not ours to keep in the repository, the way doc/pendiente.md
tells it -- disk.py lays the file where it loads, or reads the raw tracks of a
disk with no directory, and deGAC reads the adventure out of that.  Six of
them, the two parts of each of the three:

    Bangkok    CARVALHO.FAC and CARVALHO.EXP
    MegaCorp   MEGACOR2.BIN and MEGACOR3.BIN
    Vajillas   the two adventures in the raw tracks

They are decompiled once a run, into a folder of their own.
"""

import json
import os
import subprocess
import sys
import tempfile
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import disk  # noqa: E402

GAMES = os.path.join(ROOT, "juegos")

# (name, archive, file on the disk or the part of the raw tracks)
AMSTRAD_GAMES = [
    ("bangkok_fac", "carvalho_ams.zip", "CARVALHO.FAC"),
    ("bangkok_exp", "carvalho_ams.zip", "CARVALHO.EXP"),
    ("megacorp2", "megacorp_ams.zip", "MEGACOR2.BIN"),
    ("megacorp3", "megacorp_ams.zip", "MEGACOR3.BIN"),
    ("vajillas1", "vajillas_ams.zip", 1),
    ("vajillas2", "vajillas_ams.zip", 2),
]

_decompiled = {}


def available():
    return all(os.path.exists(os.path.join(GAMES, archive))
               for _, archive, _ in AMSTRAD_GAMES)


def disk_image(archive):
    with zipfile.ZipFile(os.path.join(GAMES, archive)) as inside:
        for name in inside.namelist():
            if name.lower().endswith(".dsk"):
                return inside.read(name)
    raise FileNotFoundError(f"no disk in {archive}")


def memory_of(archive, which):
    blob = disk_image(archive)
    if isinstance(which, int):
        stream = disk.raw_stream(blob)
        return disk.raw_memory(stream, disk.adventures(stream)[which - 1])
    area = disk.data_area(blob)
    memory, _ = disk.memory(disk.contents(area, disk.directory(area)[which]))
    return memory


def amstrad_adventures():
    """Every one of them as (name, path of its JSON), decompiled the first
    time they are asked for."""
    if not _decompiled:
        folder = tempfile.mkdtemp(prefix="regac-amstrad-")
        for name, archive, which in AMSTRAD_GAMES:
            image = os.path.join(folder, name + ".bin")
            with open(image, "wb") as f:
                f.write(bytes(memory_of(archive, which)))
            path = os.path.join(folder, name + ".json")
            subprocess.run([sys.executable, os.path.join(ROOT, "deGAC.py"),
                            "-m", "cpc", image, path],
                           check=True, capture_output=True)
            _decompiled[name] = path
    return list(_decompiled.items())


def amstrad_adventure(name):
    with open(dict(amstrad_adventures())[name], encoding="utf-8") as f:
        return json.load(f)
