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
import unicodedata

MAX_CODES = 256


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
    """The codes an adventure's characters take in the font.

    Characters are numbered by how much they are used, so the commonest come
    first.  That is not for the compressor, which does not care, but so that a
    machine short of font memory can hold the useful glyphs and drop the tail.
    """

    def __init__(self, texts, first=0, extra=()):
        counts = collections.Counter()
        for text in texts:
            counts.update(text)
        # Characters that need a code and a glyph but are never packed: the
        # vocabulary is matched against what the player types, not printed.
        for text in extra:
            for char in text:
                counts.setdefault(char, 0)
        self.order = [c for c, _ in counts.most_common()]
        # A code is a byte, and the ones the character set does not take are
        # what the compressor has to work with.  Saying so here is better than
        # letting it come out as a byte that will not fit, which is what the
        # first adventure written in a second alphabet would have got.
        if first + len(self.order) > MAX_CODES:
            rarest = "".join(self.order[MAX_CODES - first:])
            raise ValueError(
                f"an adventure can use {MAX_CODES - first} different "
                f"characters and this one uses {len(self.order)}; the ones it "
                f"could most do without are {rarest[:40]!r}"
            )
        self.first = first
        self.codes = {c: first + i for i, c in enumerate(self.order)}
        self.chars = {code: c for c, code in self.codes.items()}

    def __len__(self):
        return len(self.order)

    @property
    def spare(self):
        """How many codes are left for the compressor."""
        return MAX_CODES - self.first - len(self.order)

    def encode(self, text):
        try:
            return bytes(self.codes[c] for c in text)
        except KeyError as e:
            raise KeyError(f"character {e.args[0]!r} is not in the character set")

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

    def __init__(self, texts, first=0, extra=()):
        self.charset = Charset(texts, first, extra)
        encoded = [self.charset.encode(t) for t in texts]
        self.packer, self.messages = pack(
            encoded, first + len(self.charset), self.charset.spare
        )
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
