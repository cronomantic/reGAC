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
"""regac play: a file of orders played, and whether the game ended.

And the two things of the interpreter in Python it found on its first go:
an EXIT in a room's table did not end the game, because the low priority
table ran after it and put the game back on; and the score fell over on an
adventure without the messages that say it."""

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from regac.conds import compile_line  # noqa: E402
from regac.play import orders_of, play  # noqa: E402
from regac.viewer import read_adventure  # noqa: E402

EXAMPLE = os.path.join(ROOT, "ejemplo", "faro.gac")
SOLUTION = os.path.join(ROOT, "ejemplo", "solucion.txt")
WON = "Fin de la aventura"


def regac(*words):
    # what it writes has accents, and a pipe on Windows is not UTF-8 unless
    # asked
    return subprocess.run([sys.executable, "-m", "regac"] + list(words),
                          cwd=ROOT, capture_output=True, text=True,
                          encoding="utf-8",
                          env=dict(os.environ, PYTHONIOENCODING="utf-8"))


def test_the_solution_of_the_example_wins_it():
    done = regac("play", EXAMPLE, SOLUTION, "--expect", WON)
    assert done.returncode == 0, done.stderr
    assert WON in done.stdout


def test_orders_that_run_out_say_so(tmp_path):
    short = tmp_path / "corta.txt"
    short.write_text("COGE LLAVE Y NORTE\n", encoding="utf-8")
    done = regac("play", EXAMPLE, str(short))
    assert done.returncode == 1
    assert "ran out" in done.stderr


def test_winning_has_to_say_what_it_is_asked_to():
    done = regac("play", EXAMPLE, SOLUTION, "--expect", "XYZZY")
    assert done.returncode == 1
    assert "without saying" in done.stderr


def test_what_is_not_an_order():
    assert orders_of("; nada\n\nNORTE\n  ;tampoco\n SUR \n") == ["NORTE", "SUR"]


# MIRA, which is not a way out of the first room: NORTE is, and the player
# would be gone before the room's table was looked at.
LOOK = 14


def test_an_exit_in_a_rooms_table_ends_the_game():
    ddb = read_adventure(EXAMPLE, "spectrum")
    ddb["lcs"]["1"] = compile_line(f"IF ( VERB {LOOK} ) EXIT END", {})
    ended, _ = play(ddb, ["MIRA", "MIRA"])
    assert ended, "an EXIT in the room's table let the game go on"


def test_the_score_without_its_messages_still_comes_out():
    ddb = read_adventure(EXAMPLE, "spectrum")
    for number in ("249", "250", "255"):
        ddb["messages"].pop(number, None)
    ddb["lcs"]["1"] = compile_line(f"IF ( VERB {LOOK} ) EXIT END", {})
    ended, said = play(ddb, ["MIRA"])
    # the score, nought, and the turns straight after it, with nothing
    # between them where the messages would be
    last = said.rstrip().splitlines()[-1]
    assert ended and last.isdigit() and last.startswith("0"), said[-60:]
