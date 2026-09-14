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
                raise RenderError("stack underflow")
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
                raise RenderError(f"unknown opcode name {name!r}")
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

import re

from .opcodes import BY_NAME as _OPS

_TOKEN_RE = re.compile(r"[()]|[^\s()]+")


class CompileError(Exception):
    pass


def tokenize(text):
    """Split a condition line into tokens.  Parentheses are always separate,
    which lets a source be written without the spaces GAC itself demanded."""
    comment = text.find(";")
    if comment >= 0:
        text = text[:comment]
    return _TOKEN_RE.findall(text)


class _Assembler:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0
        self.code = []

    def peek(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def next(self):
        tok = self.peek()
        if tok is None:
            raise CompileError("unexpected end of condition")
        self.pos += 1
        return tok

    def expect(self, tok):
        got = self.next()
        if got != tok:
            raise CompileError(f"expected {tok!r}, found {got!r}")

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
        tok = self.next()
        if tok == "(":
            self.expr()
            self.expect(")")
            return
        if tok.lstrip("-").isdigit():
            self.emit("PUSH", int(tok))
            return
        op = _OPS.get(tok)
        if op is None:
            raise CompileError(f"unknown word {tok!r}")
        if op.form == "nullary":
            self.emit(op.name)
            return
        if op.form == "prefix":
            self.operand()
            self.emit(op.name)
            return
        raise CompileError(f"{op.name} cannot start an operand")


def compile_line(text):
    """Compile one source condition line into bytecode instructions."""
    return _Assembler(tokenize(text)).assemble()


def compile_block(lines):
    code = []
    for n, line in enumerate(lines, 1):
        try:
            code.extend(compile_line(line))
        except CompileError as e:
            raise CompileError(f"line {n}: {e}") from None
    return code
