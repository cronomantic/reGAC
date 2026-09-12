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
"""The binary database the 8 bit interpreter reads.

Everything is little endian, and every offset inside a section is relative to
that section, so a section can be moved into a memory bank without rewriting
what is inside it.

Sections are either resident, meaning always reachable, or banked.  What must
be resident is what the interpreter touches on every turn with no warning: the
vocabulary, the object and location tables, the condition tables and the font.
Text, pictures and music are looked up at known moments and can be paged in.

    Header
      0  magic "RGAC"
      4  version
      5  machine
      6  page bits: 14 for banks of 16K, 13 for 8K, 0 for no banking at all
      7  music mode
      8  music buffer size, in bytes
     10  number of banks
     11  number of sections
     12  directory, five bytes a section: bank, offset, size

A bank of 0xFF means the section is resident.  With no banking the whole image
is one block and every section is resident, which is what the eight adventures
to hand need: none of them reaches 21K.
"""

import struct

from .opcodes import BY_NAME, GFX_CMDS
from .text import TextStore

MAGIC = b"RGAC"
VERSION = 1
RESIDENT = 0xFF

MACHINES = {
    "spectrum48": 0,
    "spectrum128": 1,
    "cpc": 2,
    "msx": 3,
    "msx2": 4,
    "sam": 5,
    "next": 6,
}

# How the music player gets at the tune it is playing.  The player runs from
# the interrupt, so it must never read through a paging window that the main
# code is free to change underneath it.  See doc/binario.md.
MUSIC_COPY = 0  # the tune is copied into a resident buffer when it starts
MUSIC_SLOT = 1  # the tune stays in a bank of its own, mapped to its own slot

(
    S_CONFIG,
    S_VOCAB,
    S_OBJECTS,
    S_LOCATIONS,
    S_CONDITIONS,
    S_TEXT,
    S_FONT,
    S_GRAPHICS,
    S_MUSIC,
) = range(9)

SECTION_NAMES = [
    "config",
    "vocabulary",
    "objects",
    "locations",
    "conditions",
    "text",
    "font",
    "graphics",
    "music",
]

# What cannot be paged out, because the interpreter reaches for it at any time.
ALWAYS_RESIDENT = {S_CONFIG, S_VOCAB, S_OBJECTS, S_LOCATIONS, S_CONDITIONS, S_FONT}

VERB, NOUN, ADVERB, PRONOUN = range(4)

CONDITION_END = 0x00
NO_MESSAGE = 0xFF  # there is no message with that number
NO_CHARACTER = 0xFF  # the adventure has no such character
PUSH_MARK = 0x80


def u8(value):
    return struct.pack("<B", value & 0xFF)


def u16(value):
    return struct.pack("<H", value & 0xFFFF)


class BuildError(Exception):
    pass


# ---------------------------------------------------------------------------
# Conditions
# ---------------------------------------------------------------------------


def assemble_conditions(code):
    """Turn a condition block into bytes.

    A constant is two bytes with the top bit of the first set, which leaves
    fifteen bits, enough for the largest location number.  Everything else is
    its opcode.  A zero byte ends the table.
    """
    out = bytearray()
    for instruction in code:
        name = instruction[0]
        if name == "PUSH":
            value = instruction[1]
            if not 0 <= value <= 0x7FFF:
                raise BuildError(f"constant {value} does not fit")
            out.append(PUSH_MARK | (value >> 8))
            out.append(value & 0xFF)
            continue
        op = BY_NAME.get(name)
        if op is None:
            raise BuildError(f"unknown opcode {name!r}")
        out.append(op.code)
    out.append(CONDITION_END)
    return bytes(out)


def disassemble_conditions(data):
    """Read a condition block back, for checking what was written."""
    from .opcodes import BY_CODE

    out = []
    i = 0
    while i < len(data):
        byte = data[i]
        if byte == CONDITION_END:
            break
        if byte & PUSH_MARK:
            out.append(["PUSH", ((byte & 0x7F) << 8) | data[i + 1]])
            i += 2
            continue
        out.append([BY_CODE[byte].name])
        i += 1
    return out


# ---------------------------------------------------------------------------
# Building
# ---------------------------------------------------------------------------


