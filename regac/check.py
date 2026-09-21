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
"""Whether an adventure makes sense, which is not the same as whether it
compiles.

A source that compiles can still be wrong in the way that matters: it can say
MESS 99 where there is no message ninety nine, send the player to a room that
was never written, give an object to a place that is not there, or make a
noise the adventure never described.  None of that stops a build.  All of it
stops a game, and on a real machine what the player sees is a blank, a locked
room or silence -- with nothing to say why.

So this reads the adventure and follows every number that points at something,
which is most of them: the opcode table already says what each one means, so
there is one walk and not twenty checks.  What it cannot know it says nothing
about; what it is unsure of it calls a warning; what cannot be anything but a
mistake it calls a fault.

The numbers the interpreter itself uses are checked as well.  An adventure
that has no message 240 has nothing to ask the player with, and neither the
compiler nor the machine will say so.
"""

from .gfx import PICTURE_BOTTOM, PICTURE_TOP
from .opcodes import ADVERB, BY_NAME, CTR, FLAG, MSG, NOUN, OBJ, ROOM, VERB
from .text import typed

COUNTERS = 128                  # what the interpreters have, in every machine
CARRIED = 255                   # where an object the player holds lives
NOWHERE = 0

# What the interpreter says for itself, and cannot do without.  The numbers
# are the original's and are the same on every machine: see z80/common.
NEEDED = {
    240: "to ask the player for an order",
    241: "to say an order cannot be done",
    242: "to say an order was not understood",
}
# And the ones it only reaches for in certain circumstances, which an
# adventure may honestly not want.
WANTED = {
    243: "to ask for a key",
    244: "to ask whether the player is sure",
    246: "to say the player has not got it",
    247: "to say there is nothing like that here",
    248: "to say the player is carrying too much",
    251: "to say it is dark",
    253: "to introduce what can be seen",
    254: "to say it is done",
}


class Problem:
    """Something that is wrong, or probably wrong, and where."""

    __slots__ = ("where", "message", "fault")

    def __init__(self, where, message, fault=True):
        self.where = where              # the part of the adventure it is in
        self.message = message
        self.fault = fault              # or only a warning

    def __str__(self):
        mark = "" if self.fault else "warning: "
        return f"{mark}{self.where}: {self.message}"


def ys_of(command):
    """The y of every point a drawing order names that has to be in the frame.

    Not every number that looks like a y is one: the second pair of an
    ELLIPSE is where its radii come from and not a place, so it falls outside
    the frame as a matter of course -- the example adventure's own lighthouse
    does it five times over, which is how this was found.  A fill is left out
    too, because what the original does with a seed outside has not been
    asked of it.
    """
    name = command[0]
    if name == "PLOT":
        return command[2:3]
    if name in ("LINE", "RECT"):
        return command[2:3] + command[4:5]
    return []


def numbered(table):
    """The keys of a table as numbers, whichever way they were written.

    A decompiled adventure has them as strings, because JSON has no other
    kind of key; one read from a source has them as numbers.
    """
    return {int(key) for key in table}


def walked(code):
    """Every opcode of a condition table with the constants it was given.

    The bytecode is a stack language, so an opcode's operands are whatever was
    pushed before it.  What is pushed by another opcode rather than written as
    a number is not a constant and comes back as None: nothing can be said
    about `MESS ( CTR 3 )`, and nothing should be.
    """
    stack = []
    for instruction in code:
        name = instruction[0]
        if name == "PUSH":
            stack.append(instruction[1])
            continue
        op = BY_NAME.get(name)
        if op is None:                  # END, IF and the rest of the frame
            stack.clear() if name == "END" else None
            continue
        taken = []
        for _ in range(op.argc):
            taken.append(stack.pop() if stack else None)
        taken.reverse()
        yield op, taken
        if op.pushes:
            stack.append(None)


def follow(problems, where, code, ddb):
    """Check the numbers of one condition table against the adventure."""
    messages = numbered(ddb.get("messages", {}))
    rooms = numbered(ddb.get("locations", {}))
    objects = numbered(ddb.get("objects", {}))
    # Nought is not a word of the vocabulary but what the parser says when it
    # knew none of them, so a condition may well ask for it.
    words = {
        VERB: set(ddb.get("verbs", {}).values()),
        NOUN: set(ddb.get("nouns", {}).values()),
        ADVERB: set(ddb.get("adverbs", {}).values()),
    }
    noises = len(ddb.get("sounds") or [])

    for op, taken in walked(code):
        for kind, value in zip(op.argk, taken):
            if value is None:           # worked out while it plays
                continue
            if kind is MSG and value not in messages:
                problems.append(Problem(
                    where, f"{op.name} {value}, and there is no message {value}"))
            elif kind is ROOM and value not in rooms and value not in (NOWHERE,
                                                                       CARRIED):
                problems.append(Problem(
                    where, f"{op.name} {value}, and there is no room {value}"))
            elif kind is OBJ and value not in objects:
                problems.append(Problem(
                    where, f"{op.name} {value}, and there is no object {value}"))
            elif kind is CTR and not 0 <= value < COUNTERS:
                problems.append(Problem(
                    where, f"{op.name} {value}, and there are {COUNTERS} "
                           f"counters, numbered 0 to {COUNTERS - 1}"))
            elif kind is FLAG and not 0 <= value <= 255:
                problems.append(Problem(
                    where, f"{op.name} {value}, and there are 256 flags, "
                           f"numbered 0 to 255"))
            elif kind in words and value and value not in words[kind]:
                problems.append(Problem(
                    where, f"{op.name} {value}, and no word of the vocabulary"
                           f" has that number", fault=False))
        if op.name == "SOUND" and taken[0] is not None:
            if taken[0] < 1:
                problems.append(Problem(
                    where, "SOUND 0, and effects are numbered from one"))
            elif noises and taken[0] > noises:
                # Only when the adventure says what its noises are: a bank
                # exported from the tracker is assembly and nothing here can
                # count what is in it.
                problems.append(Problem(
                    where, f"SOUND {taken[0]}, and this adventure says what "
                           f"{noises} noises it has"))


