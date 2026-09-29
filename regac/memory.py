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
"""What a build takes of the machine, and what it leaves: said after every
machine regac make builds.

Decided by the user: an author has to know how much room is left, and where,
before the adventure stops fitting rather than after.  What is measured is
what the assembler did, not what the database guesses: sjasmplus writes the
address of every label it placed, and the stretches below are the same ones
the ASSERTs at the end of each machine's game*.asm hold the build to -- where
the interpreter and the resident part of the database start, where they have
to end by, and where they ended.  The banks are the database's own, each the
size of the machine's window, with the sections that went in each.

A stretch is reported even when the build did not fit, because that is when
it matters most: sjasmplus writes its symbols after an ASSERT fails, so the
report can say by how much it went over.
"""

import os

from .binary import PC_LONGEST_SECTION, RESIDENT, SECTION_NAMES
from .i18n import _

BAR = 20                        # how wide the bar is, in characters


def symbols(path):
    """The labels of a sjasmplus --sym file, by name: `name: EQU 0x8000`."""
    found = {}
    if not os.path.isfile(path):
        return found
    with open(path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            name, colon, rest = line.partition(":")
            words = rest.split()
            if colon and len(words) == 2 and words[0] == "EQU":
                try:
                    found[name.strip()] = int(words[1], 0)
                except ValueError:
                    pass
    return found


class Stretch:
    """Part of the machine's memory: the pieces laid in it one after
    another, from where the first starts, and where the last has to end by."""

    def __init__(self, end, pieces):
        self.pieces = pieces            # (what, where it starts, how long)
        self.start = pieces[0][1]
        self.end = end
        last = pieces[-1]
        self.used = last[1] + last[2] - self.start
        self.size = end - self.start

    @property
    def free(self):
        return self.size - self.used


def stretches(which, sym, database):
    """The stretches of one machine, from where its assembler put things.
    `which` is the name its output folder has: spectrum48, cpc464, next..."""
    interpreter, data = _("interpreter"), _("database")

    def between(what, first, past):
        return (what, sym[first], sym[past] - sym[first])

    if which in ("spectrum48", "spectrum128", "plus3", "pcw"):
        # the interpreter and then the resident database, up to the window --
        # or, on a 48K Spectrum, up to the end of the machine
        end = 0x10000 if which == "spectrum48" else sym["DB_WINDOW"]
        return [Stretch(end, [between(interpreter, "start", "database"),
                              between(data, "database", "last")])]
    if which == "cpc464":
        if "ISLAND_AT" in sym:
            # LOW_CODE: the interpreter under $4000 and clear of the mask,
            # and the whole database from $4000 to the island
            return [
                Stretch(min(sym["BASIC_KEEPS_FROM"], sym["MASK"]),
                        [between(interpreter, "start", "last")]),
                Stretch(sym["ISLAND_AT"], [(data, sym["DATABASE_AT"],
                                            database.resident_size)]),
            ]
        return [Stretch(sym["FIRMWARE_AT"],
                        [between(interpreter, "start", "database"),
                         between(data, "database", "last")])]
    if which == "cpc6128":
        # A picture off a Spectrum keeps its mask above the interpreter, and
        # the mask has to end a page short of the stack.
        end = sym["SAVE_AREA"]
        if "MASK_BYTES" in sym:
            end = min(end, sym["STACK_AT"] - 256 - sym["MASK_BYTES"])
        return [
            Stretch(sym["RESIDENT_LOADS"], [(data, sym["database"],
                                             sym["DB_RESIDENT_SIZE"])]),
            Stretch(end, [between(interpreter, "start", "last")]),
        ]
    if which == "msx":
        return [
            Stretch(sym["from_tape"], [(data, sym["database"],
                                        database.resident_size)]),
            Stretch(sym["SHADOW"], [between(interpreter, "from_tape", "last")]),
        ]
    if which == "next":
        # Only a picture off a Spectrum has the mask at $A000; one off an
        # Amstrad may run on up to what is put above it.
        end = sym["MASK"] if "MASK_BYTES" in sym else sym["ABOVE_MASK"]
        return [
            Stretch(sym["start"], [(data, sym["database"],
                                    sym["DB_RESIDENT_SIZE"])]),
            Stretch(end, [between(interpreter, "start", "last")]),
            Stretch(sym["STACK_AT"] - sym["STACK_ROOM"],
                    [between(interpreter, "above_mask", "past_mask")]),
        ]
    raise KeyError(which)


def bar(share):
    """How full, as a row of hashes: full is all of them, and over is too."""
    filled = min(BAR, round(share * BAR))
    if share > 0 and filled == 0:
        filled = 1                      # something is not nothing
    return "[" + "#" * filled + "-" * (BAR - filled) + "]"


def line(where, used, size, what):
    """One row of the report: where, how full, how much is left and of what."""
    share = used / size if size else 1.0
    if used <= size:
        left = _("{n:>5} free of {size:>5}", n=size - used, size=size)
    else:
        left = _("{n:>5} too many, of {size:>5}", n=used - size, size=size)
    return f"    {where:<12} {bar(share)} {share:>4.0%}  {left}  {what}"


def pieces_of(pieces):
    return ", ".join(f"{what} {size}" for what, _start, size in pieces)


def sections_in(database, bank):
    """The sections that went into a bank, with how big each is."""
    return ", ".join(f"{SECTION_NAMES[index]} {size}"
                     for index, (where, _offset, size)
                     in enumerate(database.placement)
                     if where == bank and size)


def database_line(database, everything=False):
    """What the database carries next to the interpreter, section by
    section, the biggest first: what there is to trim when it does not fit.
    That is the resident part -- or all of it, on a PC, where every section is
    in memory at once."""
    parts = [(_("header"), 0, database.header_size)]
    parts += [(SECTION_NAMES[index], 0, size)
              for index, (bank, _offset, size) in enumerate(database.placement)
              if size and (everything or bank == RESIDENT)]
    parts.sort(key=lambda part: -part[2])
    return " " * 17 + _("database: {what}", what=pieces_of(parts))


def bank_lines(database, most):
    """A row for every bank the database fills, and one for those left."""
    if not database.page_bits or most is None:
        return []
    page = 1 << database.page_bits
    used = len(database.banks)
    lines = [_("    banks        {used} of {most}, {size} bytes each",
               used=used, most=most, size=page)]
    for number, bank in enumerate(database.banks):
        lines.append(line(_("bank {bank}", bank=number), len(bank), page,
                          sections_in(database, number)))
    if used < most:
        where = (_("bank {bank}", bank=used) if used == most - 1 else
                 _("banks {first}-{last}", first=used, last=most - 1))
        lines.append(_("    {where:<12} unused: {n} bytes more", where=where,
                       n=(most - used) * page))
    return lines


def report(which, sym, database, most_banks=None):
    """What a build of one machine takes and leaves, as the lines to say; and
    where it went over, which is nowhere when it fits."""
    lines, over = [], []
    for stretch in stretches(which, sym, database):
        where = f"${stretch.start:04X}-${stretch.end - 1:04X}"
        lines.append(line(where, stretch.used, stretch.size,
                          pieces_of(stretch.pieces)))
        if any(what == _("database") for what, _start, _size
               in stretch.pieces):
            lines.append(database_line(database))
        if stretch.free < 0:
            over.append(_("{where} by {n} bytes", where=where,
                          n=-stretch.free))
    return lines + bank_lines(database, most_banks), over


def pc_report(program, database, stack):
    """A PC's, which has no map to fill: what DOS has to give it, and the
    largest section, which is what has to fit in the sixty four kilobytes of
    a segment."""
    image = database.resident_size + sum(len(bank) for bank in database.banks)
    lines = [_("    memory       {n} bytes: {what}",
               n=program + image + stack,
               what=pieces_of([(_("interpreter"), 0, program),
                               (_("database"), 0, image),
                               (_("stack"), 0, stack)])),
             database_line(database, everything=True)]
    sizes = [size for _bank, _offset, size in database.placement]
    largest = max(range(len(sizes)), key=lambda index: sizes[index])
    lines.append(line(SECTION_NAMES[largest], sizes[largest],
                      PC_LONGEST_SECTION, _("the largest section")))
    return lines

