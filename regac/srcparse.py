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
"""Reader for the ReGAC source format: source text -> database dictionary."""

import os

from . import fontfile
from .conds import CompileError, compile_line
from .fontfile import FontError
from .png import ImageError

QUOTES = "'\""
from .opcodes import GFX_CMDS

NOWHERE = 0
CARRIED = 255
DEFAULT_CHARSET = "ascii"
DEFAULT_WIDTH = 32
FONT_PREFIX = 8 * 32  # deGAC always prefixes the font with 32 blank characters

UNESCAPE = {"0": "\0", "n": "\n", "t": "\t", '"': '"', "\\": "\\"}


class SourceError(Exception):
    pass


def strip_comment(line):
    pos = line.find(";")
    return line if pos < 0 else line[:pos]


def parse_strings(text):
    """Read a whitespace-separated list of double-quoted strings."""
    out = []
    i = 0
    while i < len(text):
        c = text[i]
        if c.isspace():
            i += 1
            continue
        if c != '"':
            raise SourceError(f"expected a quoted string, found {text[i:]!r}")
        i += 1
        buf = []
        while i < len(text) and text[i] != '"':
            if text[i] == "\\" and i + 1 < len(text):
                buf.append(UNESCAPE.get(text[i + 1], text[i + 1]))
                i += 2
            else:
                buf.append(text[i])
                i += 1
        if i >= len(text):
            raise SourceError("unterminated string")
        i += 1
        out.append("".join(buf))
    return out


def join_text(lines):
    """Join the lines of a text block.  Lines are separated by a single space
    unless the previous one ends in a backslash, which joins with nothing."""
    lines = list(lines)
    while lines and not lines[-1]:
        lines.pop()
    if not lines:
        return ""
    out = lines[0]
    for line in lines[1:]:
        if out.endswith("\\"):
            out = out[:-1] + line
        else:
            out = out + " " + line
    return out


def text_of(line):
    """A line of adventure text, with the marker escape removed."""
    return line[1:] if line.startswith("|") else line


