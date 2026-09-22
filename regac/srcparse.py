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
import re

from . import fontfile
from .conds import CompileError, compile_line, nearest
from .fontfile import FontError
from .png import ImageError

QUOTES = "'\""
from .opcodes import BY_NAME, GFX_CMDS
from .text import INK_COLOURS

NOWHERE = 0
CARRIED = 255
DEFAULT_CHARSET = "ascii"
DEFAULT_WIDTH = 32
FONT_PREFIX = 8 * 32  # deGAC always prefixes the font with 32 blank characters

UNESCAPE = {"0": "\0", "n": "\n", "t": "\t", '"': '"', "\\": "\\"}

# What a noise comes out of.  A sound chip has a tone generator and a noise
# generator and can use either or both; a speaker of one bit has neither, and
# what it does with any of the three is flip as fast as the pitch says.  So
# this changes what is heard where there is a chip and changes nothing where
# there is not, which is why an adventure may use it freely.
TONE, NOISE, BOTH = 0, 1, 2
SOUND_CHANNELS = {"tone": TONE, "noise": NOISE, "both": BOTH}
SOUND_CHANNEL_NAMES = {number: word for word, number in SOUND_CHANNELS.items()}


def a_noise(said):
    """A noise as it is kept: four numbers, whatever shape it came in.

    Three is how they were written before there was a fourth, and an
    adventure decompiled or built then still reads: a noise that does not say
    what it comes out of is a tone."""
    kept = list(said)
    return kept + [TONE] * (4 - len(kept))



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
    unless the previous one ends in a backslash, which joins with nothing.

    An empty line is nothing at all: an author puts one there to see the text
    better, and a line kept back for another machine leaves one behind.
    Neither is a space in what gets printed -- but a line with a space on it
    is that space, because an adventure of the eight really does have a
    description that is one.
    """
    lines = [line for line in lines if line != ""]
    if not lines:
        return ""
    out = lines[0]
    for line in lines[1:]:
        if out.endswith("\\"):
            out = out[:-1] + line
        else:
            out = out + " " + line
    return out


def pointed(name, lineno, message, line=None, column=None, meant=None):
    """A mistake, where it happened, and the line with a finger on it.

    The line and the finger are worth the three lines they take: an adventure
    is thousands of lines long and a message that only gives a number makes
    the author count.  What is said is the same shape every time, so that
    whatever reads it -- a person, an editor -- can find its way.
    """
    if meant:
        message = f"{message} -- did you mean {meant}?"
    out = [f"{name}:{lineno}: {message}"]
    if line is not None and line.strip():
        out.append("    " + line.rstrip())
        if column:
            out.append("    " + " " * (column - 1) + "^")
    return "\n".join(out)


def text_of(line):
    """A line of adventure text, with the marker escape removed."""
    return line[1:] if line.startswith("|") else line


# ---------------------------------------------------------------------------
# What is only for some machines
# ---------------------------------------------------------------------------

# An adventure is one source and eight machines, and now and then the eight do
# not want the same thing: a Spectrum of 48K may have to do without the
# pictures that fit everywhere else, an Amstrad's colours are four pens rather
# than sixteen colours, and the PCW is monochrome and has nothing to sound
# with.  So a source may keep lines back:
#
#       .if cpc msx
#       El mando hace un ruido seco.
#       .else
#       El mando hace un ruido seco y la pantalla parpadea.
#       .end
#
# It is the plainest kind of conditional and it is resolved when the source is
# read, not when the adventure is played: what a machine is not to have never
# reaches its database, which is the whole point on the machines where room is
# what runs out first.
#
# What may be named is the machine, and the family it belongs to for the ones
# that have a family.  A name that is not here is a mistake and is said,
# because a typo that quietly drops half an adventure is the worst kind.
MACHINE_LABELS = {
    "spectrum48": ("spectrum48", "spectrum"),
    "spectrum128": ("spectrum128", "spectrum"),
    "plus3": ("plus3", "spectrum128", "spectrum"),
    "cpc": ("cpc", "amstrad"),
    # The two Amstrads of the target table are the same machine to a source
    # that only wants to know what it is writing for, so both answer to cpc
    # as well as to their own name: a 464 has a tape and sixty four
    # kilobytes, a 6128 a disk and another sixty four.
    "cpc464": ("cpc464", "cpc", "amstrad"),
    "cpc6128": ("cpc6128", "cpc", "amstrad"),
    "pcw": ("pcw", "amstrad"),
    "msx": ("msx",),
    "msx2": ("msx2", "msx"),
    "next": ("next",),
    "sam": ("sam",),
}
EVERY_LABEL = {label for labels in MACHINE_LABELS.values() for label in labels}

IF = ".if"
ELSE = ".else"
END = ".end"
DEF = ".def"
INCLUDE = ".include"
DIRECTIVES = (IF, ELSE, END, DEF, INCLUDE)

# What a name may look like, which is what an assembler would allow: letters,
# digits and underscores, and not beginning with a digit.
NAME = re.compile(r"[A-Za-z_]\w*$")
MOST_INCLUDES = 16              # deep enough for anybody, shallow enough to
                                # catch a file that takes itself in


def directive(line):
    """The word a line begins with, when it is one of ours."""
    first = line.strip().split(";", 1)[0].split()
    if first and first[0].lower() in DIRECTIVES:
        return first[0].lower()
    return None


def words_of(line):
    """What a directive line says, without its comment."""
    return line.strip().split(";", 1)[0].split()


def read_source(text, name, folder, machine, defs=None, lines=None,
                origins=None, seen=()):
    """Everything that happens to a source before a section has seen it.

    Three things, and they are done in one pass because they are the same
    kind of thing: lines kept back for other machines, names given to numbers,
    and files taken in.  What comes back is the lines, where each of them
    came from, and the names.

    The lines kept back are blanked rather than thrown away, and every line
    remembers the file and the number it had there, so that a mistake in a
    file that was included says that file and that line.
    """
    labels = set(MACHINE_LABELS.get(machine, ())) if machine else set()
    lines = [] if lines is None else lines
    origins = [] if origins is None else origins
    defs = {} if defs is None else defs
    keeping = []                   # a stack of (taking, taken already)

    def keep(line, number):
        lines.append(line)
        origins.append((name, number))

    for number, line in enumerate(text.splitlines(), 1):
        word = directive(line)
        taking = all(t for t, _ in keeping)
        if word is None:
            keep(line if taking else "", number)
            continue
        if word == DEF:
            if taking:
                said = words_of(line)
                if len(said) != 3:
                    raise SourceError(pointed(
                        name, number, ".def gives a name to a number: "
                        ".def PUERTA_ABIERTA 5", line))
                _, given, value = said
                if not NAME.match(given):
                    raise SourceError(pointed(
                        name, number,
                        f"{given!r} is not a name: letters, digits and "
                        f"underscores, and not starting with a digit",
                        line, line.find(given) + 1))
                if given in BY_NAME or given.upper() in GFX_CMDS:
                    raise SourceError(pointed(
                        name, number,
                        f"{given!r} is a word of the language already",
                        line, line.find(given) + 1))
                try:
                    defs[given] = int(value, 0)
                except ValueError:
                    if value not in defs:
                        raise SourceError(pointed(
                            name, number,
                            f"{value!r} is neither a number nor a name given "
                            f"to one", line, line.find(value) + 1,
                            nearest(value, defs))) from None
                    defs[given] = defs[value]
            keep("", number)
            continue
        if word == INCLUDE:
            if taking:
                said = words_of(line)
                if len(said) != 2:
                    raise SourceError(pointed(
                        name, number,
                        '.include takes one file: .include "comun.gac"', line))
                wanted = said[1].strip('"\'')
                whole = os.path.normpath(os.path.join(folder, wanted))
                if len(seen) >= MOST_INCLUDES or whole in seen:
                    raise SourceError(pointed(
                        name, number,
                        f"{wanted} is being included from itself", line))
                try:
                    with open(whole, encoding="utf-8") as f:
                        inside = f.read()
                except OSError as e:
                    raise SourceError(pointed(
                        name, number, f"{wanted} cannot be read: {e.strerror}",
                        line)) from None
                keep("", number)
                read_source(inside, os.path.basename(whole),
                            os.path.dirname(whole) or ".", machine, defs,
                            lines, origins, tuple(seen) + (whole,))
                continue
            keep("", number)
            continue
        if word == IF:
            wanted = words_of(line)[1:]
            if not wanted:
                raise SourceError(f"{name}:{number}: .if what?  Name a machine")
            strange = [w for w in wanted if w.lower() not in EVERY_LABEL]
            if strange:
                meant = nearest(strange[0], EVERY_LABEL)
                said = f"there is no machine called {strange[0]!r}"
                if not meant:       # no guess, so say what there is instead
                    said += "; what there is: " + ", ".join(sorted(EVERY_LABEL))
                raise SourceError(pointed(name, number, said, line,
                                          line.find(strange[0]) + 1, meant))
            if machine is None:
                raise SourceError(
                    f"{name}:{number}: this source keeps some lines for some "
                    f"machines, so it has to be read for one of them: say "
                    f"which with -m"
                )
            keeping.append([any(w.lower() in labels for w in wanted)] * 2)
        elif word == ELSE:
            if not keeping:
                raise SourceError(f"{name}:{number}: .else without .if")
            was, taken = keeping[-1]
            keeping[-1] = [not taken, True]
        else:
            if not keeping:
                raise SourceError(f"{name}:{number}: .end without .if")
            keeping.pop()
        keep("", number)
    if keeping:
        raise SourceError(f"{name}: a .if was never ended")
    return lines, origins, defs


def for_machine(text, machine=None, name="adventure"):
    """Just the lines, for anything that only wants to see what a machine
    gets."""
    lines, _, _ = read_source(text, name, ".", machine)
    return "\n".join(lines)


class Parser:
    def __init__(self, lines, origins=None, defs=None, name="adventure",
                 folder=None):
        self.lines = list(lines)
        # Where each line came from, which is not always this file: a line of
        # an included one says so, and says its own number there.
        self.origins = list(origins) if origins else [
            (name, n) for n in range(1, len(self.lines) + 1)]
        self.defs = dict(defs or {})    # the names given to numbers
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

    def fail(self, msg, column=None, meant=None, lineno=None, line=None):
        """Stop, saying where and showing the line.

        Most of the time the line at fault is the one being read; the sections
        that take a whole entry at once know better and say which.  What is
        said is where the author wrote it, which for an included file is that
        file and its own numbering.
        """
        if lineno is None:
            lineno = self.i + 1
        if line is None:
            line = self.lines[lineno - 1] if lineno <= len(self.lines) else None
        where, number = self.where_from(lineno)
        raise SourceError(pointed(where, number, msg, line, column, meant))

    def where_from(self, lineno):
        """The file and the line number a line of ours was written at."""
        if 1 <= lineno <= len(self.origins):
            return self.origins[lineno - 1]
        return self.name, lineno

    def number(self, word, what="a number", lineno=None, line=None):
        """A number, written as one or as a name that was given to one.

        The line is worth passing where the section has it: a loop that has
        already stepped on knows which line it was reading and the finger goes
        under the word rather than nowhere.
        """
        try:
            return int(str(word), 0)
        except ValueError:
            pass
        if word in self.defs:
            return self.defs[word]
        column = self.starts_at(line, str(word)) if line is not None else None
        self.fail(f"{word!r} is not {what}, and no .def gives it one",
                  column=column, meant=nearest(word, self.defs),
                  lineno=lineno, line=line)

    @staticmethod
    def starts_at(line, word=None):
        """The column a word begins at, or the first thing on the line."""
        if word:
            at = line.find(word)
            if at >= 0:
                return at + 1
        return len(line) - len(line.lstrip()) + 1

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
            "/SOUND": self.sound,
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
                known = list(handlers) + ["/LOC"]
                self.fail(f"there is no section called {tag}",
                          column=self.starts_at(self.cur()),
                          meant=nearest(tag, known))
            self.i += 1
            handler()
        self.finish()
        return self.ddb

    def finish(self):
        for lid, exits in self.pending_exits.items():
            resolved = []
            for word, dest in exits:
                if word.isdigit() or word in self.defs:
                    vid = self.number(word, "a verb")
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
            raw, lineno = self.cur(), self.i + 1
            st = strip_comment(raw).strip()
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
                self.ddb["init_loc"] = self.number(
                    value, "a room", lineno, raw)
            elif key == "width":
                self.width = self.number(value, "a number",
                                         lineno, raw)
            elif key == "punct":
                self.ddb["punctuation"] = parse_strings(value)
            elif key == "sep":
                self.ddb["separators"] = parse_strings(value)
            elif key == "ink":
                # The colour this adventure's text is printed in, one of the
                # Spectrum's sixteen as everywhere else.  Nought is not one of
                # them here: on every machine this builds for it is the paper,
                # and text the colour of the paper is no text, so nought is
                # left to mean "nothing said" -- which is what a source that
                # does not give this gets, and then each machine uses its own.
                colour = self.number(value, "a number", lineno, raw)
                if not 1 <= colour <= INK_COLOURS - 1:
                    self.fail(f"{colour} is not an ink: they run from 1 to "
                              f"{INK_COLOURS - 1}, and nought would be the "
                              "colour of the paper", lineno=lineno, line=raw,
                              column=self.starts_at(raw, value))
                self.ddb["ink"] = colour
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
            raw = self.lines[self.i - 1]
            parts = st.split()
            if len(parts) != 3:
                self.fail("a vocabulary entry is: word id type",
                          column=self.starts_at(raw), lineno=self.i,
                          line=raw)
            word, kind = parts[0], parts[2].lower()
            wid = self.number(parts[1], "a number for a word")
            if kind not in buckets:
                self.fail(f"there is no word type called {kind!r}",
                          column=self.starts_at(raw, parts[2]),
                          meant=nearest(kind, buckets), lineno=self.i,
                          line=raw)
            if kind == "noun" and wid == 255:
                self.ddb["pronouns"].append(word)
            else:
                self.ddb[buckets[kind]][word] = wid

    def entries(self):
        """Yield (id, header remainder, text lines, first line number).

        The line number is the body's first, because a section that takes a
        whole entry at once has read past it by the time anything in it turns
        out to be wrong.
        """
        while not self.at_section():
            st = self.cur().strip()
            if not st or st.startswith(";"):
                self.i += 1
                continue
            if not st.startswith("#"):
                self.fail(f"expected an entry starting with #, found {st[:32]!r}")
            head = strip_comment(st[1:]).split(None, 1)
            eid = self.number(head[0], "the number of an entry")
            rest = head[1] if len(head) > 1 else ""
            self.i += 1
            body = []
            first = self.i + 1
            while not self.at_section() and not self.cur().strip().startswith("#"):
                body.append(self.cur())
                self.i += 1
            yield eid, rest, body, first

    def msg(self):
        for mid, _, body, _first in self.entries():
            self.ddb["messages"][mid] = join_text(text_of(b) for b in body)

    @staticmethod
    def attrs(rest):
        out = {}
        for part in rest.split():
            key, _, value = part.partition("=")
            out[key.lower()] = value
        return out

    def obj(self):
        for oid, rest, body, _first in self.entries():
            a = self.attrs(rest)
            start = a.get("start", "0")
            start = {"nowhere": NOWHERE, "carried": CARRIED}.get(start, start)
            self.ddb["objects"][oid] = {
                "weight": self.number(a.get("weight", 0), "a weight"),
                "initial_loc": self.number(start, "a room"),
                "name": join_text(text_of(b) for b in body),
            }

    def loc(self, head):
        parts = strip_comment(head).split()
        if len(parts) < 2 or not parts[1].startswith("#"):
            self.fail("a location header is: /LOC #id [gfx=n]")
        lid = self.number(parts[1][1:], "the number of a room")
        a = self.attrs(" ".join(parts[2:]))
        self.i += 1
        desc = []
        while not self.at_section():
            desc.append(text_of(self.cur()))
            self.i += 1
        self.ddb["locations"][lid] = {
            "graphic_id": self.number(a.get("gfx", 0), "a picture"),
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
            exits.append((parts[0], self.number(parts[1], "a room")))
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
            raw = self.lines[lineno - 1]
            try:
                code.extend(compile_line(st, self.defs))
            except CompileError as e:
                # The compiler counts the columns of what it was given, which
                # is the line with its comment cut off and its indent gone, so
                # the finger is put back where the author sees it.
                column = None
                if e.column:
                    column = self.starts_at(raw) + e.column - 1
                raise SourceError(
                    pointed(self.name, lineno, e.message, raw, column, e.meant)
                ) from None
        return code

    def conds(self, key):
        self.ddb[key] = self.cond_lines()

    def gfx(self):
        for gid, _, body, first in self.entries():
            insts = []
            for number, raw in enumerate(body):
                st = strip_comment(raw).strip()
                if not st:
                    continue
                lineno = first + number
                parts = st.split()
                cmd = parts[0].upper()
                if cmd not in GFX_CMDS:
                    self.fail(f"there is no drawing command called {cmd!r}",
                              column=self.starts_at(raw, parts[0]),
                              meant=nearest(cmd, GFX_CMDS),
                              lineno=lineno, line=raw)
                argc = GFX_CMDS[cmd][1]
                if len(parts) - 1 != argc:
                    many = "one number" if argc == 1 else f"{argc} numbers"
                    self.fail(f"{cmd} takes {many}, and here it has "
                              f"{len(parts) - 1}",
                              column=self.starts_at(raw, parts[0]),
                              lineno=lineno, line=raw)
                insts.append([cmd] + [self.number(p, "a number for a "
                                                  "drawing command")
                                      for p in parts[1:]])
            self.ddb["gfx"][gid] = insts

    def sound(self):
        """The noises this adventure asks for: one to a line, in the order
        SOUND counts them from one.

            /SOUND
            ; pitch  steps  step  out of
                200    150     -1          ; cogido
                250    100      0  both    ; una puerta
                 30    110      2  noise   ; una caida

        A pitch is how long half a wave lasts and a bigger one is a lower
        note; the step is what to add to it every time, so a step that takes
        the pitch down takes the note up.  An adventure that says nothing here
        gets five that come with the interpreter.

        The fourth is what it comes out of, and it may be left off: `tone` is
        a note, `noise` is the hiss the sound chip makes with no note in it,
        and `both` is the two together.  A door, a fall and a stab of alarm
        are not notes, and a chip can say so where a speaker of one bit can
        only sweep a note and hope.  **The Spectrum 48 has no chip**, and
        there the word is read and the tone played, so an adventure that uses
        it still runs everywhere -- it just sounds better where there is
        something to sound it with.
        """
        noises = self.ddb.setdefault("sounds", [])
        while not self.at_section():
            raw, lineno = self.cur(), self.i + 1
            said = strip_comment(raw).strip()
            self.i += 1
            if not said:
                continue
            parts = said.split()
            if not 3 <= len(parts) <= 4:
                self.fail("a noise is: pitch steps step, and then tone, noise "
                          "or both, which may be left off", lineno=lineno,
                          line=raw, column=self.starts_at(raw))
            out_of = TONE
            if len(parts) == 4:
                word = parts[3].lower()
                if word not in SOUND_CHANNELS:
                    self.fail(f"{parts[3]} is not what a noise comes out of: "
                              "it is tone, noise or both", lineno=lineno,
                              line=raw, column=self.starts_at(raw, parts[3]))
                out_of = SOUND_CHANNELS[word]
            pitch, steps, step = (self.number(p, "a number", lineno, raw)
                                  for p in parts[:3])
            for value, what, low, high in ((pitch, "a pitch", 1, 255),
                                           (steps, "a length", 1, 255),
                                           (step, "a step", -128, 127)):
                if not low <= value <= high:
                    self.fail(f"{value} is not {what}: they run from {low} to "
                              f"{high}", lineno=lineno, line=raw,
                              column=self.starts_at(raw, str(value)))
            noises.append([pitch, steps, step, out_of])

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


def parse(text, name="adventure", folder=None, machine=None):
    """An adventure, read for one machine.

    The machine matters only to a source that keeps some lines for some of
    them; one that does not is the same adventure whoever asks.
    """
    folder = folder or "."
    lines, origins, defs = read_source(text, name, folder, machine)
    return Parser(lines, origins, defs, name, folder).parse()
