"""Making what a machine really loads: a disk or a tape with a loader on it.

An Amstrad starts an adventure the way it started them then: `RUN"JUEGO`, and
what runs is a BASIC program of three lines that takes the memory it needs,
pulls the interpreter in and calls it.  That program goes on the medium first
and the interpreter after it, and the two media carry the same pair.

The BASIC is written out already tokenised, which is what the machine keeps in
memory, because that is the one thing it takes without argument: a listing in
plain text works off a disk but the tape wants this.  There are only three
statements to encode, so the table below is three tokens long.

    open("juego.dsk", "wb").write(cpc_disk(code))
    open("juego.cdt", "wb").write(cpc_tape(code))
"""

import struct

from .cdt import BASIC, BINARY, File, tape
from .binary import Reader
from .dsk import Disk

# The three words the loader is made of, as Locomotive BASIC keeps them, plus
# what marks a number written in hexadecimal and what separates statements.
CALL = 0x83
LOAD = 0xA8
MEMORY = 0xAA
HEX = 0x1C
SPACE = 0x20
QUOTE = 0x22

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
    loading screen if there is one, bring the interpreter in and go.  `wanted`
    is the name to load, which on tape is the shout that means the next file
    and no fuss about it."""
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


def cpc_disk(code, name=NAME, load=CODE_AT, entry=CODE_AT, screen=None):
    """A data disk with the loader and the interpreter on it, which a machine
    starts with RUN and the name.  A loading screen, when there is one, is a
    dump of that machine's own screen and travels as a file of its own."""
    binary = f"{name}.BIN"
    picture = f"{name}.SCR" if screen else None
    disk = Disk("cpc-data")
    disk.add(f"{name}.BAS",
             amsdos(f"{name}.BAS", loader(binary, load - 1, entry, picture),
                    kind=0, load=BASIC_AT))
    if screen:
        disk.add(picture, amsdos(picture, screen, load=SCREEN_AT))
    disk.add(binary, amsdos(binary, code, load=load, entry=entry))
    return disk.image()


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
    interpreter, and then each bank end to end in the order the loader asks
    for them.
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


def cpc_tape(code, name=NAME, load=CODE_AT, entry=CODE_AT, screen=None):
    """A tape with the same, which a machine starts with RUN and nothing else
    because what it runs is whatever comes first.  A shouted name means the
    next file along, so the pieces only have to be in the order they are
    wanted: the loader, the screen, and the interpreter."""
    files = [File(name, loader("!", load - 1, entry, "!" if screen else None),
                  kind=BASIC, load=BASIC_AT)]
    if screen:
        files.append(File(name, screen, kind=BINARY, load=SCREEN_AT))
    files.append(File(name, code, kind=BINARY, load=load, entry=entry))
    return tape(files)
