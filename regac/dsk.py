"""Writing a disk image, for the machines that load off one.

This is a CP/M filesystem and the container that holds it.  The Amstrad, the
Spectrum +3 and the PCW all put CP/M on a disk with different numbers, so what
changes from one to another is a table of ten values and where the sectors are
numbered from; the rest of the work is the same.

The filesystem part follows the one in ChooseYourDestiny, which is itself a
port of libdsk and mkp3fs, and is the reason this was not written from
scratch.  What is new here is the Amstrad: AMSDOS keeps no boot record, so its
format has to be told rather than read, and its sectors are numbered from $C1
on a data disk and from $41 on a system one, which is how the machine tells
one from the other.

    disk = Disk("cpc-data")
    disk.add("JUEGO.BIN", blob)
    disk.save("juego.dsk")
"""

import struct

DIRECTORY_ENTRY = 32
RECORD = 128                    # what CP/M counts a file in
EMPTY = 0xE5                    # a formatted but unused byte, and a free entry
FILLER = 0x1A                   # what the tail of the last block is padded with


class DiskError(Exception):
    pass


class Format:
    """What a machine's disk is made of.

    The first ten values are the disk specification as CP/M itself writes it
    in a boot record, so a format that has one hands them over as they are.
    `base` is the number the first sector of a track carries, which is what an
    Amstrad reads its format off, and `boot` says whether sector zero holds
    that specification or is already the directory.
    """

    def __init__(self, tracks, sectors, sector_size, reserved, block_size,
                 dir_blocks, base, heads=1, kind=0, geometry=0,
                 read_gap=0x2A, format_gap=0x52, boot=False, byte_count=False):
        self.tracks = tracks
        self.sectors = sectors
        self.sector_size = sector_size
        self.reserved = reserved
        self.block_size = block_size
        self.dir_blocks = dir_blocks
        self.base = base
        self.heads = heads
        self.kind = kind
        self.geometry = geometry
        self.read_gap = read_gap
        self.format_gap = format_gap
        self.boot = boot
        self.byte_count = byte_count

    def specification(self):
        """The ten bytes CP/M keeps in a boot record."""
        return bytes([
            self.kind,
            self.geometry,
            self.tracks,
            self.sectors,
            self.sector_size.bit_length() - 8,      # the size is 128 << this
            self.reserved,
            self.block_size.bit_length() - 8,
            self.dir_blocks,
            self.read_gap,
            self.format_gap,
        ])


# The Amstrad's, which AMSDOS tells apart by the sector numbers alone, and the
# Spectrum +3's, which does keep a boot record.  The PCW's are the same shape
# and go here when its runtime does.
FORMATS = {
    "cpc-data": Format(tracks=40, sectors=9, sector_size=512, reserved=0,
                       block_size=1024, dir_blocks=2, base=0xC1),
    "cpc-system": Format(tracks=40, sectors=9, sector_size=512, reserved=2,
                         block_size=1024, dir_blocks=2, base=0x41),
    "cpc-ibm": Format(tracks=40, sectors=8, sector_size=512, reserved=1,
                      block_size=1024, dir_blocks=2, base=0x01),
    "plus3": Format(tracks=40, sectors=9, sector_size=512, reserved=1,
                    block_size=1024, dir_blocks=2, base=0x01,
                    boot=True, byte_count=True),
    "plus3-720": Format(tracks=80, sectors=9, sector_size=512, reserved=2,
                        block_size=2048, dir_blocks=4, base=0x01, heads=2,
                        kind=3, geometry=0x81, boot=True, byte_count=True),
    # The PCW's own, which is the same shape and starts itself: see boot().
    "pcw": Format(tracks=40, sectors=9, sector_size=512, reserved=1,
                  block_size=1024, dir_blocks=2, base=0x01,
                  boot=True, byte_count=True),
}

# What a PCW wants of the sector it starts from: the first sixteen bytes are
# the specification, the code begins after them, and the whole sector has to
# add up to this.
BOOT_AT = 0xF000
BOOT_CODE_AT = 0xF010
BOOT_SUM = 0xFF


