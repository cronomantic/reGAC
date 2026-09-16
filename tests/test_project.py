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
"""The project file, and the one command that builds everything it names.

What is of the machine rather than of the adventure -- which banks, which
loading screen, how wide the pictures are drawn -- is said once here instead
of in a dozen command lines, and `regac make` does the rest for every machine
the project lists.

The last of these switches a PCW on with what came out, because a file that
builds is not the same as a file that runs.
"""

import json
import os
import random
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
from regac.project import ProjectError, TARGETS  # noqa: E402
from regac.srcgen import generate  # noqa: E402
from regac.project import read as read_project  # noqa: E402

ADVENTURE = os.path.join(ROOT, "snapshots", "megacorp2.json")
SCREENS = {"scr": 6912, "cpc": 0x4000, "pcw": 2 * 16 * 720}

if pytest is not None:
    needs_tools = pytest.mark.skipif(
        not emulator.available() or not os.path.exists(ADVENTURE),
        reason="sjasmplus must be in tools/, with a decompiled adventure",
    )
else:

    def needs_tools(func):
        return func


def a_project(where, body, screens=True):
    """A folder with an adventure, its loading screens and a project file."""
    shutil.copyfile(ADVENTURE, os.path.join(where, "megacorp.json"))
    if screens:
        for suffix, size in SCREENS.items():
            filler = random.Random(len(suffix))
            with open(os.path.join(where, "carga." + suffix), "wb") as f:
                f.write(bytes(filler.randrange(256) for _ in range(size)))
    path = os.path.join(where, "megacorp.toml")
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)
    return path


EVERY_MACHINE = """
name   = "megacorp"
source = "megacorp.json"
output = "salida"

[targets.spectrum48]

[targets.spectrum128]
screen = "carga.scr"

[targets.plus3]
screen = "carga.scr"

[targets.cpc464]
screen = "carga.cpc"

[targets.cpc6128]
screen = "carga.cpc"

[targets.pcw]
screen = "carga.pcw"
scale  = [2, 1]
"""


def make(path, *extra):
    return subprocess.run(
        [sys.executable, "-m", "regac", "make", path] + list(extra),
        cwd=ROOT, capture_output=True, text=True,
    )


def test_it_says_what_is_wrong_with_a_project(tmp_path):
    """A name that means nothing is a mistake, not something to build around."""
    where = str(tmp_path)
    for body, complaint in (
        ('name = "x"\n[targets.spectrum48]\n', "source"),
        ('name = "x"\nsource = "megacorp.json"\n', "which machines"),
        ('name = "x"\nsource = "megacorp.json"\n[targets.oric]\n', "no oric"),
        ('name = "x"\nsource = "megacorp.json"\n[targets.cpc464]\nbancos = "16k"\n',
         "bancos"),
        ('name = "x"\nsource = "megacorp.json"\n[targets.cpc464]\nscale = 2\n',
         "cannot draw"),
        ('name = "x"\nsource = "megacorp.json"\nsalida = "x"\n[targets.cpc464]\n',
         "salida"),
    ):
        path = a_project(where, body, screens=False)
        try:
            read_project(path)
        except ProjectError as e:
            assert complaint in str(e), f"{body!r} complained about {e}"
        else:
            raise AssertionError(f"{body!r} should not have been accepted")


def test_a_scale_is_checked_against_what_the_machine_can_do(tmp_path):
    path = a_project(
        str(tmp_path),
        'name = "x"\nsource = "megacorp.json"\n[targets.pcw]\nscale = [3, 1]\n',
        screens=False,
    )
    try:
        read_project(path)
    except ProjectError as e:
        assert "3 by 1" in str(e)
    else:
        raise AssertionError("three points wide is not something the PCW does")
    # and what it can do is accepted, written either way round
    for scale in ("1", "2", "[1, 1]", "[2, 1]"):
        path = a_project(
            str(tmp_path),
            f'name = "x"\nsource = "megacorp.json"\n[targets.pcw]\nscale = {scale}\n',
            screens=False,
        )
        read_project(path)


