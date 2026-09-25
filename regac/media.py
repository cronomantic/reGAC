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
"""Making what a machine really loads: a disk or a tape with a loader on it.

An Amstrad starts an adventure the way it started them then: `RUN"JUEGO`, and
what runs is a BASIC program of three lines that takes the memory it needs,
pulls the interpreter in and calls it.  That program goes on the medium first
and the interpreter after it, and the two media carry the same pair.

The BASIC is written out already tokenised, which is what the machine keeps in
memory, because that is the one thing it takes without argument: a listing in
plain text works off a disk but the tape wants this.  There are only three
statements to encode, so the table below is three tokens long.

    open("juego.cdt", "wb").write(cpc_tape(code))
    open("juego.dsk", "wb").write(cpc6128_disk(code, resident, banks))
"""

import struct

from .cdt import BASIC, BINARY, File, tape
from .binary import Reader
from .dsk import Disk
from .i18n import _

# The three words the loader is made of, as Locomotive BASIC keeps them, plus
# what marks a number written in hexadecimal and what separates statements.
CALL = 0x83
LOAD = 0xA8
MEMORY = 0xAA
OUT = 0xB9
HEX = 0x1C
SPACE = 0x20
QUOTE = 0x22
COLON = 0x01                    # what separates two statements on a line:
                                # a tokenised line keeps it as a one and
                                # not as the letter, which LIST prints
                                # the same way and BASIC does not run

BASIC_AT = 0x0170               # where a BASIC program lives on an Amstrad
CODE_AT = 0x4000                # and where the interpreter is built to run
NAME = "JUEGO"


def basic_line(number, body):
    """One line: its length, its number, what it says, and a nought."""
    body = bytes(body) + b"\x00"
    return struct.pack("<HH", len(body) + 4, number) + body


def hex_number(value):
    """A number as the machine keeps it when it was typed with an ampersand."""
    return bytes([HEX]) + struct.pack("<H", value)


def quoted(text):
    return bytes([QUOTE]) + text.encode("ascii") + bytes([QUOTE])


SCREEN_AT = 0xC000              # where an Amstrad keeps what it is showing
SCREEN_BYTES = 0x4000


def loader(wanted, keep=CODE_AT - 1, entry=CODE_AT, screen=None):
    """The lines: keep out of the memory the interpreter wants, put up the
    loading screen if there is one, bring the interpreter in and go.
    `wanted` is the name to load, which on tape is the shout that means the
    next file and no fuss about it.
    """
    out = basic_line(10, [MEMORY, SPACE] + list(hex_number(keep)))
    if screen is not None:
        out += basic_line(20, [LOAD, SPACE] + list(quoted(screen))
                          + [ord(",")] + list(hex_number(SCREEN_AT)))
    out += basic_line(30, [LOAD, SPACE] + list(quoted(wanted)))
    out += basic_line(40, [CALL, SPACE] + list(hex_number(entry)))
    return out + bytes(2)


def amsdos(name, data, kind=BINARY, load=CODE_AT, entry=0):
    """The hundred and twenty eight bytes AMSDOS puts in front of a file on a
    disk: the same header the tape carries, and a checksum of it, which is how
    AMSDOS tells a file with a header from one without."""
    head = bytearray(128)
    stem, _, suffix = name.upper().partition(".")
    head[1:9] = stem.ljust(8).encode("ascii")
    head[9:12] = suffix.ljust(3).encode("ascii")
    head[18] = kind
    head[21:23] = struct.pack("<H", load)
    head[24:26] = struct.pack("<H", len(data))
    head[26:28] = struct.pack("<H", entry)
    head[64:67] = len(data).to_bytes(3, "little")
    head[67:69] = struct.pack("<H", sum(head[:67]) & 0xFFFF)
    return bytes(head) + bytes(data)


# A disk for the older shape -- the interpreter and the whole database in one
# stretch from $4000 -- is not written any more, and the reason is worth
# keeping: AMSDOS holds two kilobytes of buffer around $A700 and does not give
# them up when BASIC asks for the memory, so a file loaded across them comes
# back with a hole in it.  It was there for as long as that disk was, and only
# showed the day a picture landed in the hole.  A 464 loads from tape, which
# has no such thing, and the 6128 loads its interpreter at $8000 and its
# database through a window: neither goes near it.  See tests/test_media_cpc.py.