class Database:
    """Lays out an adventure as the bytes the 8 bit interpreter will read."""

    def __init__(self, ddb, machine="spectrum48", page_bits=0, music_buffer=0,
                 music_mode=MUSIC_COPY):
        if machine not in MACHINES:
            raise BuildError(f"unknown machine {machine!r}")
        self.ddb = ddb
        self.machine = machine
        self.page_bits = page_bits
        self.music_buffer = music_buffer
        self.music_mode = music_mode
        self.__gather_text()

    # -- text ---------------------------------------------------------------

    def __gather_text(self):
        """All the printable text of the adventure goes into one store, so
        that a pair found in a message can also serve a room description."""
        self.messages = sorted(self.ddb["messages"], key=int)
        self.objects = sorted(self.ddb["objects"], key=int)
        self.locations = sorted(self.ddb["locations"], key=int)
        texts = [self.ddb["messages"][m] for m in self.messages]
        texts += [self.ddb["objects"][o]["name"] for o in self.objects]
        texts += [self.ddb["locations"][l]["desc"] for l in self.locations]
        self.no_objs_index = len(texts)
        texts.append(self.ddb.get("no_objs_msg", "Nothing"))
        self.texts = texts
        extra = list(self.ddb.get("verbs", {}))
        extra += list(self.ddb.get("nouns", {}))
        extra += list(self.ddb.get("adverbs", {}))
        extra += list(self.ddb.get("pronouns", []))
        extra += list(self.ddb.get("separators", []))
        extra += [c for c in self.ddb.get("punctuation", []) if c != chr(0)]
        # The digits always get a code and a glyph, whether the adventure's
        # text happens to use one or not, because scores get printed.
        extra += list("0123456789")
        self.store = TextStore(texts, extra=extra)
        self.message_index = {m: i for i, m in enumerate(self.messages)}
        base = len(self.messages)
        self.name_index = {o: base + i for i, o in enumerate(self.objects)}
        base += len(self.objects)
        self.desc_index = {l: base + i for i, l in enumerate(self.locations)}

    def code_of(self, char):
        return self.store.charset.codes[char]

    # -- sections -----------------------------------------------------------

    def config(self):
        out = bytearray()
        out += u16(self.ddb.get("init_loc", 1))
        out += u8(self.ddb.get("width", 32))
        # The codes of the ten digits, at a fixed place so the runtime can
        # print a number without hunting for them.
        for digit in "0123456789":
            out += u8(self.code_of(digit))
        # What the player types arrives as ASCII and has to become a code of
        # this adventure's character set before it can be matched against the
        # vocabulary.  Ninety six bytes covers everything typeable.
        codes = self.store.charset.codes
        for point in range(32, 128):
            out += u8(codes.get(chr(point), NO_CHARACTER))
        punct = self.ddb.get("punctuation", [])
        # The first entry is the end of string marker and has no glyph.
        printable = [c for c in punct if c != "\0"]
        out += u8(len(printable))
        for c in printable:
            out += u8(self.code_of(c))
        separators = self.ddb.get("separators", [])
        out += u8(len(separators))
        for word in separators:
            out += u8(len(word))
            for c in word:
                out += u8(self.code_of(c))
        out += u16(self.no_objs_index)
        return bytes(out)

    def vocabulary(self):
        entries = []
        for kind, key in ((VERB, "verbs"), (NOUN, "nouns"), (ADVERB, "adverbs")):
            for word, wid in sorted(self.ddb.get(key, {}).items()):
                entries.append((kind, wid, word))
        for word in self.ddb.get("pronouns", []):
            entries.append((PRONOUN, 255, word))
        out = bytearray(u16(len(entries)))
        for kind, wid, word in entries:
            out += u8(kind) + u8(wid) + u8(len(word))
            for c in word:
                out += u8(self.code_of(c))
        return bytes(out)

    def object_table(self):
        out = bytearray(u8(len(self.objects)))
        for key in self.objects:
            obj = self.ddb["objects"][key]
            out += u8(int(key))
            out += u8(obj.get("weight", 0))
            out += u16(obj.get("initial_loc", 0))
            out += u16(self.name_index[key])
        return bytes(out)

    def location_table(self):
        out = bytearray(u16(len(self.locations)))
        for key in self.locations:
            loc = self.ddb["locations"][key]
            exits = loc.get("exits", [])
            out += u16(int(key))
            out += u16(loc.get("graphic_id", 0))
            out += u16(self.desc_index[key])
            out += u8(len(exits))
            for way in exits:
                out += u8(way["dir"]) + u16(way["dest"])
        return bytes(out)

    def conditions(self):
        high = assemble_conditions(self.ddb.get("hpcs", []))
        low = assemble_conditions(self.ddb.get("lpcs", []))
        locals_ = {k: assemble_conditions(v) for k, v in self.ddb.get("lcs", {}).items()}
        order = sorted(locals_, key=int)
        head = 6
        body = bytearray()
        off_high = head
        body += high
        off_low = head + len(body)
        body += low
        off_local = head + len(body)
        index = bytearray()
        blocks = bytearray()
        # room number, then where its block starts, ending with room zero
        data_start = off_local + 4 * len(order) + 2
        for room in order:
            index += u16(int(room)) + u16(data_start + len(blocks))
            blocks += locals_[room]
        index += u16(0)
        return u16(off_high) + u16(off_low) + u16(off_local) + bytes(body + index + blocks)

    def text(self):
        packer = self.store.packer
        out = bytearray()
        out += u8(packer.first_pair)
        out += u8(len(packer))
        for left, right in packer.table:
            out += u8(left) + u8(right)
        # Message numbers are the ones the adventure was written with and they
        # are full of gaps, so a straight table turns one into its place in the
        # store.  Two hundred and fifty six bytes, and no searching.
        lookup = bytearray([NO_MESSAGE] * 256)
        for index, key in enumerate(self.messages):
            lookup[int(key)] = index
        out += lookup
        out += u16(len(self.store.messages))
        offset = 0
        offsets = bytearray()
        data = bytearray()
        for message in self.store.messages:
            offsets += u16(offset)
            data += message
            offset += len(message)
        out += offsets
        out += u16(len(data))
        out += data
        return bytes(out)

    def font(self):
        """The glyphs, in the order the character set numbers them.

        A character the original font has no glyph for comes out blank; that
        is where the accented letters will go once they are drawn.
        """
        source = self.ddb.get("font") or []
        out = bytearray()
        out += u8(self.store.charset.first)
        out += u8(len(self.store.charset))
        for char in self.store.charset.order:
            point = ord(char)
            start = point * 8
            if point < 128 and start + 8 <= len(source):
                out += bytes(source[start : start + 8])
            else:
                out += bytes(8)
        return bytes(out)

    def graphics(self):
        gfx = self.ddb.get("gfx", {})
        order = sorted(gfx, key=int)
        head = 2 + 4 * len(order)
        blocks = bytearray()
        index = bytearray(u16(len(order)))
        for key in order:
            index += u16(int(key)) + u16(head + len(blocks))
            picture = bytearray()
            for command in gfx[key]:
                name = command[0]
                if name not in GFX_CMDS:
                    raise BuildError(f"unknown graphics command {name!r}")
                code, argc = GFX_CMDS[name]
                picture += u8(code)
                for n, argument in enumerate(command[1:]):
                    picture += u16(argument) if name == "CALL" else u8(argument)
            blocks += u16(len(picture)) + picture
        return bytes(index + blocks)

    def music(self):
        """Nothing to put here yet.  The shape is fixed now so that adding
        tunes later moves no other section: a count, then for each tune where
        it starts and how long it is."""
        return u16(0)

    # -- layout -------------------------------------------------------------

    def sections(self):
        return [
            self.config(),
            self.vocabulary(),
            self.object_table(),
            self.location_table(),
            self.conditions(),
            self.text(),
            self.font(),
            self.graphics(),
            self.music(),
        ]

    def plan(self):
        """Decide which section goes where.

        With no banking everything is resident and laid end to end.  With
        banking, what has to be reachable at any moment stays resident and the
        rest is packed into banks, whole: a section is never split, so paging
        one in never needs two pages mapped at once.
        """
        blocks = self.sections()
        page = 1 << self.page_bits if self.page_bits else 0
        resident = bytearray()
        placement = [None] * len(blocks)
        for index, block in enumerate(blocks):
            if not page or index in ALWAYS_RESIDENT:
                placement[index] = (RESIDENT, len(resident), len(block))
                resident += block
        banks = []
        for index, block in enumerate(blocks):
            if placement[index] is not None:
                continue
            if len(block) > page:
                raise BuildError(
                    f"the {SECTION_NAMES[index]} section is {len(block)} bytes "
                    f"and a bank holds {page}"
                )
            for number, bank in enumerate(banks):
                if len(bank) + len(block) <= page:
                    placement[index] = (number, len(bank), len(block))
                    bank += block
                    break
            else:
                placement[index] = (len(banks), 0, len(block))
                banks.append(bytearray(block))
        return blocks, placement, resident, banks

    def build(self):
        blocks, placement, resident, banks = self.plan()
        header = bytearray()
        header += MAGIC
        header += u8(VERSION)
        header += u8(MACHINES[self.machine])
        header += u8(self.page_bits)
        header += u8(self.music_mode)
        header += u16(self.music_buffer)
        header += u8(len(banks))
        header += u8(len(blocks))
        for bank, offset, size in placement:
            # resident offsets are counted from the end of the header
            header += u8(bank) + u16(offset) + u16(size)
        image = bytes(header) + bytes(resident)
        # Banks are padded to a whole page, as they are on the machine, so
        # that bank n always starts at the same place.
        page = 1 << self.page_bits if self.page_bits else 0
        for bank in banks:
            image += bytes(bank) + bytes(page - len(bank))
        self.placement = placement
        self.header_size = len(header)
        self.resident_size = len(header) + len(resident)
        self.banks = banks
        return image


