"""Take a file off a CPC disk image, and put it where it belongs in memory.

The Amstrad adventures come as disk images, and inside one the adventure is an
ordinary file with an AMSDOS header that says what address it loads at.  So
there is no need to run anything: read the directory, join the file's blocks,
and lay it in a 64K image at its own load address.  What comes out is what the
machine would have had in memory, which is what the decompiler wants.

    python disk.py juego.dsk                 # list what is on it
    python disk.py juego.dsk CARVALHO.FAC salida.mem
    python disk.py juego.dsk MEGACOR2.BIN salida.mem --at 0x40

A file that ends by moving itself somewhere else is followed there, because
that is what the machine would have in memory; --at overrides both.

Both the plain and the extended image formats are read.  A disk laid out to
stop it being copied keeps nothing in its directory, and its own loader reads
tracks AMSDOS would not recognise; but those tracks are still an image of what
the machine loads, so they are read too:

    python disk.py VAJILLAS.DSK              # says what is in the raw tracks
    python disk.py VAJILLAS.DSK --part 1 salida.mem

What tells where such an image goes is the database itself, which always
starts with the same eight marks of punctuation at $210C.
"""

import argparse
import struct
import sys

SECTOR_BASES = {0xC1: "data", 0x41: "system", 0x01: "ibm"}


def tracks(data):
    """Every track of the image, in order, as the bytes it occupies."""
    if data[:8] == b"MV - CPC":
        count = data[0x30] * data[0x31]
        sizes = [struct.unpack("<H", data[0x32:0x34])[0]] * count
    elif data[:8] == b"EXTENDED":
        count = data[0x30] * data[0x31]
        sizes = [data[0x34 + n] * 256 for n in range(count)]
    else:
        raise ValueError("not a CPC disk image")
    out, at = [], 0x100
    for size in sizes:
        out.append(data[at:at + size] if size else None)
        at += size
    return out


def sectors(track):
    """The sectors of one track: (id, contents), in the order they are laid
    down, which is not the order they are numbered."""
    if not track or track[:10] != b"Track-Info":
        return []
    out, at = [], 0x100
    for n in range(track[0x15]):
        info = track[0x18 + n * 8:0x20 + n * 8]
        length = struct.unpack("<H", info[6:8])[0] or (128 << info[3])
        out.append((info[2], track[at:at + length]))
        at += length
    return out


def data_area(data):
    """The disk as AMSDOS sees it: every sector in numbered order, end to end."""
    out = bytearray()
    for track in tracks(data):
        for _, blob in sorted(sectors(track), key=lambda s: s[0]):
            out += blob
    return bytes(out)


def directory(area):
    """What is on the disk: name against the list of pieces that make it up."""
    found = {}
    for at in range(0, 2048, 32):
        entry = area[at:at + 32]
        if entry[0] != 0:                       # a user other than 0, or erased
            continue
        name = entry[1:9].decode("latin-1").rstrip()
        ext = bytes(c & 0x7F for c in entry[9:12]).decode("latin-1").rstrip()
        if not name.strip():
            continue
        found.setdefault(f"{name}.{ext}", []).append(
            (entry[12] + entry[14] * 32, entry[15], [b for b in entry[16:32] if b])
        )
    return found


def contents(area, pieces):
    """One file, its extents joined in order."""
    out = bytearray()
    for _, records, blocks in sorted(pieces):
        blob = bytearray()
        for block in blocks:
            blob += area[block * 1024:(block + 1) * 1024]
        out += blob[:records * 128]
    return bytes(out)


def header(blob):
    """The AMSDOS header, if the file has one.  It is only a header if its own
    checksum says so, which is how AMSDOS itself decides."""
    if len(blob) < 128:
        return None
    if sum(blob[:67]) & 0xFFFF != struct.unpack("<H", blob[67:69])[0]:
        return None
    return {
        "kind": blob[18],
        "load": struct.unpack("<H", blob[21:23])[0],
        "length": struct.unpack("<H", blob[24:26])[0],
        "entry": struct.unpack("<H", blob[26:28])[0],
    }


def self_mover(body, load):
    """Where a file moves itself to, if the last thing in it is the move.

    Megacorp loads at $0428 and its last fourteen bytes are

        LD DE,$0040 / LD HL,$0428 / LD BC,length / LDIR / JP $1F2C

    so what the machine ends up with is the adventure at $0040, which is where
    Los pájaros de Bangkok loads outright.  Its BASIC loader calls straight
    into that, and nothing else in the file is touched, so doing the move here
    gives the same memory the machine would have without running anything.
    """
    tail = body[-14:]
    if len(tail) < 14 or tail[0] != 0x11 or tail[3] != 0x21 or tail[6] != 0x01:
        return None
    if tail[9] != 0xED or tail[10] != 0xB0 or tail[11] != 0xC3:
        return None
    to = struct.unpack("<H", tail[1:3])[0]
    frm = struct.unpack("<H", tail[4:6])[0]
    count = struct.unpack("<H", tail[7:9])[0]
    if frm != load or count > len(body):
        return None
    return to, count


