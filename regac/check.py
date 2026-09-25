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
from .opcodes import (ADVERB, BY_NAME, CTR, FLAG, MSG, NOUN, OBJ, PROC, ROOM,
                      VERB)
from .i18n import N_, _
from .text import HOLE_OBJECT, commands_of, expand, typed

COUNTERS = 128                  # what the interpreters have, in every machine
CARRIED = 255                   # where an object the player holds lives
NOWHERE = 0

# What the interpreter says for itself, and cannot do without.  The numbers
# are the original's and are the same on every machine: see z80/common.
NEEDED = {
    240: N_("to ask the player for an order"),
    241: N_("to say an order cannot be done"),
    242: N_("to say an order was not understood"),
}
# And the ones it only reaches for in certain circumstances, which an
# adventure may honestly not want.
WANTED = {
    243: N_("to ask for a key"),
    244: N_("to ask whether the player is sure"),
    246: N_("to say the player has not got it"),
    247: N_("to say there is nothing like that here"),
    248: N_("to say the player is carrying too much"),
    251: N_("to say it is dark"),
    253: N_("to introduce what can be seen"),
    254: N_("to say it is done"),
}


class Problem:
    """Something that is wrong, or probably wrong, and where."""

    __slots__ = ("where", "message", "fault")

    def __init__(self, where, message, fault=True):
        self.where = where              # the part of the adventure it is in
        self.message = message
        self.fault = fault              # or only a warning

    def __str__(self):
        if self.fault:
            return f"{self.where}: {self.message}"
        return _("warning: {where}: {message}", where=self.where,
                 message=self.message)


