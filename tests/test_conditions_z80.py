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
"""The condition machine, run on a real Z80.

The conditions are written in the syntax the adventures use, compiled with the
project's own compiler, built into a binary database and run in the emulator.
What comes back is the state the machine left behind: flags, counters, where
the player ended up and where the objects are.
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

import emulator  # noqa: E402
from regac.binary import Database  # noqa: E402
from regac.conds import compile_block  # noqa: E402

SPECTRUM = os.path.join(ROOT, "z80", "spectrum")
SOURCE = os.path.join(SPECTRUM, "test_conditions.asm")
DATABASE = os.path.join(SPECTRUM, "conditions.rgac")
SNAPSHOT = os.path.join(SPECTRUM, "conditions.sna")
LISTING = os.path.join(SPECTRUM, "conditions.lst")

CARRIED = 255

if pytest is not None:
    needs_tools = pytest.mark.skipif(
        not emulator.available(),
        reason="sjasmplus and ZEsarUX must be in tools/",
    )
else:

    def needs_tools(func):
        return func


def adventure(conditions):
    """A small adventure whose only content is the conditions under test."""
    return {
        "font": [0] * 1024,
        "verbs": {"NORTE": 1, "SUR": 2},
        "nouns": {"COSA": 1},
        "adverbs": {},
        "pronouns": [],
        "messages": {"1": "hola"},
        "objects": {
            "1": {"weight": 7, "initial_loc": 3, "name": "una cosa"},
            "2": {"weight": 1, "initial_loc": CARRIED, "name": "otra cosa"},
            "3": {"weight": 2, "initial_loc": 7, "name": "la tercera"},
        },
        "locations": {
            "1": {"graphic_id": 0, "exits": [], "desc": "el principio"},
            "3": {"graphic_id": 0, "exits": [{"dir": 1, "dest": 7}], "desc": "el medio"},
            "7": {"graphic_id": 0, "exits": [], "desc": "el destino"},
        },
        "hpcs": compile_block(conditions),
        "lpcs": [],
        "lcs": {},
        "model": "SPECTRUM",
        "punctuation": list("\0 .,-!?:"),
        "separators": ["then", "and"],
        "init_loc": 1,
        "no_objs_msg": "nada",
        "gfx": {},
    }


def run(conditions):
    """Run the conditions and give back what the machine ended up holding."""
    database = Database(adventure(conditions))
    with open(DATABASE, "wb") as f:
        f.write(database.build())
    listing = emulator.assemble(SOURCE, listing=LISTING)
    where = {
        name: emulator.label_address(listing, name)
        for name in ("vm_flags", "vm_counters", "vm_location", "obj_loc")
    }
    finished, (flags, counters, location, objects) = emulator.run(
        SNAPSHOT,
        listing,
        reads=[
            (where["vm_flags"], 32),
            (where["vm_counters"], 128),
            (where["vm_location"], 2),
            (where["obj_loc"], 16),
        ],
    )
    assert finished, "the condition machine never reached the end"
    # Markers 0 to 3 are the interpreter's own -- a room described, light,
    # a lamp, and whether to tell the score -- so the first byte is masked
    # off here and the tests below say what the conditions did with the rest.
    # A new game starts with the light on, which is why this matters.
    return {
        "flags": {n for n in range(4, 256) if flags[n >> 3] & (1 << (n & 7))},
        "markers": {n for n in range(4) if flags[0] & (1 << n)},
        "counters": {n: value for n, value in enumerate(counters) if value},
        "location": location[0] | (location[1] << 8),
        "objects": {
            n: objects[n * 2] | (objects[n * 2 + 1] << 8) for n in range(1, 4)
        },
    }


@needs_tools
def test_flags_counters_and_arithmetic():
    state = run([
        "SET 5 SET 6 SET 200 RESE 6 END",
        "42 CSET 3 INCR 3 DECR 3 DECR 3 END",
        "CTR 3 CSET 7 END",
        "1 + 2 CSET 8 END",
        "10 - 4 CSET 9 END",
        "255 CSET 20 INCR 20 END",
        "0 CSET 21 DECR 21 END",
    ])
    assert state["flags"] == {5, 200}, "a flag past the first byte must work too"
    assert state["markers"] == {1}, "a game starts with the light on and nothing else"
    assert state["counters"][3] == 41
    assert state["counters"][7] == 41
    assert state["counters"][8] == 3
    assert state["counters"][9] == 6
    assert state["counters"][20] == 255, "a counter stops at 255 rather than wrapping"
    assert 21 not in state["counters"], "and stops at zero going down"


@needs_tools
def test_tests_and_skipping():
    state = run([
        "IF ( 1 < 2 ) SET 10 END",
        "IF ( 3 > 9 ) SET 11 CSET 99 END",
        "IF ( 5 = 5 ) SET 12 END",
        "IF ( NOT 0 ) SET 13 END",
        "GOTO 7 END",
        "IF ( AT 7 ) SET 14 END",
        "IF ( SET? 10 AND RES? 11 ) SET 15 END",
        "41 CSET 3 IF ( 41 EQU? 3 ) SET 16 END",
    ])
    assert state["flags"] == {10, 12, 13, 14, 15, 16}
    # The condition that failed must leave nothing behind, and the constants
    # inside it are two bytes each, which the skipping has to know.
    assert 99 not in state["counters"]
    assert state["location"] == 7


@needs_tools
def test_objects():
    state = run([
        "GOTO 3 END",
        "IF ( HERE 1 ) SET 20 END",
        "IF ( CARR 2 ) SET 21 END",
        "IF ( AVAI 1 ) SET 22 END",
        "IF ( AVAI 2 ) SET 23 END",
        "IF ( HERE 3 ) SET 24 END",
        "IF ( 3 IN 7 ) SET 25 END",
        "WEIG 1 CSET 30 END",
        "WITH CSET 31 END",
        "1 TO 9 END",
        "2 SWAP 3 END",
        "BRIN 3 END",
        "CONN 1 CSET 32 END",
    ])
    assert state["flags"] == {20, 21, 22, 23, 25}, "object 3 is not in the room"
    assert state["counters"][30] == 7, "the weight comes from the object table"
    assert state["counters"][31] == CARRIED, "WITH stands for what you carry"
    assert state["counters"][32] == 7, "the way out of room 3 leads to room 7"
    assert state["objects"][1] == 9, "TO moves an object"
    assert state["objects"][2] == 7, "SWAP exchanges two objects"
    assert state["objects"][3] == 3, "BRIN fetches one to where you are"


if __name__ == "__main__":
    for check in (test_flags_counters_and_arithmetic, test_tests_and_skipping,
                  test_objects):
        check()
        print(f"{check.__name__}: correcto")
