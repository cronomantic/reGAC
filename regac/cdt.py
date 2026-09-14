"""Writing an Amstrad tape, in the shape the firmware reads.

A file on a CPC tape is a row of blocks of two kilobytes, and every block goes
down twice: a header record saying what it is, and a data record with the
bytes.  Each record is a sync byte, then the data in lumps of 256 with two
bytes of checksum after each, and four bytes to finish.

The checksum is the usual CCITT one, complemented and written high byte first,
which is not something to be guessed at: it was read off the Megacorp tape,
and so were the pulse lengths below, which is why they are what they are
rather than what the manuals round them to.

    open("juego.cdt", "wb").write(tape([
        File("JUEGO", basic, kind=ASCII, load=0x0170),
        File("JUEGO", code, kind=BINARY, load=0x4000, entry=0x4000),
    ]))
"""

import struct

BLOCK = 2048                    # the most one block of a file holds
SEGMENT = 256                   # and the lump each checksum covers
HEADER_SYNC = 0x2C
DATA_SYNC = 0x16
TRAILER = bytes([0xFF, 0xFF, 0xFF, 0xFE])
LAST_BITS = 7                   # of that last byte, which is how it was found

# What a file says it is.  A tokenised BASIC is nought, which is what RUN
# expects; a listing in plain text is the one the firmware calls ASCII.
BASIC = 0
BINARY = 2
ASCII = 0x16

# The pulse lengths of a tape written at the speed the firmware writes at, in
# Z80 cycles, taken from a real one.
PILOT = 2270
PILOT_PULSES = 4096
SYNC_FIRST = 1111
SYNC_SECOND = 1111
ZERO = 1144
ONE = 2288
GAP = 15                        # a breath between the two records of a block
FILE_GAP = 2000                 # and a real pause between one file and the next


class File:
    """One file as the tape carries it."""

    def __init__(self, name, data, kind=BINARY, load=0, entry=0):
        if len(name) > 16:
            raise ValueError(f"{name} is longer than a tape name can be")
        self.name = name.upper()
        self.data = bytes(data)
        self.kind = kind
        self.load = load
        self.entry = entry


def crc(blob):
    """The checksum of one segment: CCITT, and then turned inside out."""
    value = 0xFFFF
    for byte in blob:
        value ^= byte << 8
        for _ in range(8):
            value = ((value << 1) ^ 0x1021) & 0xFFFF if value & 0x8000 \
                else (value << 1) & 0xFFFF
    return (~value) & 0xFFFF


def record(sync, blob):
    """A record as it lies on the tape: the sync byte, the data in segments
    with their checksums, and the tail."""
    out = bytearray([sync])
    for at in range(0, len(blob), SEGMENT):
        segment = blob[at:at + SEGMENT]
        segment += bytes(SEGMENT - len(segment))
        out += segment + struct.pack(">H", crc(segment))
    return bytes(out + TRAILER)


def header(file, number, offset, length, last):
    """The sixty four bytes that say what is coming: the same shape AMSDOS
    puts at the head of a file on disk, which is no coincidence."""
    out = bytearray(64)
    out[0:len(file.name)] = file.name.encode("ascii")
    out[16] = number
    out[17] = 0xFF if last else 0
    out[18] = file.kind
    out[19:21] = struct.pack("<H", length)
    out[21:23] = struct.pack("<H", file.load + offset)
    out[23] = 0xFF if number == 1 else 0
    out[24:26] = struct.pack("<H", len(file.data))
    out[26:28] = struct.pack("<H", file.entry)
    return bytes(out)


def turbo(blob, pause, pilot_pulses=PILOT_PULSES):
    """One block of a tape image, with the speeds written out in full because
    this is not the speed a Spectrum uses."""
    out = bytearray([0x11])
    out += struct.pack("<HHHHHH", PILOT, SYNC_FIRST, SYNC_SECOND, ZERO, ONE,
                       pilot_pulses)
    out += bytes([LAST_BITS])
    out += struct.pack("<H", pause)
    out += len(blob).to_bytes(3, "little")
    return bytes(out + blob)


def tape(files, pause=FILE_GAP):
    """Every file, one after another, as a .cdt."""
    out = bytearray(b"ZXTape!\x1a\x01\x14")
    for file in files:
        pieces = [file.data[at:at + BLOCK]
                  for at in range(0, len(file.data), BLOCK)] or [b""]
        for number, piece in enumerate(pieces, 1):
            last = number == len(pieces)
            out += turbo(record(HEADER_SYNC,
                                header(file, number, (number - 1) * BLOCK,
                                       len(piece), last)),
                         GAP)
            out += turbo(record(DATA_SYNC, piece),
                         pause if last else GAP)
    return bytes(out)