# -- the Spectrum +3, which loads from disk and not from tape -----------------

# What the Spectrum's own BASIC keeps for each of these words.
SPECTRUM_CLEAR = 0xFD
SPECTRUM_LOAD = 0xEF
SPECTRUM_CODE = 0xAF
SPECTRUM_RANDOMIZE = 0xF9
SPECTRUM_USR = 0xC0
SPECTRUM_VAL = 0xB0
ENTER = 0x0D

PLUS3_CODE_AT = 0x8000          # where the Spectrum interpreter is built to run
PLUS3_LOADER = "DISK"           # the name the +3 menu runs by itself
PLUS3_GAME = "GAME"
FILE_BASIC = 0
FILE_CODE = 3


def spectrum_line(number, body):
    """One line of Spectrum BASIC: its number the wrong way round, which is
    how that machine writes it, then how long it is and what it says."""
    body = bytes(body) + bytes([ENTER])
    return struct.pack(">H", number) + struct.pack("<H", len(body)) + body


def spectrum_number(value):
    """A number written as VAL of a string.

    Typed in as digits it would carry five bytes of hidden binary after them,
    which is a thing to get wrong for no reason; VAL "32767" is the same
    number to the machine and is only what it looks like.
    """
    return bytes([SPECTRUM_VAL, 0x22]) + str(value).encode("ascii") + bytes([0x22])


def plus3_loader(name=PLUS3_GAME, load=PLUS3_CODE_AT, screen=False):
    """CLEAR below the interpreter, put up the screen if there is one, load
    the interpreter and call it."""
    body = [SPECTRUM_CLEAR] + list(spectrum_number(load - 1))
    if screen:
        body += ([ord(":"), SPECTRUM_LOAD, 0x22]
                 + list(PLUS3_SCREEN.encode("ascii")) + [0x22, SPECTRUM_CODE])
    body += ([ord(":"), SPECTRUM_LOAD, 0x22] + list(name.encode("ascii"))
             + [0x22, SPECTRUM_CODE, ord(":"), SPECTRUM_RANDOMIZE,
                SPECTRUM_USR] + list(spectrum_number(load)))
    return spectrum_line(10, body)


def plus3_file(kind, data, first=0, second=0):
    """The hundred and twenty eight bytes +3DOS puts in front of a file: its
    own mark, how long the lot is, and then the eight bytes a Spectrum header
    has always had -- what kind of file, how long, and two numbers whose
    meaning is the kind's business."""
    head = bytearray(128)
    head[0:8] = b"PLUS3DOS"
    head[8] = 0x1A
    head[9] = 1                                 # the issue, and then the version
    head[11:15] = (len(data) + 128).to_bytes(4, "little")
    head[15] = kind
    head[16:18] = struct.pack("<H", len(data))
    head[18:20] = struct.pack("<H", first)
    head[20:22] = struct.pack("<H", second)
    head[127] = sum(head[:127]) & 0xFF
    return bytes(head) + bytes(data)


PLUS3_SCREEN = "SCREEN"
SPECTRUM_SCREEN_AT = 0x4000
SPECTRUM_SCREEN_BYTES = 6912


def plus3_disk(code, load=PLUS3_CODE_AT, screen=None):
    """A +3 disk with the loader the machine's own menu starts.

    The first thing on that menu is Loader, and what Loader runs is the BASIC
    program called DISK, so that is what it is called.  A loading screen is a
    dump of the Spectrum's own screen and goes on as another file, put up
    before the interpreter comes in.
    """
    basic = plus3_loader(PLUS3_GAME, load, bool(screen))
    disk = Disk("plus3")
    disk.add(PLUS3_LOADER, plus3_file(FILE_BASIC, basic, 10, len(basic)))
    if screen:
        disk.add(PLUS3_SCREEN,
                 plus3_file(FILE_CODE, screen, SPECTRUM_SCREEN_AT, 0x8000))
    disk.add(PLUS3_GAME, plus3_file(FILE_CODE, code, load, 0x8000))
    return disk.image()


