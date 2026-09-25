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
"""The colours of a .gac source in VS Code, in editors/vscode/.

The grammar is made from regac/opcodes.py by editors/vscode/grammar.py, so
that a word added to the language is a word the editor knows; this says
when the one in the repository was not made again."""

import importlib.util
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from regac.opcodes import GFX_CMDS, OPS  # noqa: E402

EDITOR = os.path.join(ROOT, "editors", "vscode")


def maker():
    spec = importlib.util.spec_from_file_location(
        "grammar", os.path.join(EDITOR, "grammar.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def patterns(rule):
    """Every pattern of the grammar, in no particular order."""
    if isinstance(rule, dict):
        for key in ("match", "begin", "end"):
            if key in rule:
                yield rule[key]
        for value in rule.values():
            yield from patterns(value)
    elif isinstance(rule, list):
        for value in rule:
            yield from patterns(value)


def test_the_grammar_in_the_repository_is_the_one_the_language_makes():
    with open(maker().OUTPUT, encoding="utf-8") as f:
        kept = f.read()
    assert kept == maker().written(), (
        "the grammar is out of date: python editors/vscode/grammar.py")


def test_every_pattern_is_one():
    for pattern in patterns(maker().grammar()):
        re.compile(pattern, re.M)


def rule(name):
    return maker().grammar()["repository"][name]


def found(rule_patterns, scope, line):
    for one in rule_patterns:
        if one.get("name") == scope:
            return [m.group(0) for m in re.finditer(one["match"], line)]
    raise AssertionError(f"no {scope}")


def test_every_word_of_the_language_is_known():
    conditions = rule("conditions")["patterns"]
    line = " ".join(op.name for op in OPS if op.name[0].isalpha()
                    and op.name not in ("ENDTABLE", "IF", "END"))
    known = found(conditions, "support.function.opcode.gac", line)
    assert known == line.split(), set(line.split()) - set(known)
    drawing = found(rule("pictures")["patterns"],
                    "support.function.drawing.gac", " ".join(GFX_CMDS))
    assert drawing == list(GFX_CMDS)


def test_a_word_that_ends_in_a_question_is_one_word():
    words = found(rule("conditions")["patterns"], "support.function.opcode.gac",
                  "IF ( SET? 5 AND NOT RES? 6 ) SET 7 DO 2 END")
    assert words == ["SET?", "AND", "NOT", "RES?", "SET", "DO"]


def test_the_commands_of_a_text_and_nothing_else_of_it():
    commands = found(rule("texts")["patterns"], "constant.character.escape.gac",
                     r"Llevas \ctr 5 puntos, \ink 2 rojo, \turns turnos; \\ y \obj 12.")
    assert commands == [r"\ctr 5", r"\ink 2", r"\turns", r"\\", r"\obj 12"]


def test_the_extension_says_where_its_parts_are():
    with open(os.path.join(EDITOR, "package.json"), encoding="utf-8") as f:
        package = json.load(f)
    contributes = package["contributes"]
    for path in (contributes["languages"][0]["configuration"],
                 contributes["grammars"][0]["path"]):
        assert os.path.isfile(os.path.join(EDITOR, path)), path
    assert ".gac" in contributes["languages"][0]["extensions"]