def ys_of(command):
    """The y of every point a drawing order names that has to be in the frame.

    Not every number that looks like a y is one: the second pair of an
    ELLIPSE is where its radii come from and not a place, so it falls outside
    the frame as a matter of course -- the example adventure's own lighthouse
    does it five times over, which is how this was found.  A fill is left out
    too: its seed is a y, but what the original does with one outside is not
    what it does with a point, and it is said on its own below.
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
        for _arg in range(op.argc):
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
    procs = numbered(ddb.get("procs") or {})
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
                problems.append(Problem(where, _(
                    "{op} {value}, and there is no message {value}",
                    op=op.name, value=value)))
            elif kind is ROOM and value not in rooms and value not in (NOWHERE,
                                                                       CARRIED):
                problems.append(Problem(where, _(
                    "{op} {value}, and there is no room {value}",
                    op=op.name, value=value)))
            elif kind is PROC and value not in procs:
                problems.append(Problem(where, _(
                    "{op} {value}, and there is no /PROC {value}",
                    op=op.name, value=value)))
            elif kind is OBJ and value not in objects:
                problems.append(Problem(where, _(
                    "{op} {value}, and there is no object {value}",
                    op=op.name, value=value)))
            elif kind is CTR and not 0 <= value < COUNTERS:
                problems.append(Problem(where, _(
                    "{op} {value}, and there are {counters} counters, "
                    "numbered 0 to {last}", op=op.name, value=value,
                    counters=COUNTERS, last=COUNTERS - 1)))
            elif kind is FLAG and not 0 <= value <= 255:
                problems.append(Problem(where, _(
                    "{op} {value}, and there are 256 flags, numbered 0 to "
                    "255", op=op.name, value=value)))
            elif kind in words and value and value not in words[kind]:
                problems.append(Problem(where, _(
                    "{op} {value}, and no word of the vocabulary has that "
                    "number", op=op.name, value=value), fault=False))
        if op.name == "SOUND" and taken[0] is not None:
            if taken[0] < 1:
                problems.append(Problem(
                    where, _("SOUND 0, and effects are numbered from one")))
            elif noises and taken[0] > noises:
                # Only when the adventure says what its noises are: a bank
                # exported from the tracker is assembly and nothing here can
                # count what is in it.
                problems.append(Problem(where, _(
                    "SOUND {value}, and this adventure says what {noises} "
                    "noises it has", value=taken[0], noises=noises)))


def problems_of(ddb):
    """Everything worth saying about an adventure, faults first."""
    found = []
    messages = numbered(ddb.get("messages", {}))
    rooms = numbered(ddb.get("locations", {}))
    pictures = numbered(ddb.get("gfx", {}))

    # The holes in the text: an object's name it asks for has to be there,
    # and an object's own name may not ask for one.
    objects = numbered(ddb.get("objects", {}))
    texts = [(_("message {n}", n=n), text, False)
             for n, text in (ddb.get("messages") or {}).items()]
    texts += [(_("room {n}", n=n), room.get("desc", ""), False)
              for n, room in (ddb.get("locations") or {}).items()]
    texts += [(_("object {n}", n=n), one.get("name", ""), True)
              for n, one in (ddb.get("objects") or {}).items()]
    for where, text, a_name in texts:
        try:
            commands = list(commands_of(expand(text)))
        except ValueError as e:
            found.append(Problem(where, str(e)))
            continue
        for which, value, _rest in commands:
            if which != HOLE_OBJECT:
                continue
            if a_name:
                found.append(Problem(where, _(
                    "\\obj {value} in the name of an object, which may not "
                    "name one", value=value)))
            elif value not in objects:
                found.append(Problem(where, _(
                    "\\obj {value}, and there is no object {value}",
                    value=value)))

    follow(found, _("the high priority conditions"), ddb.get("hpcs", []), ddb)
    follow(found, _("the low priority conditions"), ddb.get("lpcs", []), ddb)
    for lid, code in (ddb.get("lcs") or {}).items():
        follow(found, _("the local conditions of room {n}", n=lid), code, ddb)
    for pid, code in (ddb.get("procs") or {}).items():
        follow(found, _("procedure {n}", n=pid), code, ddb)

    # Where the player starts, and where every way out goes.
    start = ddb.get("init_loc")
    if start is not None and int(start) not in rooms:
        found.append(Problem(_("the control section"), _(
            "the player starts in room {room}, which is not there",
            room=start)))
    for lid, room in (ddb.get("locations") or {}).items():
        for way in room.get("exits", []):
            if way["dest"] not in rooms:
                found.append(Problem(_("room {n}", n=lid), _(
                    "a way out goes to room {room}, which is not there",
                    room=way["dest"])))
        picture = room.get("graphic_id") or 0
        if picture and picture not in pictures:
            found.append(Problem(_("room {n}", n=lid), _(
                "it shows picture {picture}, which is not there",
                picture=picture)))

    # Where every object starts.
    for oid, obj in (ddb.get("objects") or {}).items():
        start = obj.get("initial_loc", NOWHERE)
        if start not in (NOWHERE, CARRIED) and start not in rooms:
            found.append(Problem(_("object {n}", n=oid), _(
                "it starts in room {room}, which is not there", room=start)))

    # A picture that calls another.
    for pid, drawing in (ddb.get("gfx") or {}).items():
        for command in drawing:
            if command[0] == "CALL" and command[1] not in pictures:
                found.append(Problem(_("picture {n}", n=pid), _(
                    "it calls picture {picture}, which is not there",
                    picture=command[1])))

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
                found.append(Problem(_("picture {n}", n=pid), _(
                    "its order {number}, {order}, goes to y={y}, outside the "
                    "frame ({bottom} to {top}): this draws what fits, where "
                    "the original would have stopped drawing the picture "
                    "there", number=number, order=command[0], y=outside[0],
                    bottom=PICTURE_BOTTOM, top=PICTURE_TOP), fault=False))

    # A fill started outside the frame.  Ours lays nothing; the original does
    # not agree, and not in one way: asked of it with a box and a seed above
    # and below, a seed just above filled from the top of the picture down,
    # a little further up nothing, and far up hung it; below the frame it
    # filled from the seed upwards, rows of the text window and all.  Laying
    # nothing and saying so is what was decided, as for the orders above --
    # see doc/pendiente.md.  No picture of the eight adventures does it.
    for pid, drawing in (ddb.get("gfx") or {}).items():
        for number, command in enumerate(drawing, start=1):
            if command[0] not in ("FILL", "BGFILL", "SHADE"):
                continue
            y = command[2]
            if PICTURE_BOTTOM <= y <= PICTURE_TOP:
                continue
            if y < PICTURE_BOTTOM:
                said = _("its order {number}, {order}, starts at y={y}, "
                         "outside the frame ({bottom} to {top}): this lays "
                         "nothing, where the original filled from there "
                         "upwards, into the text window as well",
                         number=number, order=command[0], y=y,
                         bottom=PICTURE_BOTTOM, top=PICTURE_TOP)
            else:
                said = _("its order {number}, {order}, starts at y={y}, "
                         "outside the frame ({bottom} to {top}): this lays "
                         "nothing, where the original filled from the top of "
                         "the picture down, or did nothing, or hung, "
                         "depending on how far above", number=number,
                         order=command[0], y=y, bottom=PICTURE_BOTTOM,
                         top=PICTURE_TOP)
            found.append(Problem(_("picture {n}", n=pid), said, fault=False))

    # What the interpreter says for itself.
    for number, what in NEEDED.items():
        if number not in messages:
            found.append(Problem(_("the messages"), _(
                "message {number} is missing, and the interpreter needs it "
                "{what}", number=number, what=_(what))))
    for number, what in WANTED.items():
        if number not in messages:
            found.append(Problem(_("the messages"), _(
                "message {number} is missing, which the interpreter reaches "
                "for {what}", number=number, what=_(what)), fault=False))

    # And the typeface, which is the one thing an adventure can be missing
    # without anything complaining: every letter is then eight noughts, so it
    # builds, runs, and prints blank lines.  The example adventure did exactly
    # that until it was given one.
    if not any(ddb.get("font") or []):
        found.append(Problem(_("the font"), _(
            "there is not one: every letter would print blank.  A source "
            "says /FONT file=\"...\", or draws the letters it wants one at "
            "a time"), fault=False))

    found += said_twice(ddb)

    return sorted(found, key=lambda p: (not p.fault, p.where, p.message))


KINDS = {"verbs": N_("the verbs"), "nouns": N_("the nouns"),
         "adverbs": N_("the adverbs")}


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
                out.append(Problem(_(KINDS[kind]), _(
                    "{word} ({number}) is the same word as {first} ({its}) "
                    "once the marks come off, so only the first can ever be "
                    "typed", word=word, number=number, first=first, its=its),
                    fault=False))
            else:
                folded.setdefault(same, (word, number))
    return out
