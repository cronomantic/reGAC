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
"""ReGAC: convert between the JSON database and the editable source format."""

import argparse
import json
import os
import sys

from .binary import MACHINES, SECTION_NAMES, Database, Reader
from .devices import DEVICES, device_for, make
from .gfx import Renderer
from .media import banks_of, cpc_disk, cpc_tape, plus3_banked_disk, plus3_disk
from .png import save_picture
from .srcgen import generate
from .text import TextStore
from .srcparse import SourceError, parse

VERSION = "0.1.0"


def read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path, ddb):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(ddb, f, indent=1, ensure_ascii=False)


def cmd_decompile(args):
    ddb = read_json(args.input)
    name = os.path.splitext(os.path.basename(args.input))[0]
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(generate(ddb, name))
    print(f"{args.input} -> {args.output}")


def cmd_compile(args):
    name = os.path.basename(args.input)
    with open(args.input, encoding="utf-8") as f:
        source = f.read()
    try:
        ddb = parse(source, name)
    except SourceError as e:
        sys.exit(f"ERROR: {e}")
    write_json(args.output, ddb)
    print(f"{args.input} -> {args.output}")


def cmd_check(args):
    """Decompile and recompile a database, reporting any loss."""
    original = read_json(args.input)
    name = os.path.basename(args.input)
    try:
        rebuilt = json.loads(json.dumps(parse(generate(original, name), name)))
    except SourceError as e:
        sys.exit(f"ERROR: {e}")
    if rebuilt == original:
        print(f"{name}: round trip exact")
        return
    differing = sorted(
        k for k in set(original) | set(rebuilt) if original.get(k) != rebuilt.get(k)
    )
    sys.exit(f"{name}: round trip differs in {', '.join(differing)}")


def cmd_render(args):
    """Draw one picture of an adventure, or all of them, as PNG files."""
    gfx = read_json(args.input)["gfx"]
    machine = args.machine
    if args.picture is not None:
        wanted = [str(args.picture)]
    else:
        wanted = sorted(gfx, key=int)
    if not os.path.isdir(args.output) and len(wanted) > 1:
        sys.exit(f"ERROR: {args.output} must be a directory for more than one picture")
    for pid in wanted:
        if pid not in gfx:
            sys.exit(f"ERROR: there is no picture {pid}")
        picture = Renderer(gfx, device_for(machine, gfx, pid)).run(int(pid))
        if os.path.isdir(args.output):
            path = os.path.join(args.output, f"{pid}.png")
        else:
            path = args.output
        save_picture(path, picture, scale=args.scale)
        print(f"picture {pid} -> {path}")


def cmd_checkgfx(args):
    """Compare the pictures on a target machine against the Spectrum.

    A fill spreads until the outlines stop it, so a change of resolution can
    let one escape through a gap the scaling opened, or strand its starting
    point on the wrong side of a line.  Comparing how much of the screen each
    fill reaches on each machine catches exactly that.
    """
    gfx = read_json(args.input)["gfx"]
    name = os.path.basename(args.input)
    suspect = 0
    for pid in sorted(gfx, key=int):
        reference = Renderer(gfx, make("spectrum"))
        reference.run(int(pid))
        target = Renderer(gfx, device_for(args.machine, gfx, pid))
        target.run(int(pid))
        ref_area = reference.device.width * reference.device.height
        out_area = target.device.width * target.device.height
        if len(reference.fill_coverage) != len(target.fill_coverage):
            print(f"  picture {pid}: the two runs filled a different number of times")
            suspect += 1
            continue
        for n, (a, b) in enumerate(
            zip(reference.fill_coverage, target.fill_coverage), 1
        ):
            share_a = a / ref_area
            share_b = b / out_area
            if abs(share_a - share_b) > args.tolerance:
                print(
                    f"  picture {pid}, fill {n}: covers {share_a:.0%} of the screen "
                    f"on the spectrum but {share_b:.0%} on the {args.machine}"
                )
                suspect += 1
    if suspect:
        sys.exit(f"{name}: {suspect} fills differ on the {args.machine}")
    print(f"{name}: every fill covers the same ground on the {args.machine}")


