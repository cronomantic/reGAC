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
"""What an adventure has that nothing uses, which is usually a mistake.

`regac check` says what is wrong: a number that points at nothing.  This
says what is probably wrong, the other way round: something that is there and
that nothing points at.  A room no way leads to and no GOTO names, an object
nothing can pick up, a word no condition asks for, a message nobody prints,
a picture no room shows, a table no DO runs.  None of it stops an adventure
being built, and some of it is meant -- scenery nobody takes -- so each is a
note, and the author decides.

A number worked out while the game plays -- `MESS ( RAND 3 + 10 )` -- cannot
be followed from here.  Where one of those could be pointing at anything of a
kind, nothing of that kind is said to be unused, and what was not looked at
is said instead: better silent than wrong.
"""

from .check import walked

# The messages the interpreter prints by itself: see doc/gac.md.
OWN_MESSAGES = set(range(240, 256))
CARRIED = 255                   # the room an object in the hand is in


class Note:
    __slots__ = ("kind", "message")

    def __init__(self, kind, message):
        self.kind = kind
        self.message = message

    def __str__(self):
        return f"{self.kind}: {self.message}"


def tables_of(ddb):
    """Every table of conditions, with what to call it."""
    yield "the high priority conditions", ddb.get("hpcs") or []
    yield "the low priority conditions", ddb.get("lpcs") or []
    for room, code in (ddb.get("lcs") or {}).items():
        yield f"room {room}", code
    for proc, code in (ddb.get("procs") or {}).items():
        yield f"procedure {proc}", code


def asked_for(ddb):
    """Every opcode with a constant, and every opcode whose number is worked
    out while the game plays: {name: set of constants}, {name}.  And the
    objects that come to hand some other way than GET: a SWAP puts one where
    the other was, which may be the hand, and a TO may send one there."""
    constant, worked_out, to_hand = {}, set(), set()
    for _, code in tables_of(ddb):
        for op, taken in walked(code):
            for value in taken:
                if value is None:
                    worked_out.add(op.name)
                else:
                    constant.setdefault(op.name, set()).add(value)
            if op.name == "SWAP":
                to_hand.update(v for v in taken if v is not None)
            elif op.name == "TO" and taken[1] in (CARRIED, None)                     and taken[0] is not None:
                to_hand.add(taken[0])
    return constant, worked_out, to_hand


def keys(table):
    return {int(k) for k in (table or {})}


def notes_of(ddb):
    """Everything worth a look, in the order an author would go through it."""
    notes = []
    constant, worked_out, to_hand = asked_for(ddb)
    rooms = keys(ddb.get("locations"))
    objects = keys(ddb.get("objects"))
    used = {name: constant.get(name, set()) for name in
            ("GOTO", "GET", "VERB", "NOUN", "ADVE", "MESS", "DO", "OBJ")}

    # Rooms no way leads to and no GOTO names.
    start = int(ddb.get("init_loc", 0))
    reached = {start}
    ways = {}
    for key, room in (ddb.get("locations") or {}).items():
        ways[int(key)] = [int(w["dest"]) for w in room.get("exits", [])]
    frontier = [start] + sorted(used["GOTO"] & rooms)
    reached.update(frontier)
    while frontier:
        room = frontier.pop()
        for dest in ways.get(room, []):
            if dest not in reached:
                reached.add(dest)
                frontier.append(dest)
    if "GOTO" in worked_out:
        notes.append(Note("rooms", "a GOTO works its room out while the game "
                          "plays, so which rooms are reached is not looked at"))
    else:
        for room in sorted(rooms - reached):
            notes.append(Note("rooms", f"room {room}: no way out leads here "
                              f"and no GOTO names it"))

    # Objects nothing can pick up: no GET names one, and a GET of a noun
    # typed takes the object with that noun's number.  One that a SWAP or a
    # TO may bring to hand is not said.
    nouns = set((ddb.get("nouns") or {}).values())
    takes_a_noun = "GET" in worked_out
    for number in sorted(objects):
        start_at = int((ddb.get("objects") or {})[str(number)]
                       .get("initial_loc", 0))
        if number in used["GET"] or number in to_hand or start_at == CARRIED:
            continue
        if takes_a_noun and number in nouns:
            continue
        why = ("and no noun has its number for a GET of what is typed"
               if takes_a_noun else "and no GET names it")
        notes.append(Note("objects", f"object {number} cannot be picked up: "
                          f"it does not start carried, {why}"))

    # Words no condition asks for.  A verb is also asked for by being a way
    # out, and a noun by being an object's number when a GET, a DROP or
    # another takes the noun typed.
    exits = {w["dir"] for room in (ddb.get("locations") or {}).values()
             for w in room.get("exits", [])}
    for kind, table, op, also in (
            ("verb", "verbs", "VERB", exits),
            ("noun", "nouns", "NOUN", objects if worked_out & {
                "GET", "DROP", "OBJ", "HERE", "CARR", "AVAI", "BRIN",
                "FIND", "SWAP", "TO", "IN", "WEIG"} else set()),
            ("adverb", "adverbs", "ADVE", set())):
        if op in worked_out or (kind == "verb" and "VBNO" in constant_ops(ddb)):
            notes.append(Note("words", f"a {op} works its word out while the "
                              f"game plays, so no {kind} is said to be unused"))
            continue
        for word, number in sorted((ddb.get(table) or {}).items(),
                                   key=lambda w: (w[1], w[0])):
            if number and number not in used[op] and number not in also:
                notes.append(Note("words", f"the {kind} {word} ({number}): no "
                                  f"condition asks for it"))

    # Messages nobody prints: MESS names them, and so does nothing else.
    if "MESS" in worked_out:
        notes.append(Note("messages", "a MESS works its message out while the "
                          "game plays, so which are printed is not looked at"))
    else:
        for number in sorted(keys(ddb.get("messages")) - used["MESS"]
                             - OWN_MESSAGES):
            notes.append(Note("messages", f"message {number}: nothing prints "
                              f"it"))

    # Pictures no room shows and no picture calls.
    pictures = keys(ddb.get("gfx"))
    shown = {int(room.get("graphic_id", 0))
             for room in (ddb.get("locations") or {}).values()}
    for drawing in (ddb.get("gfx") or {}).values():
        shown.update(int(order[1]) for order in drawing if order[0] == "CALL")
    for number in sorted(pictures - shown):
        notes.append(Note("pictures", f"picture {number}: no room shows it "
                          f"and no picture calls it"))

    # Tables no DO runs.
    procs = keys(ddb.get("procs"))
    if "DO" in worked_out:
        if procs:
            notes.append(Note("procedures", "a DO works its table out while "
                              "the game plays, so which run is not looked at"))
    else:
        for number in sorted(procs - used["DO"]):
            notes.append(Note("procedures", f"procedure {number}: no DO runs "
                              f"it"))
    return notes


def constant_ops(ddb):
    """The names of every opcode an adventure uses at all."""
    names = set()
    for _, code in tables_of(ddb):
        names.update(step[0] for step in code)
    return names