def problems_of(ddb):
    """Everything worth saying about an adventure, faults first."""
    found = []
    messages = numbered(ddb.get("messages", {}))
    rooms = numbered(ddb.get("locations", {}))
    pictures = numbered(ddb.get("gfx", {}))

    follow(found, "the high priority conditions", ddb.get("hpcs", []), ddb)
    follow(found, "the low priority conditions", ddb.get("lpcs", []), ddb)
    for lid, code in (ddb.get("lcs") or {}).items():
        follow(found, f"the local conditions of room {lid}", code, ddb)

    # Where the player starts, and where every way out goes.
    start = ddb.get("init_loc")
    if start is not None and int(start) not in rooms:
        found.append(Problem("the control section",
                             f"the player starts in room {start}, which is not "
                             f"there"))
    for lid, room in (ddb.get("locations") or {}).items():
        for way in room.get("exits", []):
            if way["dest"] not in rooms:
                found.append(Problem(
                    f"room {lid}", f"a way out goes to room {way['dest']}, "
                                   f"which is not there"))
        picture = room.get("graphic_id") or 0
        if picture and picture not in pictures:
            found.append(Problem(
                f"room {lid}", f"it shows picture {picture}, which is not "
                               f"there"))

    # Where every object starts.
    for oid, obj in (ddb.get("objects") or {}).items():
        start = obj.get("initial_loc", NOWHERE)
        if start not in (NOWHERE, CARRIED) and start not in rooms:
            found.append(Problem(
                f"object {oid}", f"it starts in room {start}, which is not "
                                 f"there"))

    # A picture that calls another.
    for pid, drawing in (ddb.get("gfx") or {}).items():
        for command in drawing:
            if command[0] == "CALL" and command[1] not in pictures:
                found.append(Problem(
                    f"picture {pid}", f"it calls picture {command[1]}, which "
                                      f"is not there"))

    # A picture that draws outside the frame.  Ours draws what fits; the
    # original stopped drawing that picture there and left the rest of it
    # out, which was asked of it with pictures written over one of
    # MegaCorp's -- see doc/pendiente.md.  No picture of the four adventures
    # does it, so this is for the ones being written now.
    for pid, drawing in (ddb.get("gfx") or {}).items():
        for number, command in enumerate(drawing, start=1):
            outside = [y for y in ys_of(command)
                       if not PICTURE_BOTTOM <= y <= PICTURE_TOP]
            if outside:
                found.append(Problem(
                    f"picture {pid}",
                    f"its order {number}, {command[0]}, goes to y={outside[0]},"
                    f" outside the frame ({PICTURE_BOTTOM} to {PICTURE_TOP}):"
                    f" this draws what fits, where the original would have"
                    f" stopped drawing the picture there",
                    fault=False))

    # What the interpreter says for itself.
    for number, what in NEEDED.items():
        if number not in messages:
            found.append(Problem("the messages",
                                 f"message {number} is missing, and the "
                                 f"interpreter needs it {what}"))
    for number, what in WANTED.items():
        if number not in messages:
            found.append(Problem("the messages",
                                 f"message {number} is missing, which the "
                                 f"interpreter reaches for {what}",
                                 fault=False))

    # And the typeface, which is the one thing an adventure can be missing
    # without anything complaining: every letter is then eight noughts, so it
    # builds, runs, and prints blank lines.  The example adventure did exactly
    # that until it was given one.
    if not any(ddb.get("font") or []):
        found.append(Problem("the font",
                             "there is not one: every letter would print "
                             "blank.  A source says /FONT file=\"...\", or "
                             "draws the letters it wants one at a time",
                             fault=False))

    found += said_twice(ddb)

    return sorted(found, key=lambda p: (not p.fault, p.where, p.message))


def said_twice(ddb):
    """Words that are the same word twice over, and answer to two numbers.

    What the parser compares is the word with its marks taken off and in one
    case, because no keyboard here has a key for an accent: see text.py.  So
    LAMPARA and lámpara are the same word to it, and if they answer to
    different numbers the player can only ever reach the first -- which is a
    mistake nobody would see by reading the vocabulary, because on the page
    they are two words.
    """
    out = []
    for kind in ("verbs", "nouns", "adverbs"):
        table = ddb.get(kind) or {}
        folded = {}
        for word, number in sorted(table.items()):
            same = typed(str(word)).upper()
            if same in folded and folded[same][1] != number:
                first, its = folded[same]
                out.append(Problem(
                    f"the {kind[:-1]}s",
                    f"{word} ({number}) is the same word as {first} ({its}) "
                    f"once the marks come off, so only the first can ever be "
                    f"typed", fault=False))
            else:
                folded.setdefault(same, (word, number))
    return out