def plus3_banked_disk(boot, code, banks, screen=None):
    """A +3 disk for an adventure whose database lives in banks.

    The loader is not BASIC any more -- BASIC cannot page -- so what goes in
    the file the menu runs is the one in loader3.asm, already assembled, with
    its BASIC around it.  The rest is one file with no header: the
    interpreter and then each bank end to end --
    in the order the loader asks for them, which is the order of the table it
    walks and not any order of ours.
    """
    disk = Disk("plus3")
    disk.add(PLUS3_LOADER, plus3_file(FILE_BASIC, boot, 10, len(boot)))
    pieces = ([bytes(screen)] if screen else []) + [bytes(code)]
    pieces += [bytes(b) for b in banks]
    disk.add(PLUS3_GAME, b"".join(pieces))
    return disk.image()


def banks_of(image):
    """The banked part of a built database, bank by bank and without the
    padding that makes them all the same size."""
    reader = Reader(image)
    if not reader.bank_count:
        return []
    page = 1 << reader.page_bits
    used = [0] * reader.bank_count
    for bank, offset, size in reader.directory:
        if bank != 0xFF:
            used[bank] = max(used[bank], offset + size)
    at = reader.resident_size
    return [image[at + n * page:at + n * page + used[n]]
            for n in range(reader.bank_count)]


# -- the PCW, which starts itself and has nothing to ask ----------------------

PCW_TABLE_AT = 0x1C0            # where boot.asm keeps its table, in its sector
PCW_TABLE_BYTES = 64            # to the end of the sector, and no further
PCW_SAVE_ENTRY = 60             # the last four of them: the saved game
PCW_NO_BANK = 0xFF              # a piece that goes where the map already is
PCW_SECTOR = 512
PCW_PAYLOAD = "GAME"
PCW_SAVE = "GAME.SAV"
PCW_SAVE_SECTORS = 4            # what a game amounts to, rounded up

PCW_CODE_AT = 0x0100            # where the interpreter is put
PCW_WINDOW = 0x4000             # and the window the database is paged through
PCW_DB_BANK = 5                 # whose first bank goes here: see game.asm

PCW_SCREEN_AT = 0x8000          # the half of the screen the map can see
PCW_PICTURE_BANK = 2            # which is this one, and the text is in
PCW_TEXT_BANK = 4
PCW_HALF = 16 * 720             # what a half of the screen takes
PCW_SCREEN_BYTES = 2 * PCW_HALF


