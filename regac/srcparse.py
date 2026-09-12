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
"""Reader for the ReGAC source format: source text -> database dictionary."""

from .conds import CompileError, compile_line
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
    def __init__(self, text, name="adventure"):
        self.lines = text.splitlines()
        self.i = 0
        self.name = name
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
            "separators": ["then", "and"],
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

    def font(self):
        head = self.lines[self.i - 1]
        a = self.attrs(" ".join(strip_comment(head).split()[1:]))
        self.font_chars = int(a.get("chars", 128))
        data = [0] * (self.font_chars * 8)
        while not self.at_section():
            st = strip_comment(self.cur()).strip()
            self.i += 1
            if not st:
                continue
            if not st.startswith("#"):
                self.fail("a font entry is: #code followed by 8 hex bytes")
            parts = st[1:].split()
            code = int(parts[0])
            row = [int(b, 16) for b in parts[1:]]
            if len(row) != 8:
                self.fail(f"character {code} needs 8 bytes, found {len(row)}")
            data[code * 8 : code * 8 + 8] = row
        self.ddb["font"] = data


def parse(text, name="adventure"):
    return Parser(text, name).parse()