def build(ddb, machine="spectrum48", page_bits=0, music_buffer=0):
    database = Database(ddb, machine, page_bits, music_buffer)
    return database.build(), database


# ---------------------------------------------------------------------------
# Reading it back
# ---------------------------------------------------------------------------


class Reader:
    """Reads the image the way the 8 bit interpreter will, which is how the
    writer gets checked."""

    def __init__(self, image):
        if image[:4] != MAGIC:
            raise BuildError("not a reGAC database")
        self.image = image
        self.version = image[4]
        self.machine = image[5]
        self.page_bits = image[6]
        self.music_mode = image[7]
        self.music_buffer = struct.unpack_from("<H", image, 8)[0]
        self.bank_count = image[10]
        count = image[11]
        self.directory = []
        for n in range(count):
            bank, offset, size = struct.unpack_from("<BHH", image, 12 + 5 * n)
            self.directory.append((bank, offset, size))
        self.header_size = 12 + 5 * count
        self.resident_size = self.header_size + sum(
            size for bank, _, size in self.directory if bank == RESIDENT
        )

    def section(self, index):
        bank, offset, size = self.directory[index]
        if bank == RESIDENT:
            start = self.header_size + offset
        else:
            page = 1 << self.page_bits
            start = self.resident_size + bank * page + offset
        return self.image[start : start + size]

    # -- the pieces ---------------------------------------------------------

    def charset(self):
        data = self.section(S_FONT)
        return data[0], data[1]

    def text(self):
        data = self.section(S_TEXT)
        first_pair, pair_count = data[0], data[1]
        pairs = [(data[2 + 2 * i], data[3 + 2 * i]) for i in range(pair_count)]
        p = 2 + 2 * pair_count
        self.message_lookup = data[p : p + 256]
        p += 256
        count = struct.unpack_from("<H", data, p)[0]
        p += 2
        offsets = [struct.unpack_from("<H", data, p + 2 * i)[0] for i in range(count)]
        p += 2 * count
        length = struct.unpack_from("<H", data, p)[0]
        p += 2
        blob = data[p : p + length]
        bounds = offsets + [length]
        return first_pair, pairs, [blob[bounds[i]:bounds[i + 1]] for i in range(count)]

    def conditions(self):
        data = self.section(S_CONDITIONS)
        off_high, off_low, off_local = struct.unpack_from("<HHH", data, 0)
        high = disassemble_conditions(data[off_high:off_low])
        low = disassemble_conditions(data[off_low:off_local])
        locals_ = {}
        p = off_local
        while True:
            room = struct.unpack_from("<H", data, p)[0]
            if room == 0:
                break
            start = struct.unpack_from("<H", data, p + 2)[0]
            locals_[str(room)] = disassemble_conditions(data[start:])
            p += 4
        return high, low, locals_

    def objects(self):
        data = self.section(S_OBJECTS)
        out = {}
        for n in range(data[0]):
            oid, weight, loc, name = struct.unpack_from("<BBHH", data, 1 + 6 * n)
            out[str(oid)] = {"weight": weight, "initial_loc": loc, "name": name}
        return out

    def locations(self):
        data = self.section(S_LOCATIONS)
        count = struct.unpack_from("<H", data, 0)[0]
        out = {}
        p = 2
        for _ in range(count):
            lid, gfx, desc = struct.unpack_from("<HHH", data, p)
            nexits = data[p + 6]
            p += 7
            exits = []
            for _ in range(nexits):
                exits.append({"dir": data[p], "dest": struct.unpack_from("<H", data, p + 1)[0]})
                p += 3
            out[str(lid)] = {"graphic_id": gfx, "exits": exits, "desc": desc}
        return out

    def vocabulary(self):
        data = self.section(S_VOCAB)
        count = struct.unpack_from("<H", data, 0)[0]
        p = 2
        out = []
        for _ in range(count):
            kind, wid, length = data[p], data[p + 1], data[p + 2]
            codes = data[p + 3 : p + 3 + length]
            p += 3 + length
            out.append((kind, wid, bytes(codes)))
        return out

    def graphics(self):
        data = self.section(S_GRAPHICS)
        from .opcodes import GFX_CMDS

        by_code = {code: (name, argc) for name, (code, argc) in GFX_CMDS.items()}
        count = struct.unpack_from("<H", data, 0)[0]
        out = {}
        for n in range(count):
            gid, offset = struct.unpack_from("<HH", data, 2 + 4 * n)
            length = struct.unpack_from("<H", data, offset)[0]
            block = data[offset + 2 : offset + 2 + length]
            commands = []
            p = 0
            while p < len(block):
                name, argc = by_code[block[p]]
                p += 1
                if name == "CALL":
                    commands.append([name, struct.unpack_from("<H", block, p)[0]])
                    p += 2
                else:
                    commands.append([name] + list(block[p : p + argc]))
                    p += argc
            out[str(gid)] = commands
        return out
