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
"""How an adventure's text is stored.

Two layers that know nothing about each other.

The character set gives every character the adventure uses a code, which is
also its place in the font.  Nothing reserves codes for an alphabet the
adventure does not use, so an accent costs exactly what a letter costs and
Spanish, Catalan or Portuguese need no special case.  This is where
compatibility with the original is given up: GAC packed characters into seven
bits, used the eighth to mark the end of a word and manipulated a bit to
change case, which left no room for accented letters at all.

Above that, the text is compressed by pairing.  The commonest pair of codes is
replaced by a spare code, over and over, so a single code can end up standing
for a long run of characters.  Two things recommend it over the alternatives
on an eight bit machine.  Unpacking is a table lookup and a small stack, with
no bit shuffling, and every message unpacks on its own without touching the
ones before it, which is what the interpreter needs to print message 137 and
nothing else.
"""

import collections
import re

from .i18n import _
import unicodedata

MAX_CODES = 256

# Where every character stands.  The place a character has in this list is its
# code, and that is the same in every adventure, whatever it is written in.
#
# It is fixed on purpose.  Numbering the characters by use, which is what this
# did before, left the compressor whatever codes the alphabet had not taken --
# so an adventure written in Spanish had fewer pairs than one written without
# accents, and one in Catalan fewer still.  A language should not be a
# handicap.  Fixed, everybody gets the same 128 pairs, and a font is a sheet
# of the same letters in the same places, which is a thing an artist can draw
# once and use again.
#
# The first two codes are not characters and never will be.  Nought is the
# null, so that a zero byte in a stream of text can only ever mean nothing at
# all; one is a change of colour, for when a message wants to say a
# word in another ink.
#
# The capitals of the accented vowels are here even though the Academy lets
# them go unaccented, because a title looks wrong without them.  What is not
# here cannot be used, and the build says so rather than printing a blank.
NULL_CODE = 0
INK_CODE = 1                            # a change of ink; the code after it
                                        # says which, and see below
SPECIALS_FIRST = 2
SPECIALS = (
    "áéíóúüñ"           #  2-8   Spanish, in small letters
    "ÁÉÍÓÚÜÑ"           #  9-15  and in capitals
    "¿¡"                # 16-17  the two it opens with
    "çÇ"                # 18-19  the one its neighbours add to the alphabet
    "àèòïãõâêô"         # 20-28  and the accents they put on the rest
    "ªº—"               # 29-31  the ordinals, and the dash a dialogue opens
)
ASCII_FIRST = 32                        # and from the space up it is ASCII
ASCII_LAST = 127                        # to the copyright sign these machines
                                        # keep at the end of it
FIRST_PAIR = 128                        # everything above is the compressor's
PAIRS = MAX_CODES - FIRST_PAIR

assert SPECIALS_FIRST + len(SPECIALS) <= ASCII_FIRST, "too many to fit below the space"


# A change of ink, as it is written in a source and as it travels.
#
# In the source it is a command inside the text itself, `\ink 5`, because that
# is where it belongs: what is red is a word of a sentence and not a property
# of the whole message.  The spaces after it are eaten, as they are after a
# command in any other language of this kind, so that `rojo \ink 2 y negro`
# has one space between its words and not two.  A backslash of one's own is
# written `\\`.
#
# What it turns into is two codes: INK_CODE, and then the colour -- and the
# colour rides as a printable character, nought being `0` and fifteen `?`,
# for a reason worth the oddity.  The compressor pairs codes, and a colour
# carried as a raw number would be a code below the space, which is where the
# letters ASCII has not got live; carried as a character it is an ordinary
# code like any other, so a change of ink packs and unpacks along with the
# text around it and nothing in the compressor knows it is there.
#
# The colours are the Spectrum's sixteen, as they are in the pictures: eight
# and above is the same colour bright.  Every machine reads them its own way.
INK_CHAR = "\x01"
INK_ARG_FIRST = ord("0")
INK_COLOURS = 16

# And a hole: something the text says that is only known when it is printed.
# `\ctr n` is what counter n holds, `\obj n` the name of object n and
# `\turns` the turns played, which take two counters.  There is no code left
# below the space for them -- nought is the null, one the ink and the rest
# are letters -- so they ride behind INK_CODE as well, with a letter the
# colours do not use to say which, and a number as two characters of four
# bits each, the way a colour rides and for the same reason: so that they
# pack like any other text.  Unlike a change of ink, a hole is text, so the
# spaces after it are kept: `\ctr 0 puntos` is a number, a space and a word.
HOLE_TURNS = "T"
HOLE_COUNTER = "C"
HOLE_OBJECT = "O"
COUNTERS = 128
OBJECTS = 256

COMMAND = re.compile(r"\\(?:(\\)|ink[ \t]*(\d{1,2})[ \t]*"
                     r"|(ctr|obj)[ \t]*(\d{1,3})|(turns)|(.))", re.S)


def number_chars(value):
    """A number of eight bits as the two characters it rides as."""
    return chr(INK_ARG_FIRST + (value >> 4)) + chr(INK_ARG_FIRST + (value & 15))


