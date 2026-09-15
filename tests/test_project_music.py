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
"""One command, and the music is in every machine that can play it.

What the author does is export from the tracker into a folder of their own,
name the files in the adventure's `/MUSIC`, say in the project which export is
the bank of sound effects, and run `regac make`.  Everything after that is
this: the source the assembler wants, written where it looks for it; the right
words handed to the assembler; and, on the machine whose music travels as a
file of its own, that file put on the disk and on the tape.

A machine with no sound chip is told apart here rather than made to fail: the
PCW and the 48K Spectrum build exactly as they did before and say so.
"""

import json
import os
import shutil
import subprocess
import sys

try:
    import pytest
except ImportError:
    pytest = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import emulator  # noqa: E402
from regac.__main__ import music_source  # noqa: E402
from regac.project import ProjectError  # noqa: E402
from test_music_z80 import TUNE  # noqa: E402

ADVENTURE = os.path.join(ROOT, "snapshots", "megacorp2.json")
EFFECTS = os.path.join(ROOT, "music", "effects.asm")
WRITTEN = os.path.join(ROOT, "music", "tunes.asm")

WITH_MUSIC = """
name   = "megacorp"
source = "megacorp.json"
output = "salida"
effects = "efectos.asm"

[targets.spectrum128]

[targets.plus3]

[targets.cpc]

[targets.spectrum48]
"""

if pytest is not None:
    needs_tools = pytest.mark.skipif(
        not emulator.available()
        or not os.path.exists(ADVENTURE)
        or not os.path.exists(TUNE)
        or not os.path.exists(EFFECTS),
        reason="sjasmplus and ZEsarUX must be in tools/, with a decompiled"
               " adventure, a tune and a bank of effects",
    )
else:

    def needs_tools(func):
        return func


def a_project(where):
    """A folder with an adventure that has music, the music itself, and a
    project file: what an author's own folder looks like."""
    with open(ADVENTURE, encoding="utf-8") as f:
        ddb = json.load(f)
    ddb["music"] = [{"file": "cancion.asm", "subsong": 0}]
    with open(os.path.join(where, "megacorp.json"), "w", encoding="utf-8") as f:
        json.dump(ddb, f)
    shutil.copyfile(TUNE, os.path.join(where, "cancion.asm"))
    shutil.copyfile(EFFECTS, os.path.join(where, "efectos.asm"))
    path = os.path.join(where, "megacorp.toml")
    with open(path, "w", encoding="utf-8") as f:
        f.write(WITH_MUSIC)
    return path


def test_a_tracker_file_is_exported_on_the_way(tmp_path):
    """An author who would rather name their tracker's own file can, and the
    build exports it: here with a stand-in for the tracker's exporter, because
    the real one is Arkos Tracker's and not ours to carry.

    Without one the build says what to do rather than handing the assembler a
    file it cannot read, which is the half of this that matters most: it is
    the only thing an author who has not got the exporter will ever see.
    """
    where = str(tmp_path)
    shutil.copyfile(TUNE, os.path.join(where, "cancion.aks"))
    tunes = [{"file": "cancion.aks", "subsong": 0}]
    written = os.path.join(where, "tunes.asm")

    with pytest.raises(ProjectError) as refused:
        music_source(tunes, where, written, None)
    assert "tools/" in str(refused.value) and ".asm" in str(refused.value)

    # A stand-in that does what the real one does: read a song, write the
    # assembly of it.
    stub = os.path.join(where, "export.py")
    with open(stub, "w", encoding="utf-8") as f:
        f.write("import shutil, sys\n"
                "shutil.copyfile(sys.argv[1], sys.argv[2])\n")
    music_source(tunes, where, written, [sys.executable, stub])
    source = open(written, encoding="utf-8").read()
    assert 'include "cancion.asm"' in source, source
    assert os.path.exists(os.path.join(where, "cancion.asm")), (
        "the exporter was run but what it wrote is not where the source says"
    )


@needs_tools
def test_one_command_puts_the_music_in(tmp_path):
    where = str(tmp_path)
    path = a_project(where)
    done = subprocess.run(
        [sys.executable, "-m", "regac", "make", path],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert done.returncode == 0, f"regac make failed:\n{done.stdout}\n{done.stderr}"

    # The source the assembler wants was written from the adventure's own
    # /MUSIC, and names the file where the author keeps it.
    written = open(WRITTEN, encoding="utf-8").read()
    assert "MUSIC_TUNE" in written and "cancion.asm" in written, written

    out = os.path.join(where, "salida")
    with open(os.path.join(out, "spectrum128", "megacorp.tap"), "rb") as f:
        tape = f.read()
    assert len(tape) > 20 * 1024, "the 128 tape is too small to hold anything"

    # The Amstrad's music is a file of its own, on the disk and on the tape,
    # because there it cannot be loaded where it is going to live.  A
    # directory entry is the name padded to eight and three.
    with open(os.path.join(out, "cpc", "megacorp.dsk"), "rb") as f:
        disk = f.read()
    assert b"MEGACORPMUS" in disk, "the Amstrad's disk has no music file on it"
    with open(os.path.join(out, "cpc", "megacorp.cdt"), "rb") as f:
        assert b"megacorp" in f.read().lower(), "the Amstrad's tape is empty"

    # The +3 carries its music inside the one file its loader reads, so what
    # says it is there is that the file grew by the two pieces.
    with open(os.path.join(out, "plus3", "megacorp.dsk"), "rb") as f:
        assert len(f.read()) > 64 * 1024, "the +3 disk is too small"

    # And the machine with no sound chip built anyway, and said why.
    assert os.path.exists(os.path.join(out, "spectrum48", "megacorp.tap"))
    assert "no sound chip" in done.stdout, done.stdout


if __name__ == "__main__":
    import tempfile
    test_a_tracker_file_is_exported_on_the_way(tempfile.mkdtemp())
    print("a tracker file is exported on the way")
    test_one_command_puts_the_music_in(tempfile.mkdtemp())
    print("one command puts the music in")
