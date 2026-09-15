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
"""Central opcode table for the GAC condition language.

Every other component (decompiler, source writer, source parser, code
generators) reads its knowledge of the language from this table, so adding an
opcode to the new interpreter is a data change, not a code change.

The condition bytecode is a postfix stack language.  The source syntax GAC
itself used is not postfix: operands are written in prefix or infix position
and the compiler reorders them.  `form` records which, and `argk` records what
the inline operand refers to, so that symbolic names can be substituted later.
"""

NULLARY = "nullary"  # OP                 -- takes no inline operand
PREFIX = "prefix"  # OP x               -- one inline operand
INFIX = "infix"  # x OP y             -- two inline operands
CTRL = "ctrl"  # IF / END           -- line structure

# Operand kinds, used to resolve symbolic names and to validate ranges.
NUM = "num"
OBJ = "obj"
ROOM = "room"
MSG = "msg"
FLAG = "flag"
CTR = "ctr"
VERB = "verb"
NOUN = "noun"
ADVERB = "adverb"
COND = "cond"


class Op:
    __slots__ = ("name", "code", "form", "argk", "pushes", "aliases")

    def __init__(self, name, code, form, argk=(), pushes=False, aliases=()):
        self.name = name
        self.code = code
        self.form = form
        self.argk = tuple(argk)
        self.pushes = pushes
        self.aliases = tuple(aliases)

    @property
    def argc(self):
        return len(self.argk)

    def __repr__(self):
        return f"<Op {self.name} {self.code:#04x}>"


