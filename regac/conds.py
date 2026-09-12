# MIT License
#
# Copyright (c) 2025 Cronomantic
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
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