def filename(name):
    """A name as the directory holds it: eight and three, padded out, in
    capitals and with the attribute bits clear."""
    stem, _, suffix = name.strip().upper().partition(".")
    if len(stem) > 8 or len(suffix) > 3:
        raise DiskError(f"{name} does not fit in eight and three")
    return (stem.ljust(8) + suffix.ljust(3)).encode("ascii")


class Disk:
    """A disk with files on it, built in memory and written out at the end."""

    def __init__(self, format="cpc-data"):
        self.format = FORMATS[format] if isinstance(format, str) else format
        shape = self.format
        self.per_block = shape.block_size // shape.sector_size
        self.sector_count = shape.tracks * shape.heads * shape.sectors
        # Block zero is the first one past the reserved tracks, and the
        # directory takes the first few blocks of what is left.
        usable = self.sector_count - shape.reserved * shape.sectors
        self.blocks = usable // self.per_block
        # A block number is one byte while they fit in one, and two when not.
        self.wide = self.blocks > 256
        self.pointers = 8 if self.wide else 16
        # How many sixteen kilobyte extents one directory entry stands for.
        self.extents = max(1, (shape.block_size * self.pointers) // 16384)
        self.entries = (shape.dir_blocks * shape.block_size) // DIRECTORY_ENTRY
        self.directory = bytearray([EMPTY]) * (self.entries * DIRECTORY_ENTRY)
        self.contents = {}                      # block number -> its bytes
        self.next_block = shape.dir_blocks
        self.boot_sector = None                 # what a PCW starts from
        self.raw = {}                           # and anything put by position

    # -- putting files on it ------------------------------------------------

    def add(self, name, blob, user=0):
        """Put a file on the disk, split across directory entries the way
        CP/M does it: so many blocks to an entry, and a new entry for each
        sixteen kilobytes when the blocks are small."""
        fcb = filename(name)
        if self.find(fcb, user) is not None:
            raise DiskError(f"{name} is on the disk already")
        blocks = self.lay_down(blob)
        records = (len(blob) + RECORD - 1) // RECORD
        piece = 0
        while blocks or records:
            mine, blocks = blocks[:self.pointers], blocks[self.pointers:]
            here = min(records, RECORD * self.extents)
            records -= here
            self.put_entry(user, fcb, piece, mine, here, len(blob))
            piece += 1
        if not piece:                           # an empty file still needs one
            self.put_entry(user, fcb, 0, [], 0, 0)

    def lay_down(self, blob):
        """Lay the file down in blocks, and say which ones it took."""
        taken = []
        for at in range(0, len(blob), self.format.block_size):
            if self.next_block >= self.blocks:
                raise DiskError("the disk is full")
            piece = bytes(blob[at:at + self.format.block_size])
            piece += bytes([FILLER]) * (self.format.block_size - len(piece))
            self.contents[self.next_block] = piece
            taken.append(self.next_block)
            self.next_block += 1
        return taken

    def put_entry(self, user, fcb, piece, blocks, records, size):
        """One directory entry: whose it is, what it is called, which part of
        the file it stands for, and the blocks that part sits in."""
        at = self.free_entry()
        entry = bytearray(DIRECTORY_ENTRY)
        entry[0] = user
        entry[1:12] = fcb
        # Extents are counted in sixteen kilobyte pieces and the top of the
        # count goes in a byte of its own; what the record count holds is what
        # is left over in the last of those pieces.
        full = max(records - 1, 0) // RECORD
        last = piece * self.extents + full
        entry[12] = last & 31
        entry[14] = last >> 5
        entry[15] = records - RECORD * full
        if self.format.byte_count and size % RECORD:
            entry[13] = size % RECORD
        for n, block in enumerate(blocks):
            if self.wide:
                entry[16 + n * 2] = block & 0xFF
                entry[17 + n * 2] = block >> 8
            else:
                entry[16 + n] = block
        self.directory[at:at + DIRECTORY_ENTRY] = entry

    def free_entry(self):
        for at in range(0, len(self.directory), DIRECTORY_ENTRY):
            if self.directory[at] == EMPTY:
                return at
        raise DiskError("the directory is full")

    def find(self, fcb, user=0):
        """Where a file's first entry is, or nothing if it is not here."""
        for at in range(0, len(self.directory), DIRECTORY_ENTRY):
            entry = self.directory[at:at + DIRECTORY_ENTRY]
            if entry[0] == user and bytes(b & 0x7F for b in entry[1:12]) == fcb:
                return at
        return None

    def boot(self, code, machine=BOOT_SUM):
        """Put the code a PCW starts from in the first sector.

        That machine has no ROM at all: at the switch it fetches a loader from
        the keyboard controller, reads this one sector to $F000 and, if the
        512 bytes add up to what it wants, jumps to $F010 -- which is why the
        specification takes the first sixteen and the code follows it.  The
        byte before the end is bent to make the sum come out.
        """
        spare = self.format.sector_size - (BOOT_CODE_AT - BOOT_AT) - 1
        if len(code) > spare:
            raise DiskError(f"the boot code is {len(code)} bytes and {spare} fit")
        sector = bytearray(self.format.sector_size)
        sector[0:10] = self.format.specification()
        sector[16:16 + len(code)] = code
        sector[-1] = (machine - sum(sector[:-1])) & 0xFF
        self.boot_sector = bytes(sector)
        return self.boot_sector

    def put(self, track, sector, blob):
        """Write one sector where it lies, for what has no business being in
        a file: the loader reads these by position."""
        where = track * self.format.sectors + (sector - 1)
        if not 0 <= where < self.sector_count:
            raise DiskError(f"there is no track {track} sector {sector}")
        self.raw[where] = bytes(blob).ljust(self.format.sector_size, bytes(1))

    # -- writing it out -----------------------------------------------------

    def sectors(self):
        """Every sector of the disk in the order the machine numbers them:
        the reserved tracks first, then the directory, then the blocks."""
        shape = self.format
        out = [bytes([EMPTY]) * shape.sector_size
               for _ in range(self.sector_count)]
        if shape.boot:
            out[0] = (self.boot_sector or
                      shape.specification()
                      + bytes(shape.sector_size - len(shape.specification())))
        first = shape.reserved * shape.sectors
        blocks = dict(self.contents)
        for number in range(shape.dir_blocks):
            at = number * shape.block_size
            blocks[number] = bytes(self.directory[at:at + shape.block_size])
        for number, blob in blocks.items():
            where = first + number * self.per_block
            for n in range(self.per_block):
                out[where + n] = blob[n * shape.sector_size:
                                      (n + 1) * shape.sector_size]
        for where, blob in self.raw.items():
            out[where] = blob
        return out

    def image(self):
        """The whole disk as a CPCEMU image, which is what the emulators and
        the tools of all three machines read."""
        shape = self.format
        sectors = self.sectors()
        track_size = 0x100 + shape.sectors * shape.sector_size
        head = bytearray(0x100)
        head[0:34] = b"MV - CPCEMU Disk-File\r\nDisk-Info\r\n"
        head[34:48] = b"reGAC".ljust(14)
        head[0x30] = shape.tracks
        head[0x31] = shape.heads
        head[0x32:0x34] = struct.pack("<H", track_size)
        out = bytearray(head)
        at = 0
        for track in range(shape.tracks):
            for side in range(shape.heads):
                info = bytearray(0x100)
                info[0:12] = b"Track-Info\r\n"
                info[0x10] = track
                info[0x11] = side
                info[0x14] = shape.sector_size.bit_length() - 8
                info[0x15] = shape.sectors
                info[0x16] = shape.format_gap
                info[0x17] = EMPTY
                for n in range(shape.sectors):
                    entry = 0x18 + n * 8
                    info[entry + 0] = track
                    info[entry + 1] = side
                    info[entry + 2] = shape.base + n
                    info[entry + 3] = shape.sector_size.bit_length() - 8
                out += info
                for _ in range(shape.sectors):
                    out += sectors[at]
                    at += 1
        return bytes(out)

    def save(self, path):
        with open(path, "wb") as f:
            f.write(self.image())
        return path