def cmd_text(args):
    """Report what the text of an adventure costs once packed."""
    ddb = read_json(args.input)
    texts = list(ddb["messages"].values())
    texts += [o["name"] for o in ddb["objects"].values()]
    texts += [l["desc"] for l in ddb["locations"].values()]
    texts = [t for t in texts if t]
    store = TextStore(texts)
    print(f"{os.path.basename(args.input)}")
    print(f"  characters      {store.raw_size}")
    print(f"  packed          {store.packed_size}")
    print(f"  pair table      {store.packer.table_bytes} ({len(store.packer)} pairs)")
    print(f"  total           {store.total_size}  ({store.ratio:.0%} of the original)")
    print(f"  glyphs needed   {len(store.charset)}")
    print(f"  spare codes     {store.charset.spare}")
    print(f"  unpacking stack {store.packer.depth()} bytes")


BANK_SIZES = {"none": 0, "8k": 13, "16k": 14}

# Where each machine's interpreter is built to sit, which is where its medium
# has to put it.
LOADS_AT = {"cpc": 0x4000, "plus3": 0x8000}

# And how big a dump of each machine's screen is, which is what a loading
# screen has to be.
SCREEN_BYTES = {"cpc": 0x4000, "plus3": 6912}


def cmd_build(args):
    """Write the binary database the 8 bit interpreter reads."""
    ddb = read_json(args.input)
    database = Database(
        ddb,
        machine=args.machine,
        page_bits=BANK_SIZES[args.banks],
        music_buffer=args.music_buffer,
    )
    image = database.build()
    with open(args.output, "wb") as f:
        f.write(image)
    if args.defs:
        # What an assembler needs to cut the image up: where the banks start
        # and how many there are.  Which of the machine's own pages they go
        # to is the machine's business and not the database's.
        lines = [
            "; Written by regac build.  See doc/binario.md.",
            f"DB_RESIDENT_SIZE equ {database.resident_size}",
            f"DB_BANK_COUNT    equ {len(database.banks)}",
            f"DB_BANK_BYTES    equ {1 << database.page_bits if database.banks else 0}",
        ]
        # And how much of each bank is really used, because a loader has no
        # reason to read the padding that makes them all the same size.
        for number, bank in enumerate(database.banks):
            lines.append(f"DB_BANK_USED_{number}  equ {len(bank)}")
        with open(args.defs, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    print(f"{args.input} -> {args.output}")
    print(f"  machine     {args.machine}")
    print(f"  image       {len(image)} bytes")
    print(f"  resident    {database.resident_size} bytes")
    print(f"  banks       {len(database.banks)}")
    for index, name in enumerate(SECTION_NAMES):
        bank, offset, size = database.placement[index]
        where = "resident" if bank == 0xFF else f"bank {bank}"
        print(f"  {name:<12}{size:7}  {where}")


def cmd_release(args):
    """Put the assembled interpreter on the medium its machine loads from.

    What goes in is the binary the assembler wrote; what comes out is a disk
    and a tape with a loader on them, which is what a person can use.
    """
    with open(args.input, "rb") as f:
        code = f.read()
    name = args.name.upper()
    load = args.load if args.load is not None else LOADS_AT[args.machine]
    screen = None
    if args.screen:
        with open(args.screen, "rb") as f:
            screen = f.read()
        wanted = SCREEN_BYTES[args.machine]
        if len(screen) != wanted:
            sys.exit(f"ERROR: a {args.machine} screen is {wanted} bytes and "
                     f"{args.screen} is {len(screen)}")
    written = []
    if args.machine == "cpc":
        for suffix, make in ((".dsk", cpc_disk), (".cdt", cpc_tape)):
            path = os.path.join(args.output, name.lower() + suffix)
            with open(path, "wb") as f:
                f.write(make(code, name, load, args.entry or load, screen))
            written.append(path)
        how = f'RUN"{name}" on the disk, RUN"" on the tape'
    else:
        path = os.path.join(args.output, name.lower() + ".dsk")
        with open(path, "wb") as f:
            if args.boot:
                # A banked one: the loader is machine code, because paging is
                # not something BASIC can do, and the database follows the
                # interpreter in one file.
                with open(args.boot, "rb") as boot:
                    starter = boot.read()
                with open(args.database, "rb") as database:
                    banks = banks_of(database.read())
                f.write(plus3_banked_disk(starter, code, banks, screen))
                how = f"the Loader entry of its menu, and {len(banks)} banks"
            else:
                f.write(plus3_disk(code, load, screen))
                how = "the Loader entry of the machine's own menu"
        written.append(path)
    print(f"{args.input} -> " + ", ".join(written))
    print(f"  loads at    ${load:04X}, {len(code)} bytes")
    print(f"  starts with {how}")


def main():
    parser = argparse.ArgumentParser("regac", description=f"ReGAC {VERSION}")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("decompile", help="JSON database -> .gac source")
    p.add_argument("input", help="JSON database")
    p.add_argument("output", help="source file to write")
    p.set_defaults(func=cmd_decompile)

    p = sub.add_parser("compile", help=".gac source -> JSON database")
    p.add_argument("input", help="source file")
    p.add_argument("output", help="JSON database to write")
    p.set_defaults(func=cmd_compile)

    p = sub.add_parser("render", help="draw the pictures of an adventure as PNG")
    p.add_argument("input", help="JSON database")
    p.add_argument("output", help="PNG file, or a directory for several")
    p.add_argument("-p", "--picture", type=int, help="one picture id (default: all)")
    p.add_argument("-s", "--scale", type=int, default=2, help="pixel scale")
    p.add_argument(
        "-m",
        "--machine",
        default="spectrum",
        choices=sorted(DEVICES),
        help="which machine to draw for (default: spectrum)",
    )
    p.set_defaults(func=cmd_render)

    p = sub.add_parser(
        "checkgfx", help="compare the pictures on a machine against the Spectrum"
    )
    p.add_argument("input", help="JSON database")
    p.add_argument("-m", "--machine", required=True, choices=sorted(DEVICES))
    p.add_argument(
        "-t",
        "--tolerance",
        type=float,
        default=0.05,
        help="how much of the screen a fill may differ by (default: 0.05)",
    )
    p.set_defaults(func=cmd_checkgfx)

    p = sub.add_parser("build", help="write the binary database for a machine")
    p.add_argument("input", help="JSON database")
    p.add_argument("output", help="binary file to write")
    p.add_argument("-m", "--machine", default="spectrum48", choices=sorted(MACHINES))
    p.add_argument(
        "-b",
        "--banks",
        default="none",
        choices=sorted(BANK_SIZES),
        help="size of a memory bank, or none to keep everything resident",
    )
    p.add_argument(
        "--music-buffer",
        type=int,
        default=0,
        help="bytes to reserve for the tune being played (see doc/binario.md)",
    )
    p.add_argument(
        "--defs",
        help="write an assembler include saying where the banks start",
    )
    p.set_defaults(func=cmd_build)

    p = sub.add_parser("release", help="put an assembled interpreter on a disk and a tape")
    p.add_argument("input", help="the binary the assembler wrote")
    p.add_argument("output", help="where to write the disk and the tape")
    p.add_argument("-m", "--machine", default="cpc", choices=sorted(LOADS_AT))
    p.add_argument("--name", default="JUEGO", help="what the files are called")
    p.add_argument("--load", type=lambda n: int(n, 0), default=None,
                   help="where the binary loads, if not where that machine has it")
    p.add_argument("--entry", type=lambda n: int(n, 0), default=None,
                   help="where it starts, if not where it loads")
    p.add_argument("--boot", help="the assembled loader, for a +3 with banks")
    p.add_argument("--database", help="the built database the banks come from")
    p.add_argument("--screen", help="a dump of the machine's screen, to show "
                                    "while the rest loads")
    p.set_defaults(func=cmd_release)

    p = sub.add_parser("text", help="report what the text costs once packed")
    p.add_argument("input", help="JSON database")
    p.set_defaults(func=cmd_text)

    p = sub.add_parser("check", help="verify that a database survives a round trip")
    p.add_argument("input", help="JSON database")
    p.set_defaults(func=cmd_check)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
