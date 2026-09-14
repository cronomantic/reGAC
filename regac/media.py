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


def loader(wanted, keep=CODE_AT - 1, entry=CODE_AT):
    """The three lines: keep out of the memory the interpreter wants, load it,
    and go.  `wanted` is the name to load, which on tape is the shout that
    means the next file and no fuss about it."""
    return (basic_line(10, [MEMORY, SPACE] + list(hex_number(keep)))
            + basic_line(20, [LOAD, SPACE] + list(quoted(wanted)))
            + basic_line(30, [CALL, SPACE] + list(hex_number(entry)))
            + b"\x00\x00")


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


def cpc_disk(code, name=NAME, load=CODE_AT, entry=CODE_AT):
    """A data disk with the loader and the interpreter on it, which a machine
    starts with RUN and the name."""
    binary = f"{name}.BIN"
    disk = Disk("cpc-data")
    disk.add(f"{name}.BAS",
             amsdos(f"{name}.BAS", loader(binary, load - 1, entry),
                    kind=0, load=BASIC_AT))
    disk.add(binary, amsdos(binary, code, load=load, entry=entry))
    return disk.image()


def cpc_tape(code, name=NAME, load=CODE_AT, entry=CODE_AT):
    """A tape with the same two, which a machine starts with RUN and nothing
    else because what it runs is whatever comes first."""
    return tape([
        File(name, loader("!", load - 1, entry), kind=BASIC, load=BASIC_AT),
        File(name, code, kind=BINARY, load=load, entry=entry),
    ])