def command_at(text, at):
    """The command that starts at `at` of expanded text: what it is, the
    number it carries, and how many characters it takes."""
    which = text[at + 1]
    if which in (HOLE_COUNTER, HOLE_OBJECT):
        value = ((ord(text[at + 2]) - INK_ARG_FIRST) << 4
                 | (ord(text[at + 3]) - INK_ARG_FIRST))
        return which, value, 4
    if which == HOLE_TURNS:
        return which, None, 2
    return INK_CHAR, ord(which) - INK_ARG_FIRST, 2


def expand(text):
    """Text as it is written, with its commands turned into what they travel
    as."""
    def one(found):
        if found.group(1):
            return "\\"
        if found.group(2) is not None:
            colour = int(found.group(2))
            if colour >= INK_COLOURS:
                raise ValueError(_(
                    "\\ink {colour} asks for a colour there is not: they run "
                    "from 0 to {last}", colour=colour, last=INK_COLOURS - 1))
            return INK_CHAR + chr(INK_ARG_FIRST + colour)
        if found.group(3):
            value = int(found.group(4))
            if found.group(3) == "ctr":
                if value >= COUNTERS:
                    raise ValueError(_(
                        "\\ctr {value} asks for a counter there is not: they "
                        "run from 0 to {last}", value=value, last=COUNTERS - 1))
                return INK_CHAR + HOLE_COUNTER + number_chars(value)
            if not 1 <= value < OBJECTS:
                raise ValueError(_(
                    "\\obj {value} asks for an object there cannot be: they "
                    "run from 1 to {last}", value=value, last=OBJECTS - 1))
            return INK_CHAR + HOLE_OBJECT + number_chars(value)
        if found.group(5):
            return INK_CHAR + HOLE_TURNS
        raise ValueError(_("\\{command} is not a text command",
                           command=found.group(6)))
    return COMMAND.sub(one, text)


def written(text):
    """The other way about: expanded text, as it would be written in a
    source."""
    out = []
    at = 0
    while at < len(text):
        char = text[at]
        if char == INK_CHAR:
            which, value, size = command_at(text, at)
            out.append({INK_CHAR: rf"\ink {value} ",
                        HOLE_COUNTER: rf"\ctr {value}",
                        HOLE_OBJECT: rf"\obj {value}",
                        HOLE_TURNS: r"\turns"}[which])
            at += size
            continue
        out.append("\\\\" if char == "\\" else char)
        at += 1
    return "".join(out)


def plain(text):
    """And what is left when the commands come out, which is what anything
    that only wants the letters should look at."""
    out = []
    at = 0
    while at < len(text):
        if text[at] == INK_CHAR:
            at += command_at(text, at)[2]
            continue
        out.append(text[at])
        at += 1
    return "".join(out)


def commands_of(text):
    """Every command of expanded text, as command_at gives it."""
    at = 0
    while at < len(text):
        if text[at] == INK_CHAR:
            found = command_at(text, at)
            yield found
            at += found[2]
        else:
            at += 1


def filled(text, counter, object_name):
    """Expanded text with its holes filled in, and its changes of ink left
    where they are: what a machine prints.  `counter` says what a counter
    holds and `object_name` gives an object's name as it is written, which
    may have holes of its own but not an object's name, which the build does
    not allow.  The turns are the two counters they are kept in, the high
    byte in 127 and the low in 126."""
    out = []
    at = 0
    while at < len(text):
        if text[at] != INK_CHAR:
            out.append(text[at])
            at += 1
            continue
        which, value, size = command_at(text, at)
        if which == INK_CHAR:
            out.append(text[at:at + size])
        elif which == HOLE_COUNTER:
            out.append(str(counter(value)))
        elif which == HOLE_TURNS:
            out.append(str(counter(127) * 256 + counter(126)))
        else:
            out.append(filled(expand(object_name(value)), counter, object_name))
        at += size
    return "".join(out)


def code_of(char):
    """The code a character takes, or None if it has no place at all."""
    if char == INK_CHAR:
        return INK_CODE
    at = SPECIALS.find(char)
    if at >= 0:
        return SPECIALS_FIRST + at
    point = ord(char)
    return point if ASCII_FIRST <= point <= ASCII_LAST else None


def typed(word):
    """A word as a player can actually type it, which is without its marks.

    No keyboard here has a key for an accent, so a vocabulary that says ARAÑA
    could never be matched against anything.  The marks come off the words the
    parser compares -- and only off those: the text keeps every one of them,
    because the text is printed and not typed.
    """
    return "".join(c for c in unicodedata.normalize("NFD", word)
                   if not unicodedata.combining(c))