def memory(blob, at=None):
    """A 64K image with the file laid where it loads, or where it is told."""
    head = header(blob)
    if not head:
        raise ValueError("the file has no AMSDOS header, so where it goes is unknown")
    body = blob[128:128 + head["length"]]
    where = head["load"] if at is None else at
    image = bytearray(0x10000)
    image[where:where + len(body)] = body
    moved = None if at is not None else self_mover(body, where)
    if moved:
        to, count = moved
        image[to:to + count] = body[:count]
        where = to
    return bytes(image), dict(head, laid=where, moved=bool(moved))


# The eight marks of punctuation are the first thing in a GAC database and are
# the same eight in every one there is, which is what the reference decompiler
# uses to recognise one at all.  Here they say where in a heap of sectors an
# adventure is, and, because they sit at $210C in memory, where it loads.
DATABASE_MARK = bytes([0x00, 0x20, 0x2E, 0x2C, 0x2D, 0x21, 0x3F, 0x3A])
PUNCTUATION_AT = 0x210C


def raw_stream(data):
    """Every track but the first, end to end, as the loader would read them.

    A protected disk keeps nothing in its directory, so there is no file to
    join; what there is instead is the data itself, laid down track after
    track.  The first track is left out because that one is a normal one, with
    the boot sector and the empty directory on it.
    """
    out = bytearray()
    for n, track in enumerate(tracks(data)):
        if n == 0:
            continue
        for _, blob in sorted(sectors(track), key=lambda s: s[0]):
            out += blob
    return bytes(out)


# Where the Amstrad keeps the pointers to its tables, and how many of them
# run one after another from there.
TABLES_AT = 0x4000
TABLES = 10


def has_tables(stream, base):
    """Whether the pointers of an adventure laid from `base` climb through the
    database as they should.  Eight marks of punctuation could turn up by
    chance in a picture; ten climbing pointers on top of that could not."""
    at = base + TABLES_AT
    if at < 0 or at + TABLES * 2 > len(stream):
        return False
    last = PUNCTUATION_AT
    for n in range(TABLES):
        pointer = stream[at + n * 2] | stream[at + n * 2 + 1] << 8
        if not last < pointer <= 0xFFFF:
            return False
        last = pointer
    return True


def adventures(stream):
    """Where each adventure in that heap begins, as the address of its $0000.

    La guerra de las vajillas keeps its two parts one after the other, so this
    finds two.
    """
    found, at = [], stream.find(DATABASE_MARK)
    while at >= 0:
        base = at - PUNCTUATION_AT
        if has_tables(stream, base):
            found.append(base)
        at = stream.find(DATABASE_MARK, at + 1)
    return found


def raw_memory(stream, base):
    """A 64K image of the machine, taken from that point of the heap."""
    image = bytearray(0x10000)
    piece = stream[max(base, 0):base + 0x10000]
    image[max(-base, 0):max(-base, 0) + len(piece)] = piece
    return bytes(image)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("image", help="the disk image")
    parser.add_argument("name", nargs="?", help="the file to take off it")
    parser.add_argument("output", nargs="?", help="where to write the memory image")
    parser.add_argument("--at", type=lambda n: int(n, 0), default=None,
                        help="lay it at this address instead of its own")
    parser.add_argument("--part", type=int, default=None,
                        help="which adventure to take off a disk with no directory")
    args = parser.parse_args(argv)

    data = open(args.image, "rb").read()
    area = data_area(data)
    listing = directory(area)

    if args.part is not None:
        # With --part the one name given is where to write, because there is
        # no directory to name a file in.
        out = args.output or args.name or "part.mem"
        stream = raw_stream(data)
        where = adventures(stream)
        if not 1 <= args.part <= len(where):
            print(f"the disk has {len(where)} of them", file=sys.stderr)
            return 1
        base = where[args.part - 1]
        with open(out, "wb") as f:
            f.write(raw_memory(stream, base))
        print(f"adventure {args.part} of {len(where)} laid where it loads, "
              f"from ${base:04X} of the raw tracks, in {out}")
        return 0

    if not args.name:
        first = sectors(tracks(data)[0])
        kind = SECTOR_BASES.get(min(s[0] for s in first), "unknown") if first else "unknown"
        print(f"{len(listing)} files, {kind} format")
        if not listing:
            where = adventures(raw_stream(data))
            print(f"  no directory, but {len(where)} adventures in the raw "
                  f"tracks: take them with --part")
        for name, pieces in listing.items():
            blob = contents(area, pieces)
            head = header(blob)
            where = (f"loads at ${head['load']:04X}, ${head['length']:04X} bytes"
                     if head else "no header")
            print(f"  {name:14s} {len(blob):6d} bytes  {where}")
        return 0

    if args.name not in listing:
        print(f"no {args.name} on the disk", file=sys.stderr)
        return 1
    image, head = memory(contents(area, listing[args.name]), args.at)
    out = args.output or args.name.replace(".", "_") + ".mem"
    with open(out, "wb") as f:
        f.write(image)
    how = " after moving itself there" if head["moved"] else ""
    print(f"{args.name} laid at ${head['laid']:04X}{how} in {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
