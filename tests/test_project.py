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

The adventure is the example, built from its source, so that everything but
the last of these runs wherever the two assemblers are, the CI included.  The
last switches a PCW on with what came out, because a file that builds is not
the same as a file that runs, and that one wants ZEsarUX and an adventure of
1986.
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
from regac.binary import S_TEXT, Reader  # noqa: E402
from regac.srcgen import generate  # noqa: E402
from regac.srcparse import parse  # noqa: E402
from regac.project import read as read_project  # noqa: E402
from regac.project import find_assembler, find_nasm  # noqa: E402

EXAMPLE = os.path.join(ROOT, "ejemplo")
ORIGINAL = os.path.join(ROOT, "snapshots", "megacorp2.json")
SCREENS = {"scr": 6912, "cpc": 0x4000, "pcw": 2 * 16 * 720}


def assemblers():
    """Whether regac can build: sjasmplus and NASM, wherever it looks."""
    try:
        find_assembler()
        find_nasm()
    except ProjectError:
        return False
    return True


if pytest is not None:
    needs_assemblers = pytest.mark.skipif(
        not assemblers(), reason="sjasmplus and NASM, in tools/ or on the path",
    )
    needs_tools = pytest.mark.skipif(
        not emulator.available() or not os.path.exists(ORIGINAL),
        reason="ZEsarUX and sjasmplus in tools/, and snapshots/megacorp2.json",
    )
else:

    def needs_tools(func):
        return func

    needs_assemblers = needs_tools


def the_example():
    """The example adventure as a database, read from its own source."""
    with open(os.path.join(EXAMPLE, "faro.gac"), encoding="utf-8") as f:
        return parse(f.read(), "faro.gac", EXAMPLE)


def a_project(where, body, screens=True, adventure=True):
    """A folder with an adventure, its loading screens and a project file.
    Reading a project does not open the adventure, so what only reads one
    goes without."""
    if adventure:
        with open(os.path.join(where, "faro.json"), "w", encoding="utf-8") as f:
            json.dump(the_example(), f)
    if screens:
        for suffix, size in SCREENS.items():
            filler = random.Random(len(suffix))
            with open(os.path.join(where, "carga." + suffix), "wb") as f:
                f.write(bytes(filler.randrange(256) for _ in range(size)))
    path = os.path.join(where, "faro.toml")
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)
    return path


EVERY_MACHINE = """
name   = "faro"
source = "faro.json"
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
        ('name = "x"\nsource = "faro.json"\n', "which machines"),
        ('name = "x"\nsource = "faro.json"\n[targets.oric]\n', "no oric"),
        ('name = "x"\nsource = "faro.json"\n[targets.cpc464]\nbancos = "16k"\n',
         "bancos"),
        ('name = "x"\nsource = "faro.json"\n[targets.cpc464]\nscale = 2\n',
         "cannot draw"),
        ('name = "x"\nsource = "faro.json"\nsalida = "x"\n[targets.cpc464]\n',
         "salida"),
        # as the manual wrote it for a long time, and it fell over in Python
        ('name = "x"\nsource = "faro.json"\n[targets.pcw]\nscale = "2x"\n',
         "one number or two"),
    ):
        path = a_project(where, body, screens=False, adventure=False)
        try:
            read_project(path)
        except ProjectError as e:
            assert complaint in str(e), f"{body!r} complained about {e}"
        else:
            raise AssertionError(f"{body!r} should not have been accepted")


def test_a_scale_is_checked_against_what_the_machine_can_do(tmp_path):
    path = a_project(
        str(tmp_path),
        'name = "x"\nsource = "faro.json"\n[targets.pcw]\nscale = [3, 1]\n',
        screens=False, adventure=False,
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
            f'name = "x"\nsource = "faro.json"\n[targets.pcw]\nscale = {scale}\n',
            screens=False, adventure=False,
        )
        read_project(path)


@needs_assemblers
def test_one_command_builds_every_machine(tmp_path):
    where = str(tmp_path)
    path = a_project(where, EVERY_MACHINE)
    done = make(path)
    assert done.returncode == 0, f"regac make failed:\n{done.stdout}\n{done.stderr}"

    out = os.path.join(where, "salida")
    for folder, name in (
        ("spectrum48", "faro.tap"),
        ("spectrum128", "faro.tap"),
        ("plus3", "faro.dsk"),
        ("cpc464", "faro.cdt"),
        ("cpc6128", "faro.dsk"),
        ("pcw", "faro.dsk"),
    ):
        made = os.path.join(out, folder, name)
        # the example is small: its tape for a 48K Spectrum, with no screen,
        # is some eleven and a half kilobytes
        assert os.path.exists(made), f"{folder}/{name} was never written"
        assert os.path.getsize(made) > 8 * 1024, f"{folder}/{name} is too small"

    # The loading screens really went on: each is its machine's own dump, and
    # a sector of it is enough to look for, because a disk breaks a file up.
    for folder, name, suffix in (
        ("spectrum128", "faro.tap", "scr"),
        ("plus3", "faro.dsk", "scr"),
        ("cpc6128", "faro.dsk", "cpc"),
        ("pcw", "faro.dsk", "pcw"),
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
    with open(os.path.join(out, "spectrum48", "faro.tap"), "rb") as f:
        assert screen[:512] not in f.read(), "a screen turned up uninvited"


@needs_assemblers
def test_it_builds_in_a_copy_and_leaves_the_interpreters_alone(tmp_path):
    """Two builds at once trod on each other when make assembled where regac
    is, and an installation nobody may write in could build nothing: it
    assembles in a copy, and what it leaves there is kept only when asked."""
    where = str(tmp_path)
    path = a_project(where, EVERY_MACHINE)
    tree = [os.path.join(ROOT, folder) for folder in ("z80", "x86", "music")]

    def stamps():
        return {os.path.join(folder, name):
                os.stat(os.path.join(folder, name)).st_mtime_ns
                for top in tree if os.path.isdir(top)
                for folder, _dirs, names in os.walk(top) for name in names}

    before = stamps()
    kept = os.path.join(where, "build")
    done = make(path, "-t", "spectrum128", "--build-dir", kept)
    assert done.returncode == 0, f"regac make failed:\n{done.stdout}\n{done.stderr}"
    assert stamps() == before, "make wrote where regac is installed"
    for left in ("game128.rgac", "banks.inc", "game128.lst", "game128.sym",
                 "game128.tap"):
        assert os.path.exists(os.path.join(kept, "z80", "spectrum", left)), left


@needs_assemblers
def test_a_name_longer_than_a_disk_takes_still_builds(tmp_path):
    """AMSDOS names a file with eight letters and three, and four of the eight
    of 1986 are called with nine -- megacorp1, vajillas2 -- which the 6128's
    disk once refused with a trace.  Its files take the name DOS would, and
    the .dsk keeps the project's."""
    where = str(tmp_path)
    path = a_project(where, 'name = "vajillas1"\nsource = "faro.json"\n'
                            'output = "salida"\n[targets.cpc6128]\n',
                     screens=False)
    done = make(path)
    assert done.returncode == 0, f"regac make failed:\n{done.stdout}\n{done.stderr}"
    with open(os.path.join(where, "salida", "cpc6128", "vajillas1.dsk"),
              "rb") as f:
        disk = f.read()
    for suffix in (b"BAS", b"BIN", b"RES", b"B0 "):
        assert b"VAJILLAS" + suffix in disk, suffix


