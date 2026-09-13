"""Take a file off a CPC disk image, and put it where it belongs in memory.

The Amstrad adventures come as disk images, and inside one the adventure is an
ordinary file with an AMSDOS header that says what address it loads at.  So
there is no need to run anything: read the directory, join the file's blocks,
and lay it in a 64K image at its own load address.  What comes out is what the
machine would have had in memory, which is what the decompiler wants.

    python disk.py juego.dsk                 # list what is on it
    python disk.py juego.dsk CARVALHO.FAC salida.mem

Both the plain and the extended image formats are read.  Disks whose sectors
were renumbered to stop them being copied are not: those still have to be
loaded on the machine, which is what grab.py is for.
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


def memory(blob):
    """A 64K image with the file laid where it loads."""
    head = header(blob)
    if not head:
        raise ValueError("the file has no AMSDOS header, so where it goes is unknown")
    body = blob[128:128 + head["length"]]
    image = bytearray(0x10000)
    image[head["load"]:head["load"] + len(body)] = body
    return bytes(image), head


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("image", help="the disk image")
    parser.add_argument("name", nargs="?", help="the file to take off it")
    parser.add_argument("output", nargs="?", help="where to write the memory image")
    args = parser.parse_args(argv)

    data = open(args.image, "rb").read()
    area = data_area(data)
    listing = directory(area)
    if not args.name:
        first = sectors(tracks(data)[0])
        kind = SECTOR_BASES.get(min(s[0] for s in first), "unknown") if first else "unknown"
        print(f"{len(listing)} files, {kind} format")
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
    image, head = memory(contents(area, listing[args.name]))
    out = args.output or args.name.replace(".", "_") + ".mem"
    with open(out, "wb") as f:
        f.write(image)
    print(f"{args.name} laid at ${head['load']:04X} in {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