class Charset:
    """Which of the fixed codes an adventure actually uses.

    The codes themselves are not this class's to decide -- they are the same
    in every adventure, and `code_of` says what they are.  What is worked out
    here is the stretch of them the font has to carry: from the lowest the
    adventure uses to the highest, holes and all, because the font travels as
    a run of glyphs with a code to start it.
    """

    def __init__(self, texts, extra=()):
        used = set()
        for text in texts:
            used.update(text)
        # Characters that need a code and a glyph but are never packed: the
        # vocabulary is matched against what the player types, not printed.
        for text in extra:
            used.update(text)
        stranger = sorted(c for c in used if code_of(c) is None)
        if stranger:
            raise ValueError(_(
                "there is no place in the character set for {some} ({all} in "
                "all); what fits is ASCII and {specials!r}",
                some=", ".join(f"{c!r}" for c in stranger[:8]),
                all=len(stranger), specials=SPECIALS))
        self.codes = {c: code_of(c) for c in sorted(used, key=code_of)}
        self.chars = {code: c for c, code in self.codes.items()}
        # The font carries letters and nothing else.  A change of ink has a
        # code like a letter, so that the compressor can pair it, but it is
        # never drawn -- and if it counted here it would drag the run of
        # glyphs down to code one and make the font carry the thirty blanks in
        # between for nothing.
        glyphs = {code: c for code, c in self.chars.items()
                  if code >= SPECIALS_FIRST}
        self.first = min(glyphs, default=0)
        last = max(glyphs, default=0)
        # The run, holes and all: a hole is a code nothing uses, and what the
        # font carries for it is eight noughts.
        self.order = [glyphs.get(code) for code in range(self.first, last + 1)]

    def __len__(self):
        return len(self.order)

    @property
    def spare(self):
        """How many codes are left for the compressor, which is always the
        same number: that is the whole point of a fixed set."""
        return PAIRS

    def encode(self, text):
        try:
            return bytes(self.codes[c] for c in text)
        except KeyError as e:
            raise KeyError(_("character {char!r} is not in the character set",
                             char=e.args[0]))

    def decode(self, data):
        return "".join(self.chars[b] for b in data)


class Packer:
    """Pair coding: the table of pairs, and the packing and unpacking."""

    def __init__(self, table, first_pair):
        self.table = list(table)  # code - first_pair -> (left, right)
        self.first_pair = first_pair

    def __len__(self):
        return len(self.table)

    @property
    def table_bytes(self):
        return 2 * len(self.table)

    def unpack(self, data):
        """Expand one message.  This mirrors what the 8 bit routine does: walk
        the bytes, and where one stands for a pair push both halves and carry
        on.  Nothing before this message is read."""
        out = bytearray()
        stack = []
        for byte in data:
            stack.append(byte)
            while stack:
                code = stack.pop()
                if code < self.first_pair:
                    out.append(code)
                else:
                    left, right = self.table[code - self.first_pair]
                    stack.append(right)
                    stack.append(left)
        return bytes(out)

    def depth(self):
        """The deepest the unpacking stack ever goes, which is what the 8 bit
        routine has to make room for."""
        cache = {}

        def height(code):
            if code < self.first_pair:
                return 1
            if code in cache:
                return cache[code]
            left, right = self.table[code - self.first_pair]
            cache[code] = 1 + max(height(left), height(right))
            return cache[code]

        return max((height(c) for c in range(self.first_pair + len(self.table))), default=1)


def pack(sequences, first_pair, spare, min_uses=3):
    """Build the pair table for a set of messages and pack them.

    Pairs are only ever counted inside one message, never across two, so the
    messages stay independent of one another.
    """
    seqs = [list(s) for s in sequences]
    table = []
    for code in range(first_pair, first_pair + spare):
        pairs = collections.Counter()
        for s in seqs:
            for i in range(len(s) - 1):
                pairs[(s[i], s[i + 1])] += 1
        if not pairs:
            break
        (left, right), uses = pairs.most_common(1)[0]
        if uses < min_uses:
            break
        table.append((left, right))
        for n, s in enumerate(seqs):
            out = []
            i = 0
            limit = len(s) - 1
            while i < len(s):
                if i < limit and s[i] == left and s[i + 1] == right:
                    out.append(code)
                    i += 2
                else:
                    out.append(s[i])
                    i += 1
            seqs[n] = out
    return Packer(table, first_pair), [bytes(s) for s in seqs]


class TextStore:
    """An adventure's text, ready to be written out for a machine."""

    def __init__(self, texts, extra=()):
        # The commands an author writes inside the text become codes here, at
        # the one door every text comes through, so that nothing further in
        # has to know they were ever written differently.
        texts = [expand(text) for text in texts]
        self.charset = Charset(texts, extra)
        encoded = [self.charset.encode(t) for t in texts]
        self.packer, self.messages = pack(encoded, FIRST_PAIR, PAIRS)
        self.raw_size = sum(len(t) for t in encoded)

    @property
    def packed_size(self):
        return sum(len(m) for m in self.messages)

    @property
    def total_size(self):
        return self.packed_size + self.packer.table_bytes

    @property
    def ratio(self):
        return self.total_size / self.raw_size if self.raw_size else 1.0

    def read(self, index):
        """Get one message back, the way the interpreter will."""
        return self.charset.decode(self.packer.unpack(self.messages[index]))
