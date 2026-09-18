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
"""Whether an adventure makes sense, which the compiler cannot tell.

`MESS 99` compiles perfectly whether or not there is a message ninety nine.
So does a way out to a room nobody wrote, an object that starts in a place
that is not there, or the third tune of an adventure with two.  What the
player gets is a blank, a locked room or silence, with nothing to say why --
and that is what this looks for.

The eight decompiled adventures are part of the test, because they are what
the language really looks like.  One of them turns out to have a fault of its
own, which is the best thing that could have happened to a checker: Los
pajaros de Bangkok says MESS 130 in a room of its first part and the message
was never written.  It has been there since 1987.
"""

import json
import os
import sys

try:
    import pytest
except ImportError:
    pytest = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from regac.check import problems_of  # noqa: E402
from regac.conds import compile_block  # noqa: E402
from test_conditions_z80 import adventure  # noqa: E402

SNAPSHOTS = os.path.join(ROOT, "snapshots")


def of(conditions=(), **changes):
    """A small adventure, with whatever is wrong with it done on purpose."""
    ddb = adventure(list(conditions))
    # The small one has none of the messages an interpreter says for itself,
    # and that is not what is being looked at here.
    ddb["messages"].update({str(n): "." for n in
                            (240, 241, 242, 243, 244, 246, 247, 248, 251, 253,
                             254)})
    # and a letter of a font, because an adventure with none of it is a
    # warning of its own and never what these are looking at
    ddb["font"] = [0] * 8 + [0x18, 0x24, 0x42, 0x7E, 0x42, 0x42, 0x42, 0x00]
    ddb.update(changes)
    return ddb


def faults(ddb):
    return [str(p) for p in problems_of(ddb) if p.fault]


def warnings(ddb):
    return [str(p) for p in problems_of(ddb) if not p.fault]


def test_a_sound_adventure_says_nothing():
    assert problems_of(of(["SET 1 END"])) == []


def test_a_message_that_is_not_there():
    said = faults(of(["MESS 99 END"]))
    assert said and "MESS 99" in said[0] and "no message 99" in said[0], said


def test_a_room_that_is_not_there():
    assert any("no room 42" in s for s in faults(of(["GOTO 42 END"])))
    # Nowhere and carried are rooms in the language's own sense, and mean what
    # they always meant: an object put away, and an object in a pocket.
    assert not faults(of(["1 TO 0 END", "2 TO 255 END"]))


def test_an_object_that_is_not_there():
    assert any("no object 9" in s for s in faults(of(["GET 9 END"])))


def test_a_counter_the_interpreter_has_not_got():
    assert any("counters" in s for s in faults(of(["7 CSET 200 END"])))
    assert not faults(of(["7 CSET 127 END"]))


def test_a_word_of_the_vocabulary_nobody_has():
    said = warnings(of(["IF ( VERB 77 ) LOOK END"]))
    assert any("VERB 77" in s for s in said), said
    # Nought is what the parser says when it knew none of them, so asking for
    # it is a fair question and not a mistake.
    assert not warnings(of(["IF ( VERB 0 ) LOOK END"]))


def test_what_is_worked_out_while_it_plays_is_let_alone():
    """`MESS ( CTR 3 )` says a different message every time, so there is
    nothing to check and nothing should be said."""
    assert not problems_of(of(["MESS ( CTR 3 ) END"]))


def test_where_the_player_starts():
    assert any("starts in room 99" in s for s in faults(of(init_loc=99)))


def test_where_a_way_out_goes():
    ddb = of()
    ddb["locations"]["1"]["exits"] = [{"dir": 1, "dest": 77}]
    assert any("goes to room 77" in s for s in faults(ddb))


def test_where_an_object_starts():
    ddb = of()
    ddb["objects"]["1"]["initial_loc"] = 88
    assert any("starts in room 88" in s for s in faults(ddb))