@needs_tools
def test_one_command_builds_every_machine(tmp_path):
    where = str(tmp_path)
    path = a_project(where, EVERY_MACHINE)
    done = make(path)
    assert done.returncode == 0, f"regac make failed:\n{done.stdout}\n{done.stderr}"

    out = os.path.join(where, "salida")
    for folder, name in (
        ("spectrum48", "megacorp.tap"),
        ("spectrum128", "megacorp.tap"),
        ("plus3", "megacorp.dsk"),
        ("cpc464", "megacorp.cdt"),
        ("cpc6128", "megacorp.dsk"),
        ("pcw", "megacorp.dsk"),
    ):
        made = os.path.join(out, folder, name)
        assert os.path.exists(made), f"{folder}/{name} was never written"
        assert os.path.getsize(made) > 16 * 1024, f"{folder}/{name} is too small"

    # The loading screens really went on: each is its machine's own dump, and
    # a sector of it is enough to look for, because a disk breaks a file up.
    for folder, name, suffix in (
        ("spectrum128", "megacorp.tap", "scr"),
        ("plus3", "megacorp.dsk", "scr"),
        ("cpc6128", "megacorp.dsk", "cpc"),
        ("pcw", "megacorp.dsk", "pcw"),
    ):
        with open(os.path.join(where, "carga." + suffix), "rb") as f:
            screen = f.read()
        with open(os.path.join(out, folder, name), "rb") as f:
            assert screen[:512] in f.read(), (
                f"the loading screen never reached {folder}/{name}"
            )
    # and the one that asked for no screen did not get one
    with open(os.path.join(where, "carga.scr"), "rb") as f:
        screen = f.read()
    with open(os.path.join(out, "spectrum48", "megacorp.tap"), "rb") as f:
        assert screen[:512] not in f.read(), "a screen turned up uninvited"


@needs_tools
def test_only_the_machine_that_was_asked_for(tmp_path):
    where = str(tmp_path)
    path = a_project(where, EVERY_MACHINE)
    done = make(path, "-t", "pcw")
    assert done.returncode == 0, f"regac make failed:\n{done.stdout}\n{done.stderr}"
    out = os.path.join(where, "salida")
    assert os.path.exists(os.path.join(out, "pcw", "megacorp.dsk"))
    assert not os.path.exists(os.path.join(out, "cpc464")), (
        "it built more than it was told"
    )


@needs_tools
def test_what_it_built_actually_runs(tmp_path):
    """A file that builds is not the same as a file that runs, so one of them
    is switched on: the PCW, which needs no menu and no tape."""
    where = str(tmp_path)
    path = a_project(where, EVERY_MACHINE)
    assert make(path, "-t", "pcw").returncode == 0
    disk = os.path.join(where, "salida", "pcw", "megacorp.dsk")

    with open(ADVENTURE, encoding="utf-8") as f:
        ddb = json.load(f)
    from test_game_pcw import screen, wait_screen  # noqa: F401
    from test_text_pcw import glyph_table
    from regac.binary import Database

    glyphs = glyph_table(Database(ddb, machine="pcw"))
    prompt = ddb["messages"]["240"].strip()[:3]
    session = emulator.Session(
        machine="PCW8256", extra=["--enable-dsk", "--dsk-file", disk]
    )
    try:
        lines = wait_screen(session, glyphs, prompt)
    finally:
        session.close()
    assert any(prompt in line for line in lines if line), (
        f"what regac make built never got going: {lines}"
    )


KEPT_BACK = """
name   = "megacorp"
source = "megacorp.gac"
output = "salida"

[targets.spectrum48]

[targets.cpc464]
"""


@needs_tools
def test_a_source_is_read_again_for_every_machine(tmp_path):
    """A source may keep some of itself back for some machines, so the one
    command has to read it once for each of them rather than once for all.

    What is looked at is the databases: the same adventure built twice, with
    one message longer on one machine than on the other, cannot come out the
    same size unless the reading happened once and was handed round.
    """
    where = str(tmp_path)
    with open(ADVENTURE, encoding="utf-8") as f:
        ddb = json.load(f)
    source = generate(ddb)
    # A message that is not the same on the two machines, by a good margin.
    mark = "#1\n"
    at = source.index(mark) + len(mark)
    source = (source[:at] + ".if cpc\nCorto.\n.else\n"
              + "Largo, y mucho mas largo, para que se note en el tamano. " * 8
              + "\n.end\n" + source[at:])
    with open(os.path.join(where, "megacorp.gac"), "w", encoding="utf-8") as f:
        f.write(source)
    path = os.path.join(where, "megacorp.toml")
    with open(path, "w", encoding="utf-8") as f:
        f.write(KEPT_BACK)

    done = make(path)
    assert done.returncode == 0, f"regac make failed:\n{done.stdout}\n{done.stderr}"
    sizes = {}
    for which, folder, built in (("spectrum48", "spectrum", "game.rgac"),
                                 ("cpc", "cpc", "game.rgac")):
        sizes[which] = os.path.getsize(os.path.join(ROOT, "z80", folder, built))
    assert sizes["spectrum48"] > sizes["cpc"], (
        f"both machines got the same adventure: {sizes}"
    )


def test_the_table_says_what_each_machine_needs():
    """Every machine in the table has to name a source that is there, or the
    first anyone hears of it is a build that fails."""
    for name, target in TARGETS.items():
        source = os.path.join(ROOT, target.folder, target.source)
        assert os.path.exists(source), f"{name} names {source}, which is not there"
        assert target.media or target.release, f"{name} makes no medium at all"


if __name__ == "__main__":
    import pathlib
    import tempfile

    test_one_command_builds_every_machine(pathlib.Path(tempfile.mkdtemp()))
    print("one command builds every machine")
