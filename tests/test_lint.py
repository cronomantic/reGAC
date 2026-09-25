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
"""regac lint: what an adventure has that nothing uses."""

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from regac.conds import compile_line  # noqa: E402
from regac.lint import notes_of  # noqa: E402


def an_adventure(low=(), **more):
    """Two rooms, a way between them, an object, a word of each kind and two
    messages: everything used by the conditions given, or not."""
    code = []
    for line in low:
        code += compile_line(line, {})
    ddb = {
        "verbs": {"NORTE": 1, "COGE": 2, "SALTA": 3},
        "nouns": {"LLAVE": 1, "PUERTA": 5},
        "adverbs": {"RAPIDO": 1},
        "messages": {"1": "UNO", "2": "DOS", "240": ">"},
        "objects": {"1": {"weight": 1, "initial_loc": 1, "name": "LLAVE"}},
        "locations": {"1": {"graphic_id": 1, "exits": [{"dir": 1, "dest": 2}],
                            "desc": "UNO"},
                      "2": {"graphic_id": 0, "exits": [], "desc": "DOS"}},
        "gfx": {"1": [["CALL", 2]], "2": [], "3": []},
        "hpcs": [], "lpcs": code, "lcs": {}, "init_loc": 1,
    }
    ddb.update(more)
    return ddb


def said(ddb):
    return [str(note) for note in notes_of(ddb)]


def test_what_nothing_uses_is_said():
    notes = said(an_adventure())
    for wanted in ("object 1 cannot be picked up", "the verb COGE (2)",
                   "the noun LLAVE (1)", "the adverb RAPIDO (1)",
                   "message 1: nothing prints it", "picture 3: no room"):
        assert any(wanted in note for note in notes), (wanted, notes)
    # a verb that is a way out is used, and the interpreter's messages are
    assert not any("NORTE" in note for note in notes), notes
    assert not any("message 240" in note for note in notes), notes
    # a picture a room shows, or another calls, is used
    assert not any("picture 1" in n or "picture 2" in n for n in notes), notes


def test_what_is_used_is_not():
    notes = said(an_adventure(low=[
        "IF ( VERB 2 AND NOUN 1 AND ADVE 1 ) GET 1 MESS 1 MESS 2 END",
        "IF ( VERB 3 ) WAIT END"]))
    assert not any("object 1" in n or "COGE" in n or "LLAVE" in n
                   or "RAPIDO" in n or "message 1" in n or "message 2" in n
                   for n in notes), notes


def test_a_room_no_way_leads_to_and_no_goto_names():
    ddb = an_adventure()
    ddb["locations"]["3"] = {"graphic_id": 0, "exits": [], "desc": "TRES"}
    assert any("room 3: no way out" in n for n in said(ddb))
    ddb["lpcs"] = compile_line("IF ( VERB 3 ) GOTO 3 END", {})
    assert not any("room 3" in n for n in said(ddb))


def test_a_get_of_what_is_typed_takes_the_object_with_its_nouns_number():
    notes = said(an_adventure(low=["IF ( VERB 2 ) GET NO1 END"]))
    assert not any("object 1" in n for n in notes), notes


def test_what_a_swap_brings_to_hand_can_be_had():
    ddb = an_adventure(low=["IF ( VERB 3 ) 2 SWAP 1 END"])
    assert not any("object 1" in n for n in said(ddb))


def test_a_number_worked_out_while_playing_is_not_guessed_at():
    notes = said(an_adventure(low=["IF ( VERB 3 ) MESS ( RAND 2 ) END"]))
    assert not any("nothing prints it" in n for n in notes), notes
    assert any("works its message out" in n for n in notes), notes


def test_a_table_no_do_runs():
    ddb = an_adventure(procs={"4": compile_line("IF ( AT 1 ) WAIT END", {})})
    assert any("procedure 4: no DO runs it" in n for n in said(ddb))


def test_it_runs_on_the_example():
    out = subprocess.run([sys.executable, "-m", "regac", "lint",
                          os.path.join(ROOT, "ejemplo", "faro.gac")],
                         cwd=ROOT, check=True, capture_output=True, text=True)
    assert out.stdout.strip()
