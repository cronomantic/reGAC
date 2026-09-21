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
"""One adventure, and the lines each machine is to have of it.

`.if cpc msx` ... `.else` ... `.end` keeps lines back, and it is resolved when
the source is read rather than when the adventure is played: what a machine is
not to have never reaches its database.  That is the point of it -- on the
machines where room runs out first, a conditional the interpreter had to obey
would cost more than it saved.

What is checked here is that every kind of line can be kept back, not only
text: a whole section, an entry, a condition of the table, a word of the
vocabulary.  The preprocessor knows nothing about any of them -- it works on
lines before anything else has looked at them -- and that is exactly why it
has to be shown working on each.
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

from regac.srcparse import SourceError, for_machine, parse  # noqa: E402

SOURCE = """/CTL
model    SPECTRUM
start    1
width    32

/VOC
NORTE                      1  verb
.if amstrad
JOYSTICK                   9  noun
.end

/MSG
#1
Un ruido seco\\
.if cpc msx
 y nada mas.
.else
 y la pantalla parpadea.
.end
#2
Siempre.

/OBJ
#1  weight=1  start=nowhere
una cosa

/LOC #1  gfx=0
El principio.
  /LOCAL
    IF ( VERB 1 ) MESS 2 END
.if spectrum
    IF ( VERB 1 ) MESS 1 END
.end

/HIGH
.if next
QUIET END
.end
LOOK END
"""


def read(machine):
    return parse(SOURCE, "test.gac", machine=machine)


def test_the_text_a_machine_gets():
    assert read("cpc")["messages"][1] == "Un ruido seco y nada mas."
    assert read("msx")["messages"][1] == "Un ruido seco y nada mas."
    assert read("spectrum48")["messages"][1] == (
        "Un ruido seco y la pantalla parpadea."
    )
    # And what is outside the conditional is everybody's.
    for machine in ("cpc", "msx", "spectrum48", "next", "pcw"):
        assert read(machine)["messages"][2] == "Siempre."


def test_a_family_takes_in_its_machines():
    """`amstrad` is the CPC and the PCW, `spectrum` the three Sinclairs: a
    line for a family is a line for each of them and for nobody else."""
    for machine in ("cpc", "pcw"):
        assert "JOYSTICK" in read(machine)["nouns"], machine
    for machine in ("spectrum48", "msx", "next"):
        assert "JOYSTICK" not in read(machine)["nouns"], machine
    for machine in ("spectrum48", "spectrum128", "plus3"):
        assert len(read(machine)["lcs"][1]) > len(read("cpc")["lcs"][1]), (
            f"{machine} should have the condition kept for its family"
        )


def test_a_line_of_the_tables_can_be_kept_back():
    """A condition is a line like any other, so it goes in or it does not."""
    assert len(read("next")["hpcs"]) > len(read("cpc")["hpcs"])
    assert read("cpc")["hpcs"], "what is outside the conditional stays"


def test_the_line_numbers_do_not_move():
    """What is kept back is blanked and not taken out, so that an error three
    sections further on still says the line the author is looking at."""
    for machine in ("cpc", "spectrum48"):
        assert len(for_machine(SOURCE, machine).splitlines()) == \
            len(SOURCE.splitlines()), machine


def test_a_source_that_keeps_lines_back_needs_a_machine():
    """Reading it for nobody would quietly give an adventure that is neither
    one thing nor the other, so it is refused instead."""
    try:
        parse(SOURCE, "test.gac")
    except SourceError as e:
        assert "-m" in str(e), e
    else:
        raise AssertionError("a source with conditionals was read for nobody")


def test_a_machine_that_does_not_exist_is_a_mistake():
    bad = SOURCE.replace(".if cpc msx", ".if cpcc")
    try:
        parse(bad, "test.gac", machine="cpc")
    except SourceError as e:
        assert "cpcc" in str(e) and "cpc" in str(e)
    else:
        raise AssertionError("a typo in a machine name went through")


def test_what_is_not_balanced_is_said():
    for broken, said in (
        (SOURCE.replace(".end\nLOOK END", "LOOK END"), "never ended"),
        (SOURCE.replace(".if next", ".else"), ".else without .if"),
        (SOURCE.replace(".if next", ".end"), ".end without .if"),
        (SOURCE.replace(".if next", ".if"), ".if what?"),
    ):
        try:
            parse(broken, "test.gac", machine="next")
        except SourceError as e:
            assert said in str(e), f"{said!r} not in {e}"
        else:
            raise AssertionError(f"{said}: went through")


def test_one_inside_another():
    source = """/CTL
model SPECTRUM
/MSG
#1
.if spectrum
.if plus3
De disco.
.else
De cinta.
.end
.else
De donde sea.
.end
"""
    assert parse(source, machine="plus3")["messages"][1] == "De disco."
    assert parse(source, machine="spectrum48")["messages"][1] == "De cinta."
    assert parse(source, machine="cpc")["messages"][1] == "De donde sea."


def test_a_source_without_any_is_the_same_for_everybody():
    plain = """/CTL
model SPECTRUM
/MSG
#1
Lo mismo en todas partes.
"""
    for machine in (None, "cpc", "next"):
        assert parse(plain, machine=machine)["messages"][1] == \
            "Lo mismo en todas partes."


if __name__ == "__main__":
    for name, test in sorted(globals().items()):
        if name.startswith("test_"):
            test()
            print(name[5:].replace("_", " "))