def test_a_picture_that_is_not_there():
    ddb = of()
    ddb["locations"]["1"]["graphic_id"] = 12
    assert any("picture 12" in s for s in faults(ddb))
    # and one picture calling another
    ddb = of()
    ddb["gfx"] = {"1": [["CALL", 5]]}
    assert any("calls picture 5" in s for s in faults(ddb))


def test_a_tune_the_adventure_has_not_got():
    ddb = of(["MUSIC 2 END"])
    ddb["music"] = [{"file": "una.asm", "subsong": 0}]
    assert any("MUSIC 2" in s and "1 tunes" in s for s in faults(ddb))
    ddb["music"] = [{"file": "una.asm", "subsong": 0},
                    {"file": "otra.asm", "subsong": 0},
                    {"file": "tercera.asm", "subsong": 0}]
    assert not faults(ddb)
    # And an adventure with no music at all saying MUSIC anything.
    assert any("no music at all" in s for s in faults(of(["MUSIC 0 END"])))


def test_a_noise_the_adventure_has_not_got():
    """A bank exported from the tracker is assembly and nothing here can count
    what is in it, but an adventure that says its own noises can be counted."""
    ddb = of(["SOUND 3 END"])
    ddb["sounds"] = [[100, 40, -1], [30, 90, 2]]
    assert any("SOUND 3" in s and "2 noises" in s for s in faults(ddb))
    ddb["sounds"].append([200, 60, 0])
    assert not faults(ddb)
    # And with nothing said, nothing is claimed: the bank may hold anything.
    assert not faults(of(["SOUND 9 END"]))
    assert any("numbered from one" in s for s in faults(of(["SOUND 0 END"])))


def test_the_messages_the_interpreter_says_for_itself():
    ddb = of()
    del ddb["messages"]["240"]
    del ddb["messages"]["251"]
    assert any("message 240 is missing" in s for s in faults(ddb)), (
        "the one it asks with is not optional"
    )
    assert any("message 251 is missing" in s for s in warnings(ddb)), (
        "the one for the dark is, because an adventure may have no dark in it"
    )


def test_two_words_that_are_one_word():
    """The parser takes the marks off what it compares, so LAMPARA and lampara
    are the same word to it -- and if they answer to different numbers, only
    the first can ever be reached."""
    ddb = of()
    ddb["nouns"] = {"LAMPARA": 5, "lámpara": 6}
    said = warnings(ddb)
    assert any("same word" in s for s in said), said
    # The same word with the same number is a synonym, which is the point.
    ddb["nouns"] = {"LAMPARA": 5, "lámpara": 5}
    assert not any("same word" in s for s in warnings(ddb))


def a_decompiled_adventure():
    return any(name.endswith(".json") for name in os.listdir(SNAPSHOTS))         if os.path.isdir(SNAPSHOTS) else False


@pytest.mark.skipif(pytest is not None and not a_decompiled_adventure(),
                    reason="no decompiled adventure in snapshots/")     if pytest is not None else (lambda f: f)
def test_the_eight_adventures_are_looked_at_too():
    """What the language really looks like is in the eight that were
    decompiled, and a checker that they cannot pass is a checker that says the
    wrong things."""
    counted = {}
    for name in sorted(os.listdir(SNAPSHOTS)):
        if not name.endswith(".json"):
            continue
        with open(os.path.join(SNAPSHOTS, name), encoding="utf-8") as f:
            ddb = json.load(f)
        counted[name] = len(faults(ddb))
    assert counted, "no decompiled adventure to look at"
    # Two of them really are wrong, and the same way: a message that was
    # never written.  Everything else has to come out clean.
    wrong = {name: n for name, n in counted.items() if n}
    assert set(wrong) <= {"Bangkok1.json", "Bangkok2.json"}, counted
    for name in wrong:
        with open(os.path.join(SNAPSHOTS, name), encoding="utf-8") as f:
            said = faults(json.load(f))
        assert all("there is no message" in s for s in said), said


if __name__ == "__main__":
    for name, test in sorted(globals().items()):
        if name.startswith("test_"):
            test()
            print(name[5:].replace("_", " "))