# fmt: off
OPS = [
    Op("ENDTABLE", 0x00, CTRL),
    Op("AND",      0x01, INFIX,   (COND, COND),  pushes=True),
    Op("OR",       0x02, INFIX,   (COND, COND),  pushes=True),
    Op("NOT",      0x03, PREFIX,  (COND,),       pushes=True),
    Op("XOR",      0x04, INFIX,   (COND, COND),  pushes=True),
    Op("HOLD",     0x05, PREFIX,  (NUM,)),
    Op("GET",      0x06, PREFIX,  (OBJ,)),
    Op("DROP",     0x07, PREFIX,  (OBJ,)),
    Op("SWAP",     0x08, INFIX,   (OBJ, OBJ)),
    Op("TO",       0x09, INFIX,   (OBJ, ROOM)),
    Op("OBJ",      0x0A, PREFIX,  (OBJ,)),
    Op("SET",      0x0B, PREFIX,  (FLAG,)),
    Op("RESE",     0x0C, PREFIX,  (FLAG,)),
    Op("SET?",     0x0D, PREFIX,  (FLAG,),       pushes=True),
    Op("RES?",     0x0E, PREFIX,  (FLAG,),       pushes=True),
    Op("CSET",     0x0F, INFIX,   (NUM, CTR)),
    Op("CTR",      0x10, PREFIX,  (CTR,),        pushes=True),
    Op("DECR",     0x11, PREFIX,  (CTR,)),
    Op("INCR",     0x12, PREFIX,  (CTR,)),
    Op("EQU?",     0x13, INFIX,   (NUM, CTR),    pushes=True),
    Op("DESC",     0x14, PREFIX,  (ROOM,)),
    Op("LOOK",     0x15, NULLARY),
    Op("MESS",     0x16, PREFIX,  (MSG,)),
    Op("PRIN",     0x17, PREFIX,  (NUM,)),
    Op("RAND",     0x18, PREFIX,  (NUM,),        pushes=True),
    Op("<",        0x19, INFIX,   (NUM, NUM),    pushes=True),
    Op(">",        0x1A, INFIX,   (NUM, NUM),    pushes=True),
    Op("=",        0x1B, INFIX,   (NUM, NUM),    pushes=True),
    Op("SAVE",     0x1C, NULLARY),
    Op("LOAD",     0x1D, NULLARY),
    Op("HERE",     0x1E, PREFIX,  (OBJ,),        pushes=True),
    Op("CARR",     0x1F, PREFIX,  (OBJ,),        pushes=True),
    Op("AVAI",     0x20, PREFIX,  (OBJ,),        pushes=True, aliases=("AVAIL",)),
    Op("+",        0x21, INFIX,   (NUM, NUM),    pushes=True),
    Op("-",        0x22, INFIX,   (NUM, NUM),    pushes=True),
    Op("TURN",     0x23, NULLARY,  (),           pushes=True),
    Op("AT",       0x24, PREFIX,  (ROOM,),       pushes=True),
    Op("BRIN",     0x25, PREFIX,  (OBJ,)),
    Op("FIND",     0x26, PREFIX,  (OBJ,)),
    Op("IN",       0x27, INFIX,   (OBJ, ROOM),   pushes=True),
    Op("NOP",      0x28, NULLARY),
    Op("NOP29",    0x29, NULLARY),
    Op("OKAY",     0x2A, NULLARY),
    Op("WAIT",     0x2B, NULLARY),
    Op("QUIT",     0x2C, NULLARY),
    Op("EXIT",     0x2D, NULLARY),
    Op("ROOM",     0x2E, NULLARY,  (),           pushes=True),
    Op("NOUN",     0x2F, PREFIX,  (NOUN,),       pushes=True),
    Op("VERB",     0x30, PREFIX,  (VERB,),       pushes=True),
    Op("ADVE",     0x31, PREFIX,  (ADVERB,),     pushes=True),
    Op("GOTO",     0x32, PREFIX,  (ROOM,)),
    Op("NO1",      0x33, NULLARY,  (),           pushes=True),
    Op("NO2",      0x34, NULLARY,  (),           pushes=True),
    Op("VBNO",     0x35, NULLARY,  (),           pushes=True),
    Op("LIST",     0x36, PREFIX,  (ROOM,)),
    Op("PICT",     0x37, NULLARY),
    Op("TEXT",     0x38, NULLARY),
    Op("CONN",     0x39, PREFIX,  (VERB,),       pushes=True),
    Op("WEIG",     0x3A, PREFIX,  (OBJ,),        pushes=True),
    Op("WITH",     0x3B, NULLARY,  (),           pushes=True),
    Op("STRE",     0x3C, PREFIX,  (NUM,)),
    Op("LF",       0x3D, NULLARY),
    Op("IF",       0x3E, CTRL),
    Op("END",      0x3F, CTRL),
    # Not the original's.  A byte with bit seven set is a number, so the
    # language has room from here up to $7F.
    Op("MUSIC",    0x40, PREFIX,  (NUM,)),
    Op("SOUND",    0x41, PREFIX,  (NUM,)),
    Op("QUIET",    0x42, NULLARY),
]
# fmt: on

BY_NAME = {}
for _op in OPS:
    BY_NAME[_op.name] = _op
    for _alias in _op.aliases:
        BY_NAME[_alias] = _op

BY_CODE = {op.code: op for op in OPS}

# Names deGAC emits that are not opcodes of the language itself.
PSEUDO = {"PUSH", "OP0", "NOP", "UNKNOWN"}


# ---------------------------------------------------------------------------
# Vector graphics commands: name -> (opcode, argument count)
# ---------------------------------------------------------------------------

GFX_CMDS = {
    "BORDER": (0x01, 1),
    "PLOT": (0x02, 2),
    "ELLIPSE": (0x03, 4),
    "FILL": (0x04, 2),
    "BGFILL": (0x05, 2),
    "SHADE": (0x06, 2),
    "CALL": (0x07, 1),
    "RECT": (0x08, 4),
    "LINE": (0x09, 4),
    "INK": (0x10, 1),
    "PAPER": (0x11, 1),
    "BRIGHT": (0x12, 1),
    "FLASH": (0x13, 1),
    # The Amstrad's, which the Spectrum has no use for: the two pens a fill
    # weaves together, which there are a different thing from the pen an
    # outline is drawn in.  Machines that know nothing of it pay it no mind.
    "PENS": (0x14, 2),
}
