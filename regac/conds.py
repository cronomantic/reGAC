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
"""Rendering of condition bytecode back into GAC source lines.

The bytecode is postfix; the source syntax is prefix/infix.  Rebuilding the
source means running the postfix program over a stack of source fragments
instead of a stack of values.  Everything the renderer knows about each opcode
comes from `regac.opcodes`.
"""

from .opcodes import BY_NAME, CTRL, INFIX, NULLARY, PREFIX


class Node:
    """One item of a rendered line.  A node is `live` while it still represents
    a value on the operand stack, i.e. while a later opcode may still consume
    it.  Nodes keep their position, so a value the original bytecode pushes and
    never consumes is rendered where it was pushed instead of being dropped."""

    __slots__ = ("text", "infix")

    def __init__(self, text, infix=False):
        self.text = text
        self.infix = infix

    def operand(self):
        return f"( {self.text} )" if self.infix else self.text


class RenderError(Exception):
    pass


def render_block(code, strict=False):
    """Render a flat condition table into a list of source lines.

    `code` is the list deGAC produces: ["PUSH", n] or [opcode_name].
    Returns a list of strings, one per condition line.
    """
    lines = []
    items = []  # every node of the current line, in source order
    stack = []  # the subset of those nodes still live as operands

    def push(text, infix=False):
        node = Node(text, infix)
        items.append(node)
        stack.append(node)
        return node

    def plain(text):
        items.append(Node(text))

    def take():
        if not stack:
            if strict:
                raise RenderError(_("stack underflow"))
            return Node("?")
        node = stack.pop()
        items.remove(node)
        return node

    def flush():
        if items:
            lines.append(" ".join(n.text for n in items))
            del items[:]
        del stack[:]

    for ins in code:
        name = ins[0]
        if name == "PUSH":
            push(str(ins[1]))
            continue
        if name in ("OP0", "ENDTABLE"):
            break
        if name == "UNKNOWN":
            plain(f"; <unknown opcode {ins[1]:#04x}>")
            continue

        op = BY_NAME.get(name)
        if op is None:
            if strict:
                raise RenderError(_("unknown opcode name {name!r}", name=name))
            plain(f"; <{name}>")
            continue

        if op.form is CTRL:
            if op.name == "IF":
                plain(f"IF ( {take().text} )")
            elif op.name == "END":
                plain("END")
                flush()
        elif op.form is NULLARY:
            if op.pushes:
                push(op.name)
            else:
                plain(op.name)
        elif op.form is PREFIX:
            text = f"{op.name} {take().operand()}"
            push(text) if op.pushes else plain(text)
        elif op.form is INFIX:
            right = take()
            left = take()
            text = f"{left.text} {op.name} {right.operand()}"
            push(text, infix=True) if op.pushes else plain(text)

    flush()
    return lines


# ---------------------------------------------------------------------------
# Source -> bytecode
# ---------------------------------------------------------------------------

import difflib
import re

from .i18n import _
from .opcodes import BY_NAME as _OPS

_TOKEN_RE = re.compile(r"[()]|[^\s()]+")


class CompileError(Exception):
    """Something the condition compiler could not read.

    It carries where it happened and, when there is an obvious one, what the
    author probably meant: whoever is printing it knows which file and which
    line, and can point at the very word.
    """

    def __init__(self, message, column=None, meant=None):
        super().__init__(message)
        self.message = message
        self.column = column            # where in the line, counting from one
        self.meant = meant              # the word it was probably going to be

    def __str__(self):
        if self.meant:
            return f"{self.message} -- did you mean {self.meant}?"
        return self.message


def nearest(word, among):
    """The one of those a misspelling was probably meant to be, or None.

    An unknown word in a condition is a typo far more often than it is
    anything else, and the language is sixty eight words long: saying which of
    them was meant costs a line and saves a hunt.
    """
    spellings = {str(one).upper(): one for one in among}
    close = difflib.get_close_matches(str(word).upper(), list(spellings),
                                      n=1, cutoff=0.6)
    return spellings[close[0]] if close else None


def tokenize(text):
    """Split a condition line into tokens, each with where it began.

    Parentheses are always separate, which lets a source be written without
    the spaces GAC itself demanded.
    """
    comment = text.find(";")
    if comment >= 0:
        text = text[:comment]
    return [(m.group(0), m.start() + 1) for m in _TOKEN_RE.finditer(text)]


class _Assembler:
    def __init__(self, tokens, defs=None):
        self.tokens = tokens
        self.defs = defs or {}          # the names a .def gave to numbers
        self.pos = 0
        self.code = []

    def peek(self):
        return self.tokens[self.pos][0] if self.pos < len(self.tokens) else None

    def where(self):
        """The column the next token starts at, or the end of the line."""
        if self.pos < len(self.tokens):
            return self.tokens[self.pos][1]
        if self.tokens:
            last, at = self.tokens[-1]
            return at + len(last)
        return 1

    def next(self):
        tok = self.peek()
        if tok is None:
            raise CompileError(_("the condition stops in the middle"),
                               self.where())
        self.pos += 1
        return tok

    def expect(self, tok):
        at = self.where()
        got = self.next()
        if got != tok:
            raise CompileError(_("expected {wanted!r}, found {got!r}",
                                 wanted=tok, got=got), at)

    def emit(self, *ins):
        self.code.append(list(ins))

    def assemble(self):
        while self.peek() is not None:
            tok = self.peek()
            if tok == "IF":
                self.next()
                self.expect("(")
                self.expr()
                self.expect(")")
                self.emit("IF")
            elif tok == "END":
                self.next()
                self.emit("END")
            else:
                self.expr()
        return self.code

    def expr(self):
        """One statement or value: an operand followed by any number of infix
        continuations.  GAC evaluates strictly left to right, with no operator
        precedence at all."""
        self.operand()
        while True:
            op = _OPS.get(self.peek())
            if op is None or op.form != "infix":
                return
            self.next()
            self.operand()
            self.emit(op.name)

    def operand(self):
        at = self.where()
        tok = self.next()
        if tok == "(":
            self.expr()
            self.expect(")")
            return
        if tok.lstrip("-").isdigit():
            self.emit("PUSH", int(tok))
            return
        if tok in self.defs:
            self.emit("PUSH", self.defs[tok])
            return
        op = _OPS.get(tok)
        if op is None:
            raise CompileError(_("unknown word {word!r}", word=tok), at,
                               nearest(tok, list(_OPS) + list(self.defs)))
        if op.form == "nullary":
            self.emit(op.name)
            return
        if op.form == "prefix":
            self.operand()
            self.emit(op.name)
            return
        raise CompileError(_("{op} goes between two things, so it cannot "
                             "start one", op=op.name), at)


def compile_line(text, defs=None):
    """Compile one source condition line into bytecode instructions.

    `defs` are the names a source gave to numbers with .def, which stand
    wherever a number would.
    """
    return _Assembler(tokenize(text), defs).assemble()


def compile_block(lines, defs=None):
    code = []
    for n, line in enumerate(lines, 1):
        try:
            code.extend(compile_line(line, defs))
        except CompileError as e:
            raise CompileError(_("line {n}: {what}", n=n, what=e)) from None
    return code
