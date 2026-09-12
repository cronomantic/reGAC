"""Take a memory image out of an adventure that is loading from disk or tape.

The decompiler reads memory, not media: it wants the adventure sitting where
the interpreter put it, so that the pointers it follows mean something.  For
the Spectrum that came free, because the adventures to hand were snapshots.
For the other machines what can be found is a disk or a tape image, so the
image has to be loaded on the machine it was made for and the memory read off
afterwards.

That is all this does.  It starts the emulator on the machine asked for, puts
the medium in, waits for the game to load and settle, and writes out what is
in memory as a flat file where the address of a byte is its offset.

    python grab.py --machine CPC464 juego.cdt juego.bin
    python grab.py --machine CPC6128 juego.dsk juego.bin

A disk goes in the drive; anything else is handed to the emulator to work out
for itself.  Loading happens at the speed the machine really loaded at unless
the emulator can hurry it, so a tape takes minutes: --wait says how long to
give it, and --keys what to type first if the game does not start on its own.

Checked against a Spectrum snapshot, which can be compared against itself:
reading the 48K back gives the snapshot byte for byte bar the frame counter
and the two bytes of stack the snapshot itself uses to start.
"""

import argparse
import os
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "tests"))

import emulator  # noqa: E402


def grab(image, machine, wait, keys=None, start=0, size=0x10000, boot=None,
         port=emulator.PORT):
    image = os.path.abspath(image)
    extra = ["--fastautoload", "--simulaterealloadfast"]
    if image.lower().endswith(".dsk"):
        extra += ["--enable-dsk", "--dsk-file", image]
    session = emulator.Session(machine=machine, port=port, extra=extra)
    try:
        time.sleep(boot if boot is not None else emulator.BOOT_SECONDS)
        if not image.lower().endswith(".dsk"):
            session.command(f"smartload {image}")
        if keys:
            session.keys(keys)
            session.enter()
        time.sleep(wait)
        return session.read(start, size)
    finally:
        session.close()


def looks_like_gac(image, table=0x4000):
    """Whether the pointers GAC keeps at a fixed place look like pointers.

    On the Amstrad they sit in a row from $4000 on: nouns, adverbs, objects,
    locations and the three condition tables.  If every one of them points
    somewhere above the start of the database and below the top of memory,
    the load worked.  It is a weak test, but a wrong one is loud.
    """
    found = []
    for n in range(8):
        at = table + n * 2
        if at + 1 >= len(image):
            return []
        found.append(image[at] | (image[at + 1] << 8))
    return found if all(0x2000 < p < 0xFFFF for p in found) else []


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("image", help="the disk, tape or snapshot to load")
    parser.add_argument("output", help="where to write the memory image")
    parser.add_argument("--machine", default="CPC464", help="which machine to load it on")
    parser.add_argument("--wait", type=float, default=60.0, help="seconds to let it load")
    parser.add_argument("--boot", type=float, default=None, help="seconds to let the machine boot")
    parser.add_argument("--keys", default=None, help="what to type once it has booted")
    parser.add_argument("--start", type=lambda n: int(n, 0), default=0)
    parser.add_argument("--size", type=lambda n: int(n, 0), default=0x10000)
    args = parser.parse_args(argv)

    image = grab(args.image, args.machine, args.wait, args.keys, args.start,
                 args.size, args.boot)
    with open(args.output, "wb") as f:
        f.write(image)
    print(f"{len(image)} bytes of {args.machine} memory in {args.output}")
    if args.start == 0:
        pointers = looks_like_gac(image)
        if pointers:
            print("looks like GAC: " + " ".join(f"{p:04X}" for p in pointers))
        else:
            print("no GAC tables at $4000; give it longer, or type something to start it")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
