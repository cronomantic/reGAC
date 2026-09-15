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
"""Turn an Arkos Tracker player into a source sjasmplus can assemble.

The players that come with Arkos Tracker are written for RASM, and three
things in them are RASM's rather than the Z80's.  None is hard on its own;
together they are the difference between "include it and go" and an afternoon.

  * **Disark's markers.**  Scattered through the player are labels like
    `dkbs (void):`, which say to Disark -- the tool that makes the assembled
    output relocatable -- where the pointers are.  RASM takes a label with no
    value; nothing else does.  They carry no code and come out.

  * **Macros that make labels.**  The player declares its hundred variables
    with `PLY_AKM_db name`, and inside the macro the name becomes a label by
    substitution.  A macro cannot make a label here, so the two of them are
    expanded where they stand.

  * **Flags that are tested with IFDEF.**  The player is configured by
    assigning `NAME = 1` and asking `IFDEF NAME`.  Here IFDEF sees defines and
    not symbols, so those become defines -- guarded, because defining one
    twice is an error here and a shrug there.

  * **A comma at the end of a list.**  One row of the period table ends with
    one, which RASM reads as the end of the list and this assembler reads as
    the promise of another number.  It comes off.

What comes out is the same player, byte for byte, in a source this project's
assembler reads.  Run it again when Arkos Tracker is updated:

    python arkos.py ArkosTracker3/players/playerAkm/sources/z80/PlayerAkm.asm \\
                    z80/arkos/PlayerAkm.asm

The players are MIT, like z80/ itself; keep their notice with them.
"""

import argparse
import os
import re
import sys

# What a line of assignment looks like, and the words that are not symbols.
ASSIGNMENT = re.compile(r"^[ \t]+([A-Za-z_][\w.]*)[ \t]*=[ \t]*(.+?)[ \t]*$")
FLAG = re.compile(r"^[ \t]*([A-Za-z_][\w.]*)[ \t]*=[ \t]*1[ \t]*(;.*)?$")
MARKER = re.compile(r"^(\s*)[A-Za-z_]\w* \(void\):")
MARKER_ALONE = re.compile(r"^\s*[A-Za-z_]\w*\s*\(void\)\s*$")
DATA_COMMA = re.compile(
    r"^(\s*(?:db|dw|defb|defw)\s+.*?),\s*(;.*)?$", re.I)
MACRO_START = re.compile(r"^\s*MACRO\s+([A-Za-z_]\w*)", re.I)
MACRO_END = re.compile(r"^\s*ENDM\b", re.I)
KEYWORDS = {"if", "ifdef", "ifndef", "assert", "else", "endif", "repeat",
            "while", "rend", "macro", "org", "db", "dw", "ds", "defb", "defw"}


def maker_of_labels(body):
    """Whether a macro's body is the kind that makes a label out of its
    argument, which is the kind that has to be expanded by hand."""
    return any("{label}" in line for line in body)


def convert(text):
    """The player, as a source this assembler reads, and what was done."""
    lines = text.splitlines()
    out, counts = [], {"markers": 0, "variables": 0, "flags": 0, "macros": 0,
                       "commas": 0}
    makers, macro, body = set(), None, []
    for line in lines:
        start = MACRO_START.match(line)
        if start and macro is None:
            macro, body = start.group(1), []
            continue
        if macro is not None:
            if MACRO_END.match(line):
                if maker_of_labels(body):
                    makers.add(macro.lower())
                counts["macros"] += 1
                macro = None
            else:
                body.append(line)
            continue

        if MARKER_ALONE.match(line):
            counts["markers"] += 1
            continue
        if MARKER.match(line):
            line = MARKER.sub(r"\1", line)
            counts["markers"] += 1
            if not line.strip():
                continue

        used = re.match(r"^\s*([A-Za-z_]\w*)\s+(\S+)(.*)$", line)
        if used and used.group(1).lower() in makers:
            kind = "dw" if used.group(1).lower().endswith("dw") else "db"
            comment = used.group(3)
            said = comment.split(";", 1)[1] if ";" in comment else ""
            line = f"{used.group(2)}: {kind} 0" + (f"      ;{said}" if said else "")
            counts["variables"] += 1

        flag = FLAG.match(line)
        if flag and flag.group(1).lower() not in KEYWORDS:
            name, said = flag.group(1), flag.group(2) or ""
            out += [f"                IFNDEF {name}",
                    f"                DEFINE {name} 1 {said}".rstrip(),
                    "                ENDIF"]
            counts["flags"] += 1
            continue

        dangling = DATA_COMMA.match(line)
        if dangling:
            line = dangling.group(1) + ("      " + dangling.group(2)
                                        if dangling.group(2) else "")
            counts["commas"] += 1

        moved = ASSIGNMENT.match(line)
        if moved and moved.group(1).lower() not in KEYWORDS:
            line = f"{moved.group(1)} = {moved.group(2)}"      # a label wants column one

        out.append(line)
    return "\n".join(out) + "\n", counts


HEADER = """; Converted from the source that comes with Arkos Tracker, which is written
; for RASM, by arkos.py in the root of this project.  Run that again rather
; than editing this by hand: what it does and why is in its own docstring.
;
; {name} and everything it contains is
;
;   MIT License
;   Copyright (c) 2016-2025 Julien Nevo (contact@julien-nevo.com)
;
; and the whole of that notice is in LICENSE.txt beside this file.  The
; conversion changes no instruction and no byte of what it assembles to.
;
"""


def main():
    parser = argparse.ArgumentParser("arkos")
    parser.add_argument("input", help="a player source from Arkos Tracker")
    parser.add_argument("output", help="where to write the converted source")
    args = parser.parse_args()
    with open(args.input, encoding="utf-8", errors="replace") as f:
        text = f.read()
    converted, counts = convert(text)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(HEADER.format(name=os.path.basename(args.input)))
        f.write(converted)
    print(f"{args.input} -> {args.output}")
    for what, many in counts.items():
        print(f"  {what:12}{many}")


if __name__ == "__main__":
    sys.exit(main())