def test_what_does_not_go_on_a_disk_is_said_and_not_traced():
    from regac.dsk import DiskError, filename

    assert issubclass(DiskError, ValueError)
    try:
        filename("megacorp1.BAS")
    except ValueError:
        pass
    else:
        raise AssertionError("nine letters went on an AMSDOS disk")


@needs_assemblers
def test_only_the_machine_that_was_asked_for(tmp_path):
    where = str(tmp_path)
    path = a_project(where, EVERY_MACHINE)
    done = make(path, "-t", "pcw")
    assert done.returncode == 0, f"regac make failed:\n{done.stdout}\n{done.stderr}"
    out = os.path.join(where, "salida")
    assert os.path.exists(os.path.join(out, "pcw", "faro.dsk"))
    assert not os.path.exists(os.path.join(out, "cpc464")), (
        "it built more than it was told"
    )


@needs_tools
def test_what_it_built_actually_runs(tmp_path):
    """A file that builds is not the same as a file that runs, so one of them
    is switched on: the PCW, which needs no menu and no tape."""
    where = str(tmp_path)
    path = a_project(where, EVERY_MACHINE, adventure=False)
    shutil.copyfile(ORIGINAL, os.path.join(where, "faro.json"))
    assert make(path, "-t", "pcw").returncode == 0
    disk = os.path.join(where, "salida", "pcw", "faro.dsk")

    with open(ORIGINAL, encoding="utf-8") as f:
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
name   = "faro"
source = "faro.gac"
output = "salida"

[targets.spectrum48]

[targets.cpc464]
"""


@needs_assemblers
def test_a_source_is_read_again_for_every_machine(tmp_path):
    """A source may keep some of itself back for some machines, so the one
    command has to read it once for each of them rather than once for all.

    What is looked at is the text of the databases: the same adventure built
    twice, with one message longer on one machine than on the other, cannot
    come out with the same text unless the reading happened once and was
    handed round.  The text and not the whole database, because the rest is
    not the same on two machines anyway: an Amstrad's pictures carry their
    inks in front of them.
    """
    where = str(tmp_path)
    source = generate(the_example())
    # A message that is not the same on the two machines, by a good margin:
    # the first of /MSG, whatever its number.
    at = source.index("\n#", source.index("/MSG")) + 1
    at = source.index("\n", at) + 1
    source = (source[:at] + ".if cpc\nCorto.\n.else\n"
              + "Largo, y mucho mas largo, para que se note en el tamano. " * 8
              + "\n.end\n" + source[at:])
    with open(os.path.join(where, "faro.gac"), "w", encoding="utf-8") as f:
        f.write(source)
    path = os.path.join(where, "faro.toml")
    with open(path, "w", encoding="utf-8") as f:
        f.write(KEPT_BACK)

    # the databases are read where it assembled, which it keeps when told
    kept = os.path.join(where, "build")
    done = make(path, "--build-dir", kept)
    assert done.returncode == 0, f"regac make failed:\n{done.stdout}\n{done.stderr}"
    sizes = {}
    for which, folder, built in (("spectrum48", "spectrum", "game.rgac"),
                                 ("cpc", "cpc", "game.rgac")):
        with open(os.path.join(kept, "z80", folder, built), "rb") as f:
            sizes[which] = len(Reader(f.read()).section(S_TEXT))
    assert sizes["spectrum48"] > sizes["cpc"], (
        f"both machines got the same text: {sizes}"
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