class Parser:
    def __init__(self, text, name="adventure", folder=None):
        self.lines = text.splitlines()
        self.i = 0
        self.name = name
        self.folder = folder or "."     # what a file= is relative to
        self.pending_exits = {}  # location id -> [(word or number, dest)]
        self.font_chars = 0
        self.ddb = {
            "font": [],
            "verbs": {},
            "nouns": {},
            "pronouns": [],
            "adverbs": {},
            "messages": {},
            "objects": {},
            "locations": {},
            "hpcs": [],
            "lpcs": [],
            "lcs": {},
            "gfx": {},
            "model": "SPECTRUM",
            "punctuation": list("\0 .,-!?:"),
            "separators": [],
            "init_loc": 1,
            "no_objs_msg": "Nothing",
        }
        self.charset = DEFAULT_CHARSET
        self.width = DEFAULT_WIDTH

    # -- line helpers -------------------------------------------------------

    def cur(self):
        return self.lines[self.i]

    def eof(self):
        return self.i >= len(self.lines)

    def at_section(self):
        return self.eof() or self.cur().lstrip().startswith("/")

    def fail(self, msg):
        raise SourceError(f"{self.name}:{self.i + 1}: {msg}")

    def skip_blank(self):
        """Skip blank and comment lines outside text blocks."""
        while not self.eof():
            if strip_comment(self.cur()).strip():
                return
            self.i += 1

    # -- top level ----------------------------------------------------------

    def parse(self):
        handlers = {
            "/CTL": self.ctl,
            "/VOC": self.voc,
            "/MSG": self.msg,
            "/OBJ": self.obj,
            "/HIGH": lambda: self.conds("hpcs"),
            "/LOW": lambda: self.conds("lpcs"),
            "/GFX": self.gfx,
            "/FONT": self.font,
            "/MUSIC": self.music,
        }
        while True:
            self.skip_blank()
            if self.eof():
                break
            head = self.cur().strip()
            if not head.startswith("/"):
                self.fail(f"expected a section marker, found {head[:32]!r}")
            tag = head.split()[0].upper()
            if tag == "/LOC":
                self.loc(head)
                continue
            handler = handlers.get(tag)
            if handler is None:
                self.fail(f"unknown section {tag}")
            self.i += 1
            handler()
        self.finish()
        return self.ddb

    def finish(self):
        for lid, exits in self.pending_exits.items():
            resolved = []
            for word, dest in exits:
                if word.isdigit():
                    vid = int(word)
                elif word in self.ddb["verbs"]:
                    vid = self.ddb["verbs"][word]
                else:
                    raise SourceError(
                        f"location {lid}: {word!r} is not a verb of the vocabulary"
                    )
                resolved.append({"dir": vid, "dest": dest})
            self.ddb["locations"][lid]["exits"] = resolved
        if self.font_chars:
            size = self.font_chars * 8
            font = self.ddb["font"]
            self.ddb["font"] = font + [0] * (size - len(font))
        else:
            self.ddb["font"] = [0] * FONT_PREFIX
        if self.charset != DEFAULT_CHARSET:
            self.ddb["charset"] = self.charset
        if self.width != DEFAULT_WIDTH:
            self.ddb["width"] = self.width

    # -- sections -----------------------------------------------------------

    def ctl(self):
        while not self.at_section():
            st = strip_comment(self.cur()).strip()
            self.i += 1
            if not st:
                continue
            key, _, value = st.partition(" ")
            key = key.lower()
            value = value.strip()
            if key == "model":
                self.ddb["model"] = value
            elif key == "charset":
                # Still accepted, so that sources written before this compile,
                # and it chooses nothing: the character set is worked out from
                # the text itself, one code and one glyph for every character
                # the adventure uses, and an accented letter is built out of
                # the adventure's own font.  See regac/glyphs.py.
                self.charset = value
            elif key == "start":
                self.ddb["init_loc"] = int(value)
            elif key == "width":
                self.width = int(value)
            elif key == "punct":
                self.ddb["punctuation"] = parse_strings(value)
            elif key == "sep":
                self.ddb["separators"] = parse_strings(value)
            elif key == "nothing":
                self.ddb["no_objs_msg"] = parse_strings(value)[0]
            else:
                self.fail(f"unknown /CTL setting {key!r}")

    def voc(self):
        buckets = {"verb": "verbs", "noun": "nouns", "adverb": "adverbs"}
        while not self.at_section():
            st = strip_comment(self.cur()).strip()
            self.i += 1
            if not st:
                continue
            parts = st.split()
            if len(parts) != 3:
                self.fail("a vocabulary entry is: word id type")
            word, wid, kind = parts[0], int(parts[1]), parts[2].lower()
            if kind not in buckets:
                self.fail(f"unknown word type {kind!r}")
            if kind == "noun" and wid == 255:
                self.ddb["pronouns"].append(word)
            else:
                self.ddb[buckets[kind]][word] = wid

    def entries(self):
        """Yield (id, header remainder, text lines) for a #-keyed section."""
        while not self.at_section():
            st = self.cur().strip()
            if not st or st.startswith(";"):
                self.i += 1
                continue
            if not st.startswith("#"):
                self.fail(f"expected an entry starting with #, found {st[:32]!r}")
            head = strip_comment(st[1:]).split(None, 1)
            eid = int(head[0])
            rest = head[1] if len(head) > 1 else ""
            self.i += 1
            body = []
            while not self.at_section() and not self.cur().strip().startswith("#"):
                body.append(self.cur())
                self.i += 1
            yield eid, rest, body

    def msg(self):
        for mid, _, body in self.entries():
            self.ddb["messages"][mid] = join_text(text_of(b) for b in body)

    @staticmethod
    def attrs(rest):
        out = {}
        for part in rest.split():
            key, _, value = part.partition("=")
            out[key.lower()] = value
        return out

    def obj(self):
        for oid, rest, body in self.entries():
            a = self.attrs(rest)
            start = a.get("start", "0")
            start = {"nowhere": NOWHERE, "carried": CARRIED}.get(start, start)
            self.ddb["objects"][oid] = {
                "weight": int(a.get("weight", 0)),
                "initial_loc": int(start),
                "name": join_text(text_of(b) for b in body),
            }

    def loc(self, head):
        parts = strip_comment(head).split()
        if len(parts) < 2 or not parts[1].startswith("#"):
            self.fail("a location header is: /LOC #id [gfx=n]")
        lid = int(parts[1][1:])
        a = self.attrs(" ".join(parts[2:]))
        self.i += 1
        desc = []
        while not self.at_section():
            desc.append(text_of(self.cur()))
            self.i += 1
        self.ddb["locations"][lid] = {
            "graphic_id": int(a.get("gfx", 0)),
            "exits": [],
            "desc": join_text(desc),
        }
        while not self.eof():
            tag = self.cur().strip().split()[0].upper()
            if tag == "/CONN":
                self.i += 1
                self.conn(lid)
            elif tag == "/LOCAL":
                self.i += 1
                code = self.cond_lines()
                if code:
                    self.ddb["lcs"][lid] = code
            else:
                break

    def conn(self, lid):
        exits = []
        while not self.at_section():
            st = strip_comment(self.cur()).strip()
            self.i += 1
            if not st:
                continue
            parts = st.split()
            if len(parts) != 2:
                self.fail("a connection is: direction destination")
            exits.append((parts[0], int(parts[1])))
        if exits:
            self.pending_exits[lid] = exits

    def cond_lines(self):
        code = []
        while not self.at_section():
            st = strip_comment(self.cur()).strip()
            lineno = self.i + 1
            self.i += 1
            if not st:
                continue
            try:
                code.extend(compile_line(st))
            except CompileError as e:
                raise SourceError(f"{self.name}:{lineno}: {e}") from None
        return code

    def conds(self, key):
        self.ddb[key] = self.cond_lines()

    def gfx(self):
        for gid, _, body in self.entries():
            insts = []
            for raw in body:
                st = strip_comment(raw).strip()
                if not st:
                    continue
                parts = st.split()
                cmd = parts[0].upper()
                if cmd not in GFX_CMDS:
                    self.fail(f"unknown graphics command {cmd!r}")
                argc = GFX_CMDS[cmd][1]
                if len(parts) - 1 != argc:
                    self.fail(f"{cmd} takes {argc} arguments")
                insts.append([cmd] + [int(p) for p in parts[1:]])
            self.ddb["gfx"][gid] = insts

    def music(self):
        """The tunes this adventure has, one to a line, in the order MUSIC
        counts them: the file the tracker exported and which of its subsongs
        to play, which is nought unless it says otherwise.

            /MUSIC
            menu.akm.asm     0
            menu.akm.asm     1
            cueva.akm.asm

        The file is relative to this source, and is not read here: it is
        assembly, and what reads it is the assembler.  `regac build` writes
        the little source that includes them all in the right shape.
        """
        tunes = self.ddb.setdefault("music", [])
        while not self.eof() and not self.cur().lstrip().startswith("/"):
            line = strip_comment(self.cur()).strip()
            self.i += 1
            if not line:
                continue
            pieces = line.split()
            subsong = 0
            if len(pieces) > 1:
                if not pieces[-1].isdigit():
                    self.fail(f"a tune is a file and a subsong: {line!r}")
                subsong = int(pieces[-1])
                pieces = pieces[:-1]
            tunes.append({"file": " ".join(pieces), "subsong": subsong})

    def font(self):
        """A typeface of the author's own, given whole or a letter at a time.

        A whole one is a file: a dump of eight bytes a character, a console
        font, a C64 charset with its load address, or a PNG of the letters in
        a grid -- fontfile.py works out which and where its first letter
        stands, and `first` and `order` are there for when it cannot.  `file`
        is relative to this source.

        A letter at a time is the entries below it, which win over the file so
        that one glyph can be changed without redrawing the rest.  A letter is
        named by its number or by itself: #241 and #"Ñ" are the same.
        """
        head = self.lines[self.i - 1]
        a = self.attrs(" ".join(strip_comment(head).split()[1:]))
        self.font_chars = int(a.get("chars", 128))
        data = [0] * (self.font_chars * 8)
        whole = a.get("file")
        if whole:
            path = os.path.join(self.folder, whole.strip('"'))
            first = int(a["first"]) if "first" in a else None
            try:
                glyphs = fontfile.read(
                    path, first,
                    a.get("order", "ascii").strip(QUOTES),
                    a["layout"].strip(QUOTES) if "layout" in a else None,
                )
            except (OSError, FontError, ImageError) as trouble:
                self.fail(f"the font {whole}: {trouble}")
            for code, glyph in glyphs.items():
                data = self.room_for(data, code * 8 + 8)
                data[code * 8 : code * 8 + 8] = glyph
        while not self.at_section():
            st = strip_comment(self.cur()).strip()
            self.i += 1
            if not st:
                continue
            if not st.startswith("#"):
                self.fail("a font entry is: #code followed by 8 hex bytes")
            parts = st[1:].split()
            code = self.char_code(parts[0])
            row = [int(b, 16) for b in parts[1:]]
            if len(row) != 8:
                self.fail(f"character {code} needs 8 bytes, found {len(row)}")
            data = self.room_for(data, code * 8 + 8)
            data[code * 8 : code * 8 + 8] = row
        self.font_chars = len(data) // 8
        self.ddb["font"] = data

    def room_for(self, data, size):
        """Let the table reach a character beyond the ones declared: an
        accented letter drawn by hand lives past the first hundred and
        twenty eight, and saying so twice would be a way of getting it wrong.
        """
        if size > len(data):
            data = data + [0] * (size - len(data))
        return data

    def char_code(self, word):
        """A character named by its number, or by itself in quotes."""
        if word.startswith('"') or word.startswith("'"):
            letter = word.strip("\"'")
            if len(letter) != 1:
                self.fail(f"{word} is not one character")
            return ord(letter)
        return int(word)


def parse(text, name="adventure", folder=None):
    return Parser(text, name, folder).parse()
