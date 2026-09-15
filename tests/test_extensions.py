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
"""Names for numbers, and files taken into other files.

`.def PUERTA_ABIERTA 5` is the one that changes how an adventure reads: a
source written with it says what it means instead of what it counts, and the
number is still what reaches the machine.  It stands wherever a number would
-- in a condition, in a connection, as the number of a message -- because a
number is a number wherever it is written.

`.include "comun.gac"` is the other half of the same idea: the names, the
vocabulary and the low priority conditions two parts of one adventure share
are written once.  GAC itself had this, in its way: the QS.ADV file it started
every new adventure from.

What both of them must not do is lose the author.  A mistake inside a file
that was included says that file and its own line number, not a line of the
one that took it in.
"""

import os
import sys

try:
    import pytest
except ImportError:
    pytest = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from regac.srcparse import SourceError, parse  # noqa: E402

COMMON = """; what the two parts of this adventure share
.def PUERTA_ABIERTA   5
.def BIENVENIDA      14
.def CALLE            7

/VOC
NORTE                      1  verb
SUR                        2  verb
"""

ADVENTURE = """/CTL
model    SPECTRUM
start    CALLE
width    32

.include "comun.gac"

/MSG
#BIENVENIDA
Bienvenido a la aventura.

/LOC #CALLE  gfx=0
Una calle.
  /CONN
    NORTE   PUERTA_ABIERTA
  /LOCAL
    IF ( SET? PUERTA_ABIERTA ) MESS BIENVENIDA END

/HIGH
IF ( AT CALLE ) SET PUERTA_ABIERTA END
"""


def written(folder, name, text):
    path = os.path.join(str(folder), name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


def built(folder, source=ADVENTURE, common=COMMON):
    if common is not None:
        written(folder, "comun.gac", common)
    return parse(source, "partida.gac", folder=str(folder), machine="cpc")


def refused(folder, source, common=COMMON):
    try:
        built(folder, source, common)
    except SourceError as e:
        return str(e)
    raise AssertionError(f"this should not have been read: {source!r}")


def test_a_name_stands_wherever_a_number_would(tmp_path):
    ddb = built(tmp_path)
    assert ddb["init_loc"] == 7, "in the control section"
    assert 14 in ddb["messages"], "as the number of a message"
    assert 7 in ddb["locations"], "as the number of a room"
    assert ddb["locations"][7]["exits"] == [{"dir": 1, "dest": 5}], (
        "as where a way out goes"
    )
    assert ["PUSH", 5] in ddb["hpcs"], "and in a condition"
    assert ["PUSH", 14] in ddb["lcs"][7], "and in a local one"


def test_what_is_included_is_there(tmp_path):
    ddb = built(tmp_path)
    assert ddb["verbs"] == {"NORTE": 1, "SUR": 2}, (
        "the vocabulary of the included file is the adventure's"
    )


def test_a_mistake_in_an_included_file_says_that_file(tmp_path):
    said = refused(tmp_path, '/CTL\nmodel SPECTRUM\n.include "comun.gac"\n',
                   "/VOC\nNORTE   1  verbo\n")
    assert said.startswith("comun.gac:2: "), said
    assert "did you mean verb?" in said


def test_a_file_that_takes_itself_in_is_stopped(tmp_path):
    written(tmp_path, "bucle.gac", '.include "bucle.gac"\n')
    said = refused(tmp_path,
                   '/CTL\nmodel SPECTRUM\n.include "bucle.gac"\n', None)
    assert "included from itself" in said, said


def test_a_file_that_is_not_there_says_so(tmp_path):
    said = refused(tmp_path,
                   '/CTL\nmodel SPECTRUM\n.include "noexiste.gac"\n', None)
    assert "noexiste.gac cannot be read" in said, said


def test_what_a_def_may_not_be(tmp_path):
    for source, wanted in (
        (".def 9PUERTA 5\n", "is not a name"),
        (".def MESS 5\n", "is a word of the language already"),
        (".def LINE 5\n", "is a word of the language already"),
        (".def PUERTA cinco\n", "neither a number nor a name"),
        (".def PUERTA\n", ".def gives a name to a number"),
    ):
        said = refused(tmp_path, "/CTL\nmodel SPECTRUM\n" + source, None)
        assert wanted in said, f"{source!r}: {said}"


def test_a_name_nobody_gave_a_number_is_a_mistake(tmp_path):
    said = refused(
        tmp_path,
        "/CTL\nmodel SPECTRUM\n/HIGH\nIF ( SET? PUERTA ) LOOK END\n", None)
    assert "unknown word 'PUERTA'" in said, said

    # And one that is nearly a name that was given one says which.
    said = refused(
        tmp_path,
        "/CTL\nmodel SPECTRUM\n.def PUERTA 5\n/LOC #PUERTAA gfx=0\nUna calle.\n",
        None)
    assert "did you mean PUERTA?" in said, said


def test_a_name_may_be_given_to_another_name(tmp_path):
    ddb = built(
        tmp_path,
        "/CTL\nmodel SPECTRUM\n.def PUERTA 5\n.def ENTRADA PUERTA\n"
        "/HIGH\nSET ENTRADA END\n", None)
    assert ["PUSH", 5] in ddb["hpcs"]


def test_a_name_may_be_hexadecimal(tmp_path):
    ddb = built(tmp_path,
                "/CTL\nmodel SPECTRUM\n.def TINTA 0x0A\n/HIGH\nPRIN TINTA END\n",
                None)
    assert ["PUSH", 10] in ddb["hpcs"]


def test_a_def_can_be_kept_back_for_a_machine(tmp_path):
    """The two directives are read in the same pass and in order, so a name
    may be one thing on one machine and another on another."""
    source = ("/CTL\nmodel SPECTRUM\n"
              ".if amstrad\n.def TINTA 3\n.else\n.def TINTA 6\n.end\n"
              "/HIGH\nPRIN TINTA END\n")
    for machine, wanted in (("cpc", 3), ("spectrum48", 6), ("msx", 6)):
        ddb = parse(source, "partida.gac", folder=str(tmp_path),
                    machine=machine)
        assert ["PUSH", wanted] in ddb["hpcs"], machine


if __name__ == "__main__":
    import tempfile
    for name, test in sorted(globals().items()):
        if name.startswith("test_"):
            test(tempfile.mkdtemp())
            print(name[5:].replace("_", " "))
