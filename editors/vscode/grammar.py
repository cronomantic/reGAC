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
"""Write the grammar that colours a .gac source in VS Code.

The words of the language are read out of regac/opcodes.py, which is the one
place they are written down, so the grammar is made and not kept by hand:

    python editors/vscode/grammar.py

and tests/test_editor.py says when it is out of date.

What it knows of the shape of a source is what doc/formato-fuente.md says:
the sections, the directives, the conditions, the drawing orders, and that
inside a text -- a message, an object's name, a room -- everything is
literal but its commands, and a semicolon there is not a comment.
"""

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)

from regac.opcodes import GFX_CMDS, OPS  # noqa: E402

OUTPUT = os.path.join(HERE, "syntaxes", "gac.tmLanguage.json")
NEXT_SECTION = r"(?=^\s*/[A-Za-z])"


def words(names):
    """A pattern that matches any of the words, whole: a word here may end
    in a question mark, SET? and its kind."""
    ordered = sorted(names, key=len, reverse=True)
    return r"(?<![\w?])(" + "|".join(re.escape(n) for n in ordered) + r")(?![\w?])"


def grammar():
    opcodes = [op.name for op in OPS if op.name[0].isalpha()
               and op.name not in ("ENDTABLE", "IF", "END")]
    operators = [op.name for op in OPS if not op.name[0].isalpha()]
    comment = {"name": "comment.line.semicolon.gac", "match": r";.*$"}
    directive = {"name": "keyword.control.directive.gac",
                 "match": r"^\s*\.(if|else|end|def|include)\b"}
    number = {"name": "constant.numeric.gac",
              "match": r"(?<![\w#])(0x[0-9A-Fa-f]+|\d+)(?![\w])"}
    entry = {"name": "entity.name.section.entry.gac",
             "match": r"^\s*#\S+"}
    attribute = {"match": r"\b([a-z]+)(=)",
                 "captures": {"1": {"name": "variable.parameter.gac"},
                              "2": {"name": "keyword.operator.gac"}}}
    name = {"name": "variable.other.constant.gac",
            "match": r"\b[A-Za-z_][A-Za-z0-9_]*\b"}
    return {
        "$schema": "https://raw.githubusercontent.com/martinring/"
                   "tmlanguage/master/tmlanguage.json",
        "name": "GAC",
        "scopeName": "source.gac",
        "fileTypes": ["gac"],
        "patterns": [
            {"include": "#directive"},
            {"include": "#conditions"},
            {"include": "#pictures"},
            {"include": "#texts"},
            {"include": "#settings"},
            {"include": "#comment"},
            {"include": "#number"},
        ],
        "repository": {
            "comment": comment,
            "directive": directive,
            "number": number,
            "section": {"name": "keyword.other.section.gac",
                        "match": r"^\s*/[A-Za-z]+"},
            # the tables of conditions, and the ways out of a room
            "conditions": {
                "begin": r"^\s*(/(HIGH|LOW|LOCAL|PROC|CONN))\b",
                "beginCaptures": {"1": {"name": "keyword.other.section.gac"}},
                "end": NEXT_SECTION,
                "patterns": [
                    comment, directive, entry,
                    {"name": "keyword.control.gac",
                     "match": r"(?<![\w?])(IF|END)(?![\w?])"},
                    {"name": "support.function.opcode.gac",
                     "match": words(opcodes)},
                    {"name": "keyword.operator.gac",
                     "match": "|".join(re.escape(o) for o in operators)},
                    {"name": "punctuation.paren.gac", "match": r"[()]"},
                    number, name,
                ],
            },
            # the drawing orders of the pictures
            "pictures": {
                "begin": r"^\s*(/GFX)\b",
                "beginCaptures": {"1": {"name": "keyword.other.section.gac"}},
                "end": NEXT_SECTION,
                "patterns": [
                    comment, directive, entry, attribute,
                    {"name": "support.function.drawing.gac",
                     "match": words(GFX_CMDS)},
                    number, name,
                ],
            },
            # messages, objects and rooms: text, where only the commands and
            # the headers of the entries are anything but letters
            "texts": {
                "begin": r"^\s*(/(MSG|OBJ|LOC))\b(.*)$",
                "beginCaptures": {
                    "1": {"name": "keyword.other.section.gac"},
                    "3": {"patterns": [entry, attribute, number, comment]}},
                "end": NEXT_SECTION,
                "patterns": [
                    directive,
                    {"match": r"^\s*(#\S+)(.*)$",
                     "captures": {
                         "1": {"name": "entity.name.section.entry.gac"},
                         "2": {"patterns": [attribute, number, name,
                                            comment]}}},
                    {"name": "constant.character.escape.gac",
                     "match": r"\\(ink|ctr|obj)[ \t]*\d{1,3}|\\turns|\\\\"},
                    {"name": "invalid.illegal.command.gac",
                     "match": r"\\."},
                    {"name": "constant.character.escape.line.gac",
                     "match": r"^\s*\|"},
                    {"name": "string.unquoted.text.gac", "match": r"[^\\]+"},
                ],
            },
            # the rest: the settings, the vocabulary, the font, the noises
            "settings": {
                "begin": r"^\s*(/(CTL|VOC|FONT|SOUND))\b",
                "beginCaptures": {"1": {"name": "keyword.other.section.gac"}},
                "end": NEXT_SECTION,
                "patterns": [
                    comment, directive, attribute,
                    {"name": "storage.type.word.gac",
                     "match": r"\b(verb|noun|adverb|pronoun)\b"},
                    {"name": "keyword.other.setting.gac",
                     "match": r"^\s*(model|charset|start|width|punct|sep|"
                              r"ink|nothing)\b"},
                    {"name": "support.constant.channel.gac",
                     "match": r"\b(tone|noise|both)\b"},
                    {"name": "string.quoted.double.gac", "match": r'"[^"]*"'},
                    number,
                ],
            },
        },
    }


def written():
    return json.dumps(grammar(), indent=2, ensure_ascii=False) + "\n"


if __name__ == "__main__":
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(written())
    print(OUTPUT)