def pcw_disk(boot, pieces, entry=PCW_CODE_AT, save=PCW_SAVE_SECTORS):
    """A disk a PCW starts by itself.

    `pieces` are what to load, in the order they lie on the disk: where each
    goes, what it is, and which of the machine's banks to put in the window
    first.  They travel as one file, so that the disk still has a filesystem
    on it that a person can read, and the loader is told where that file
    begins and reads on from there.  `entry` is where to jump when they are
    all in.

    The saved game is a second file, made here, of the right size and empty.
    Where it starts goes in the table too, and the interpreter reads it from
    there: it writes those sectors itself, without touching the directory,
    and the result is still a file CP/M's own tools can copy about.
    """
    disk = Disk("pcw")
    payload, table = bytearray(), bytearray()
    for where, blob, bank in pieces:
        padded = bytes(blob) + bytes(-len(blob) % PCW_SECTOR)
        table += struct.pack("<HBB", where, len(padded) // PCW_SECTOR, bank)
        payload += padded
    table += bytes(4)                           # and nowhere, to end it
    disk.add(PCW_PAYLOAD, bytes(payload))
    header = bytes(disk.where(PCW_PAYLOAD)) + struct.pack("<H", entry)
    table = header + bytes(table)
    if len(table) > PCW_SAVE_ENTRY:
        raise ValueError(_("too many pieces to fit in the boot sector's "
                           "table"))
    table = table.ljust(PCW_SAVE_ENTRY, b"\0")
    if save:
        disk.add(PCW_SAVE, bytes(save * PCW_SECTOR))
        table += bytes(disk.where(PCW_SAVE)) + bytes([save, 0])
    disk.boot(boot, table.ljust(PCW_TABLE_BYTES, b"\0"), PCW_TABLE_AT)
    return disk.image()


def pcw_release(boot, code, banks, screen=None):
    """The whole of an adventure on one PCW disk: the interpreter, the banks
    its database is split into, and the saved game waiting to be written.

    A loading screen is the whole of this machine's screen as the video reads
    it, both halves one after the other, and it goes first so that it is there
    for the rest of the load.  The top half is written where the map already
    shows it; the bottom half is in a bank of its own, so it goes through the
    same window the database uses.
    """
    pieces = []
    if screen:
        pieces.append((PCW_SCREEN_AT, bytes(screen[:PCW_HALF]), PCW_NO_BANK))
        pieces.append((PCW_WINDOW, bytes(screen[PCW_HALF:]), PCW_TEXT_BANK))
    pieces.append((PCW_CODE_AT, bytes(code), PCW_NO_BANK))
    pieces += [(PCW_WINDOW, bytes(bank), PCW_DB_BANK + n)
               for n, bank in enumerate(banks)]
    return pcw_disk(boot, pieces)


# The other way round, for an adventure whose database leaves no room for the
# interpreter above $4000: the interpreter goes under it and the database has
# everything from $4000 up.  See the map at the top of z80/cpc/game.asm.
CPC_LOW_CODE_AT = 0x0400        # where the interpreter runs
CPC_LOW_DATABASE_AT = 0x4000    # and where the database is loaded
CPC_LOW_ISLAND_AT = 0xAB00      # up to the island, which is the interpreter's
CPC_LOW_ROOM = CPC_LOW_ISLAND_AT - CPC_LOW_DATABASE_AT

def low_loader(wanted, screen=None):
    """The lines for that one: keep BASIC out of everything from $4000 up,
    bring the interpreter in there, call the mover in front of it that carries
    it down to $0400 and comes back, load the database over where it was, and
    go.

    What is called at the end is not the interpreter but the starter the mover
    left at the island: with the lower ROM still in, $0400 is ROM and not the
    interpreter, so something above $4000 has to put the ROMs out of the way
    and jump down.

    BASIC keeps its variables under HIMEM, which is $3FFF here, and grows them
    downwards; the interpreter ends around $2450, so there are some five
    kilobytes between the two and nothing of ours is written over."""
    out = basic_line(10, [MEMORY, SPACE] + list(hex_number(CPC_LOW_DATABASE_AT - 1)))
    if screen is not None:
        out += basic_line(20, [LOAD, SPACE] + list(quoted(screen))
                          + [ord(",")] + list(hex_number(SCREEN_AT)))
    out += basic_line(30, [LOAD, SPACE] + list(quoted(wanted)))
    out += basic_line(40, [CALL, SPACE] + list(hex_number(CPC_LOW_DATABASE_AT)))
    out += basic_line(50, [LOAD, SPACE] + list(quoted(wanted)))
    out += basic_line(60, [CALL, SPACE] + list(hex_number(CPC_LOW_ISLAND_AT)))
    return out + bytes(2)


def cpc_low_tape(code, database, name=NAME, screen=None):
    """A tape of that shape: the loader, the screen if there is one, the
    interpreter with its mover in front, and the database as a file of its
    own."""
    room = CPC_LOW_ROOM
    if len(database) > room:
        raise ValueError(_(
            "the database is {count} bytes and {room} fit under the island, "
            "even with the interpreter out of the way", count=len(database),
            room=room))
    files = [File(name, low_loader("!", "!" if screen else None,
                                   ),
                  kind=BASIC, load=BASIC_AT)]
    if screen:
        files.append(File(name, screen, kind=BINARY, load=SCREEN_AT))
    files.append(File(name, code, kind=BINARY, load=CPC_LOW_DATABASE_AT))
    files.append(File(name, database, kind=BINARY, load=CPC_LOW_DATABASE_AT))
    return tape(files)


def cpc_tape(code, name=NAME, load=CODE_AT, entry=CODE_AT, screen=None):
    """A tape with the same, which a machine starts with RUN and nothing else
    because what it runs is whatever comes first.  A shouted name means the
    next file along, so the pieces only have to be in the order they are
    wanted: the loader, the screen and the interpreter."""
    files = [File(name, loader("!", load - 1, entry,
                               "!" if screen else None),
                  kind=BASIC, load=BASIC_AT)]
    if screen:
        files.append(File(name, screen, kind=BINARY, load=SCREEN_AT))
    files.append(File(name, code, kind=BINARY, load=load, entry=entry))
    return tape(files)


# -- and the 6128, which has a disk and another sixty four kilobytes ----------

# The only sixteen kilobytes the gate array can swap are the ones at $4000, so
# that is where the window goes and the interpreter lives above it.  Which is
# also why the loader has to page: a bank is loaded through the window with
# the bank in it, one file at a time, and BASIC can do that because OUT is a
# word it knows.
CPC6128_WINDOW = 0x4000         # where a bank is loaded, and the resident half
CPC6128_CODE_AT = 0x8000        # and where the interpreter goes
CPC6128_PAGES = (0xC4, 0xC5, 0xC6, 0xC7)
CPC6128_NORMAL = 0xC0           # the arrangement that puts the machine back
CPC6128_PORT = 0x7F00           # any port whose high byte is that one

# The saved game, which the interpreter writes by sectors itself: a file made
# here, empty and the right size, and where it starts written into the three
# bytes of the interpreter that z80/cpc/disc.asm reads.  Those bytes are the
# third to the fifth of the binary, behind the jump over them.
CPC6128_SAVE_SECTORS = 4        # what a game amounts to, rounded up; the same
                                # number as SAVE_SECTORS in disc.asm
CPC6128_SAVE_WHERE = 2          # where in the binary the three bytes go
CPC6128_SECTOR = 512


def cpc6128_loader(binary, resident, banks, screen=None):
    """The lines a 6128 needs, which are the 464's with the paging in the
    middle: protect the memory, put up the screen, lay
    the resident half of the database in the window -- in the bank that is
    there when nothing has been paged, which none of the four ever covers --
    then each bank in turn through the window, put the machine back and go.
    """
    out = basic_line(10, [MEMORY, SPACE] + list(hex_number(CPC6128_WINDOW - 1)))
    if screen is not None:
        out += basic_line(20, [LOAD, SPACE] + list(quoted(screen))
                          + [ord(",")] + list(hex_number(SCREEN_AT)))
    out += basic_line(30, [LOAD, SPACE] + list(quoted(resident)))
    for number, named in enumerate(banks):
        out += basic_line(40 + number,
                          [OUT, SPACE] + list(hex_number(CPC6128_PORT))
                          + [ord(",")] + list(hex_number(CPC6128_PAGES[number]))
                          + [COLON, LOAD, SPACE] + list(quoted(named)))
    out += basic_line(50, [OUT, SPACE] + list(hex_number(CPC6128_PORT))
                      + [ord(",")] + list(hex_number(CPC6128_NORMAL)))
    out += basic_line(60, [LOAD, SPACE] + list(quoted(binary)))
    out += basic_line(70, [CALL, SPACE] + list(hex_number(CPC6128_CODE_AT)))
    return out + bytes(2)


def cpc6128_disk(code, resident, banks, name=NAME, screen=None):
    """A disk a 6128 starts with RUN and the name.

    Every piece is a file of its own with its own AMSDOS header, which is what
    lets BASIC put each one where it belongs: the banks all say $4000 because
    they all come in through the window, and which bank they land in is what
    the OUT in front of the LOAD decides.

    The saved game is one more file, empty, with no header, because nothing
    loads it: the interpreter writes its sectors itself.  Where it starts is
    written into the interpreter before that goes on the disk, and that is why
    it goes on last.
    """
    if len(banks) > len(CPC6128_PAGES):
        raise ValueError(_(
            "a 6128 has {given} banks to give and this wants {wanted}",
            given=len(CPC6128_PAGES), wanted=len(banks)))
    binary = f"{name}.BIN"
    held = f"{name}.RES"
    picture = f"{name}.SCR" if screen else None
    named = [f"{name}.B{n}" for n in range(len(banks))]
    disk = Disk("cpc-data")
    disk.add(f"{name}.BAS",
             amsdos(f"{name}.BAS",
                    cpc6128_loader(binary, held, named, picture),
                    kind=0, load=BASIC_AT))
    if screen:
        disk.add(picture, amsdos(picture, screen, load=SCREEN_AT))
    disk.add(held, amsdos(held, resident, load=CPC6128_WINDOW))
    for piece, what in zip(named, banks):
        disk.add(piece, amsdos(piece, bytes(what), load=CPC6128_WINDOW))
    saved = f"{name}.SAV"
    disk.add(saved, bytes(CPC6128_SAVE_SECTORS * CPC6128_SECTOR))
    code = told_where_to_save(code, disk.where(saved))
    disk.add(binary, amsdos(binary, code, load=CPC6128_CODE_AT,
                            entry=CPC6128_CODE_AT))
    return disk.image()


def told_where_to_save(code, where):
    """The interpreter with the track and record of its saved game, and how
    many sectors that is, in the three bytes it keeps for them.  A binary that
    does not start by jumping over three bytes is not one that keeps them, and
    writing into it would break it, so it is refused."""
    at = CPC6128_SAVE_WHERE
    if bytes(code[:at]) != bytes((0x18, 3)):
        raise ValueError(_(
            "the 6128's interpreter should start by jumping over the three "
            "bytes that say where the saved game is, and this one does not"))
    track, record = where
    out = bytearray(code)
    out[at:at + 3] = bytes((track, record, CPC6128_SAVE_SECTORS))
    return bytes(out)


# -- the Spectrum Next, whose medium the assembler writes itself --------------

# A .nex file carries its own loading screen, so there is nothing here for the
# Next but the size of one: layer 2 at 256 by 192, a byte to a pixel, which is
# what the machine shows and what a dump of it is.
NEXT_SCREEN_BYTES = 256 * 192


# -- the MSX, whose tape is a file of blocks and nothing else -----------------

# A block on an MSX cassette is this marker and then its bytes, and a marker
# only ever begins on an eighth byte.  A file is two blocks: the one that says
# what it is and what it is called, and the one with the thing itself.
MSX_MARKER = bytes([0x1F, 0xA6, 0xDE, 0xBA, 0xCC, 0x13, 0x7D, 0x74])
MSX_BINARY = bytes([0xD0]) * 10         # what marks a header as a binary's
MSX_NAME_BYTES = 6                      # and the name that follows it
MSX_CODE_AT = 0x8000                    # where the interpreter is built to run

# How much of the database comes in at a time.  It is read into the copy of
# the screen the interpreter has not started using yet, so the size is that
# buffer's; the machine has to be taken back for each chunk, and the motor
# stops while that happens, so every chunk is a block of its own.
MSX_CHUNK = 8192

# A loading screen here is the video chip's own memory: its patterns, its
# names and its colours, one after another, which is what a screen 2 picture
# amounts to.  What a person will have is a .SC2, which is exactly that with
# seven bytes of BSAVE header in front of it.
MSX_SCREEN_BYTES = 0x3800
MSX_BSAVE = 7
MSX_BSAVE_MARK = 0xFE


def msx_block(out, body):
    """One block onto the tape, marker and all, on the eighth byte."""
    while len(out) % 8:
        out.append(0)
    out += MSX_MARKER
    out += bytes(body)
    return out


def msx_file(out, name, data, load, entry):
    """A binary file as the machine's own BLOAD reads it: what it is called,
    and then where it goes, where it ends and where to start it."""
    msx_block(out, MSX_BINARY + name.upper().ljust(MSX_NAME_BYTES)[:MSX_NAME_BYTES]
              .encode("ascii"))
    head = struct.pack("<HHH", load, load + len(data) - 1, entry)
    return msx_block(out, head + bytes(data))


def msx_screen(data):
    """A loading screen as the video chip holds it, whichever of the two ways
    it was handed over: a dump of those tables, or the .SC2 an MSX drawing
    program writes, which is the same thing behind a BSAVE header."""
    if len(data) == MSX_SCREEN_BYTES + MSX_BSAVE and data[0] == MSX_BSAVE_MARK:
        return bytes(data[MSX_BSAVE:])
    return bytes(data)


def msx_tape(code, database=b"", screen=None, load=MSX_CODE_AT, entry=None,
             name=PCW_PAYLOAD):
    """The whole of an adventure on one cassette, which a person starts with
    `BLOAD"CAS:",R` and nothing else.

    Only the interpreter is a file: it is what BLOAD can reach, because BLOAD
    reaches no further than the thirty two kilobytes the BASIC can see, and a
    database does not go there -- it goes under the BIOS, where nothing can
    put it but the interpreter itself.  So the interpreter is started first
    and reads the rest of the tape with the machine's own routines, a chunk at
    a time, and the chunks are blocks with no name on them.

    What comes behind the interpreter starts with three bytes that say what is
    coming -- how big the database is, and whether a loading screen is in
    front of it -- so that nothing about one adventure is built into the
    loader.  The screen goes in the same block as the first chunk, because
    stopping the motor between them would buy nothing: the screen needs no
    memory at all, it goes straight into the chip as it is read.
    """
    out = bytearray()
    msx_file(out, name, code, load, load if entry is None else entry)
    header = struct.pack("<HB", len(database), 1 if screen else 0)
    if screen:
        header += msx_screen(screen)
    chunks = [bytes(database[at:at + MSX_CHUNK])
              for at in range(0, len(database), MSX_CHUNK)]
    msx_block(out, header + (chunks[0] if chunks else b""))
    for piece in chunks[1:]:
        msx_block(out, piece)
    return bytes(out)


# -- the PC, which runs an .EXE and asks for nothing else ---------------------

# What DOS reads at the head of an .EXE.  The image behind it is whatever NASM
# wrote with `-f bin`, and nothing in it names a segment: the interpreter
# works its segments out from CS once it is running, so there is no table of
# places for DOS to patch.  What DOS does patch without being asked is CS and
# SS themselves, which the header gives counting from the start of the image.
MZ_HEADER_BYTES = 0x1C          # the header proper, and the table would go here
MZ_PARAGRAPH = 16               # the unit DOS counts memory in
MZ_PAGE = 512                   # and the unit it counts the file in
MZ_STACK_BYTES = 1024
MZ_ALL = 0xFFFF                 # ask for all the memory there is


def paragraphs(size):
    return (size + MZ_PARAGRAPH - 1) // MZ_PARAGRAPH


def mz_exe(image, entry=0, stack=MZ_STACK_BYTES, memory=0, most=MZ_ALL):
    """An .EXE out of a flat binary built to run from offset nought.

    The header is twenty eight bytes but the image has to start on a
    paragraph, so the file carries thirty two in front of it.  Behind the
    image in memory go `memory` bytes that the program wants and the file does
    not carry, and behind those the stack, in a segment of its own.  DOS will
    not start the program without room for both, and gives it up to `most`
    paragraphs more if it has them: all of it, unless told otherwise.
    """
    if not 0 < stack <= 0x10000 or stack % 2:
        raise ValueError(_("a stack of {stack} bytes is not one DOS can "
                           "set up", stack=stack))
    head = paragraphs(MZ_HEADER_BYTES)
    size = head * MZ_PARAGRAPH + len(image)
    needed = paragraphs(memory) + paragraphs(stack)
    header = struct.pack(
        "<2s13H",
        b"MZ",
        size % MZ_PAGE,                         # what the last page holds
        (size + MZ_PAGE - 1) // MZ_PAGE,        # pages, counting the last
        0,                                      # nothing to patch
        head,
        needed,                                 # the least DOS must add
        max(needed, most),                      # and the most it may
        paragraphs(len(image)) + paragraphs(memory),  # SS, from the image
        stack & 0xFFFF,                         # SP: a full 64K is nought
        0,                                      # no checksum, as DOS ignores it
        entry,                                  # IP
        0,                                      # CS, from the image
        MZ_HEADER_BYTES,                        # where the table would be
        0,                                      # not an overlay
    )
    return header.ljust(head * MZ_PARAGRAPH, b"\x00") + bytes(image)
