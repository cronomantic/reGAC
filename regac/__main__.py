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
import shlex
import shutil
import subprocess
import json
import os
import sys

from .check import problems_of
from .binary import MACHINES, SECTION_NAMES, BuildError, Database, Reader
from .devices import DEVICES, device_for, from_an_amstrad, make
from .gfx import Renderer
from .media import (MSX_SCREEN_BYTES, PCW_SCREEN_BYTES, banks_of, cpc6128_disk,
                    cpc_low_tape, cpc_tape, msx_screen, msx_tape,
                    pcw_release, CPC_LOW_CODE_AT, CPC_LOW_ROOM,
                    plus3_banked_disk, plus3_disk, mz_exe, MZ_STACK_BYTES)
from .project import (TARGETS, ProjectError, assemble, screen_for,
                      wide)
from .project import read as read_project
from .png import save_picture
from .srcgen import generate
from .text import INK_CHAR, TextStore, commands_of, expand
from .srcparse import (MACHINE_LABELS, SOUND_CHANNEL_NAMES, SourceError,
                        a_noise, parse)

VERSION = "0.2.0"


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
        # A source may point at a font of its own, and where it points is
        # from where it stands.
        ddb = parse(source, name, os.path.dirname(os.path.abspath(args.input)),
                    machine=args.machine)
    except SourceError as e:
        sys.exit(f"ERROR: {e}")
    write_json(args.output, ddb)
    print(f"{args.input} -> {args.output}")


def cmd_check(args):
    """Say whether an adventure survives a round trip and whether it makes
    sense, which are two different questions.

    The round trip is about this tool: decompiled and recompiled, does the
    adventure come back the same?  The rest is about the adventure: does every
    number that points at something point at something that is there?
    """
    original = read_json(args.input)
    name = os.path.basename(args.input)
    wrong = False
    try:
        rebuilt = json.loads(json.dumps(parse(generate(original, name), name)))
    except SourceError as e:
        sys.exit(f"ERROR: {e}")
    if rebuilt == original:
        print(f"{name}: round trip exact")
    else:
        differing = sorted(k for k in set(original) | set(rebuilt)
                           if original.get(k) != rebuilt.get(k))
        print(f"{name}: round trip differs in {', '.join(differing)}")
        wrong = True

    found = problems_of(original)
    faults = [p for p in found if p.fault]
    for problem in found:
        print(f"{name}: {problem}")
    if found:
        print(f"{name}: {len(faults)} faults and {len(found) - len(faults)}"
              f" warnings")
    else:
        print(f"{name}: nothing points anywhere it should not")
    if wrong or faults:
        sys.exit(1)


def cmd_render(args):
    """Draw one picture of an adventure, or all of them, as PNG files."""
    ddb = read_json(args.input)
    gfx = ddb["gfx"]
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
        picture = Renderer(gfx, device_for(machine, gfx, pid, ddb)).run(int(pid))
        if os.path.isdir(args.output):
            path = os.path.join(args.output, f"{pid}.png")
        else:
            path = args.output
        save_picture(path, picture, scale=args.scale)
        print(f"picture {pid} -> {path}")


def cmd_draw(args):
    """Look at a picture in a window, drawn again whenever the source is
    saved.  See regac/viewer.py."""
    from .viewer import SPECTRUM_MACHINES, run

    if args.machine is not None and args.machine not in SPECTRUM_MACHINES:
        sys.exit(f"ERROR: there is nothing to draw {args.machine} with; "
                 f"try one of {', '.join(SPECTRUM_MACHINES)}")
    try:
        run(args.input, args.picture, args.machine, args.scale, args.trace)
    except ValueError as e:
        sys.exit(f"ERROR: {e}")


def cmd_map(args):
    """The map of an adventure, as an SVG.  See regac/mapper.py."""
    from .mapper import svg
    from .viewer import read_adventure

    try:
        ddb = read_adventure(args.input, args.machine)
    except (SourceError, OSError, ValueError) as e:
        sys.exit(f"ERROR: {e}")
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(svg(ddb, os.path.basename(args.input)))
    print(f"{args.input} -> {args.output}")


def cmd_play(args):
    """Play a file of orders and say whether the game ended.  See
    regac/play.py."""
    from .play import orders_of, play
    from .viewer import read_adventure

    try:
        ddb = read_adventure(args.input, args.machine)
        with open(args.orders, encoding="utf-8") as f:
            orders = orders_of(f.read())
        ended, said = play(ddb, orders)
    except (SourceError, OSError, ValueError) as e:
        sys.exit(f"ERROR: {e}")
    sys.stdout.write(said)
    won = ended and (args.expect is None or args.expect in said)
    if not ended:
        print("\n-- the orders ran out with the game still asking",
              file=sys.stderr)
    elif args.expect is not None and not won:
        print(f"\n-- the game ended without saying {args.expect!r}",
              file=sys.stderr)
    else:
        print("\n-- the game ended", file=sys.stderr)
    sys.exit(0 if won else 1)


def cmd_lint(args):
    """What the adventure has that nothing uses.  See regac/lint.py."""
    from .lint import notes_of
    from .viewer import read_adventure

    try:
        ddb = read_adventure(args.input, args.machine)
    except (SourceError, OSError, ValueError) as e:
        sys.exit(f"ERROR: {e}")
    notes = notes_of(ddb)
    for note in notes:
        print(note)
    if not notes:
        print("nothing that nothing uses")


def cmd_checkgfx(args):
    """Compare the pictures on a target machine against the Spectrum.

    A fill spreads until the outlines stop it, so a change of resolution can
    let one escape through a gap the scaling opened, or strand its starting
    point on the wrong side of a line.  Comparing how much of the screen each
    fill reaches on each machine catches exactly that.
    """
    ddb = read_json(args.input)
    gfx = ddb["gfx"]
    name = os.path.basename(args.input)
    if from_an_amstrad(ddb):
        sys.exit(f"{name} was written on an Amstrad: its pictures are drawn with "
                 "the Amstrad's rules and there is no Spectrum to compare them with")
    suspect = 0
    for pid in sorted(gfx, key=int):
        reference = Renderer(gfx, make("spectrum"))
        reference.run(int(pid))
        target = Renderer(gfx, device_for(args.machine, gfx, pid, ddb))
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


BANK_SIZES = {"none": 0, "8k": 13, "16k": 14, "64k": 16}

# Where each machine's interpreter is built to sit, which is where its medium
# has to put it.
LOADS_AT = {"cpc464": 0x4000, "cpc6128": 0x8000, "plus3": 0x8000,
            "pcw": 0x0100, "msx": 0x8000}

# And how big a dump of each machine's screen is, which is what a loading
# screen has to be.
SCREEN_BYTES = {"cpc464": 0x4000, "cpc6128": 0x4000, "plus3": 6912,
                "pcw": PCW_SCREEN_BYTES, "msx": MSX_SCREEN_BYTES}


def noises_source(noises, out):
    """The four bytes a noise is, written where the interpreter reads them.

    A pitch, how many waves it lasts, what to add to the pitch every one, and
    what it comes out of: the same four the five that come with the
    interpreter are, because an author's noises are not a different kind of
    thing from ours.
    """
    lines = ["; Written by regac build from the adventure's own /SOUND.",
             "; A bigger pitch is a lower note; the step is what to add to it;",
             "; the last is the tone generator, the noise one, or both."]
    for number, said in enumerate(noises, 1):
        pitch, waves, step, out_of = a_noise(said)
        numbers = f"{pitch}, {waves}, {step}, {out_of}"
        lines.append(f"                db      {numbers}"
                     f"{'':<{max(1, 16 - len(numbers))}}"
                     f"; {number}, {SOUND_CHANNEL_NAMES[out_of]}")
    with open(out, "w", encoding="utf-8") as f:
        f.write(chr(10).join(lines) + chr(10))


def cmd_build(args):
    """Write the binary database the 8 bit interpreter reads."""
    ddb = read_json(args.input)
    try:
        database = Database(
            ddb,
            machine=args.machine,
            page_bits=BANK_SIZES[args.banks],
        )
        image = database.build()
    except BuildError as e:
        sys.exit(f"ERROR: {e}")
    with open(args.output, "wb") as f:
        f.write(image)
    noises = ddb.get("sounds") or []
    if noises and args.noises:
        noises_source(noises, args.noises)
        print(f"{args.input} -> {args.noises}")
        print(f"  noises      {len(noises)}")
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


def write_media(machine, code, where, name, load, entry, screen=None,
                boot=None, banks=None, database=None):
    """Put an assembled interpreter on the medium its machine loads from, and
    say what was written and how a person starts it."""
    written = []
    if machine == "pcw":
        # A machine that starts itself: no operating system, no loader in
        # BASIC, just the sector it boots from and the pieces behind it.
        if boot is None or banks is None:
            sys.exit("ERROR: a pcw release wants --boot and --database")
        path = os.path.join(where, name.lower() + ".dsk")
        with open(path, "wb") as f:
            f.write(pcw_release(boot, code, banks, screen))
        written.append(path)
        how = f"nothing: the machine starts it, with {len(banks)} banks behind it"
    elif machine == "msx":
        # A machine with a cassette and no banks: the interpreter is a file
        # and the database is the blocks behind it, which the interpreter
        # reads itself once it has somewhere to put them.
        path = os.path.join(where, name.lower() + ".cas")
        with open(path, "wb") as f:
            f.write(msx_tape(code, database or b"", screen, load, entry, name))
        written.append(path)
        how = (f'BLOAD"CAS:",R, with {"a screen and " if screen else ""}'
               f'{len(database or b"")} bytes behind it')
    elif machine == "cpc6128":
        # A disk and another sixty four kilobytes: every piece is a file with
        # its own header, and the loader pages before each bank goes in.  The
        # resident half travels the same way, through the window, in the bank
        # that is there when nothing has been paged.
        if database is None:
            sys.exit("ERROR: a cpc6128 release wants --database")
        resident = database[:Reader(database).resident_size]
        path = os.path.join(where, name.lower() + ".dsk")
        with open(path, "wb") as f:
            f.write(cpc6128_disk(code, resident, banks or [], name, screen,
                                 ))
        written.append(path)
        how = f'RUN"{name}" on the disk, with {len(banks or [])} banks behind it'
    elif machine == "cpc464":
        # A tape and sixty four kilobytes: the loader is in BASIC, and what
        # it runs is whatever comes first, so RUN and nothing else.
        path = os.path.join(where, name.lower() + ".cdt")
        with open(path, "wb") as f:
            if entry == CPC_LOW_CODE_AT:
                # The other way round, because this database leaves no room
                # above $4000: the interpreter is carried under it and the
                # database is a file of its own.
                f.write(cpc_low_tape(code, database or b"", name, screen,
                                     ))
            else:
                f.write(cpc_tape(code, name, load, entry, screen))
        written.append(path)
        how = 'RUN"" on the tape'
        if entry == CPC_LOW_CODE_AT:
            how += ", with the interpreter under the database"
    else:
        path = os.path.join(where, name.lower() + ".dsk")
        with open(path, "wb") as f:
            if boot is not None:
                # A banked one: the loader is machine code, because paging is
                # not something BASIC can do, and the database follows the
                # interpreter in one file.
                f.write(plus3_banked_disk(boot, code, banks or [], screen,
                                          ))
                how = f"the Loader entry of its menu, and {len(banks or [])} banks"
            else:
                f.write(plus3_disk(code, load, screen))
                how = "the Loader entry of the machine's own menu"
        written.append(path)
    return written, how


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
        if args.machine == "msx":
            screen = msx_screen(screen)
        if len(screen) != wanted:
            sys.exit(f"ERROR: a {args.machine} screen is {wanted} bytes and "
                     f"{args.screen} is {len(screen)}")
    boot = banks = database = None
    if args.boot:
        with open(args.boot, "rb") as f:
            boot = f.read()
    if args.database:
        with open(args.database, "rb") as f:
            database = f.read()
        banks = banks_of(database)
    written, how = write_media(args.machine, code, args.output, name, load,
                               args.entry or load, screen, boot, banks,
                               database)
    print(f"{args.input} -> " + ", ".join(written))
    print(f"  loads at    ${load:04X}, {len(code)} bytes")
    print(f"  starts with {how}")


def write_database(ddb, path, machine, banks, defs=None):
    """The binary database one machine reads, and the include an assembler
    needs to cut it up."""
    database = Database(ddb, machine=machine, page_bits=BANK_SIZES[banks],
                        )
    with open(path, "wb") as f:
        f.write(database.build())
    if defs:
        # What an assembler needs: where the banks start and how many there
        # are.  Which of the machine's own pages they go to is the machine's
        # business and not the database's.
        lines = [
            "; Written by regac.  See doc/binario.md.",
            f"DB_RESIDENT_SIZE equ {database.resident_size}",
            f"DB_BANK_COUNT    equ {len(database.banks)}",
            f"DB_BANK_BYTES    equ {1 << database.page_bits if database.banks else 0}",
        ]
        # And how much of each bank is really used, because a loader has no
        # reason to read the padding that makes them all the same size.
        for number, bank in enumerate(database.banks):
            lines.append(f"DB_BANK_USED_{number}  equ {len(bank)}")
        with open(defs, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    return database


# The PC's stack: the unpacking of a message calls itself, and a picture calls
# others eight deep.
PC_STACK_BYTES = 2 * MZ_STACK_BYTES


def dos_name(name):
    """A name DOS will run: letters and digits, eight at most, in capitals."""
    kept = "".join(c for c in name.upper() if c.isascii() and c.isalnum())
    return (kept or "GAME")[:8]


def cmd_make(args):
    """Build an adventure for every machine its project file names.

    One file and one command instead of a dozen: what is of the machine --
    which banks, which loading screen, how big the pictures are drawn -- is
    said once, in the project, and this does the rest.
    """
    try:
        project = read_project(args.input)
    except ProjectError as e:
        sys.exit(f"ERROR: {e}")
    root = os.path.dirname(os.path.abspath(args.input)) or "."
    source = os.path.join(root, project["source"])
    written_source = None
    if source.endswith(".gac"):
        with open(source, encoding="utf-8") as f:
            written_source = f.read()
    else:
        ddb = read_json(source)
    name = project["name"]
    output = args.output or os.path.join(root, project["output"])

    # The adventure and its loading screens sit beside the project file; the
    # interpreters sit where reGAC itself is installed.
    tree = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    wanted = args.target or sorted(project["targets"])
    everything = []
    for which in wanted:
        settings = project["targets"].get(which)
        if settings is None:
            sys.exit(f"ERROR: the project says nothing about {which}")
        # A source is read again for every machine, because it may keep some
        # of itself back for some of them; a JSON has no such thing in it and
        # is read once.
        if written_source is not None:
            try:
                # From the folder the source is in, which is what a file= in
                # it is relative to: a font, another source it includes.  This
                # said nothing, so `make` looked for them where it was run
                # from and `compile` looked where the source was.
                ddb = parse(written_source, os.path.basename(source),
                            os.path.dirname(os.path.abspath(source)),
                            machine=which)
            except SourceError as e:
                sys.exit(f"ERROR: {e}")
        try:
            noises = make_noises(ddb, tree)
            written = make_one(TARGETS[which], settings, ddb, name, root, output,
                               tree, noises)
        except (ProjectError, BuildError) as e:
            sys.exit(f"ERROR: {which}: {e}")
        print(f"{which:12} -> " + ", ".join(
            os.path.relpath(path, output) for path in written))
        everything += written
    if args.zip:
        # What was built, a folder a machine as it is on the disk, in one
        # file to hand out: a release, for one.
        import zipfile

        with zipfile.ZipFile(args.zip, "w", zipfile.ZIP_DEFLATED) as bundle:
            for path in everything:
                bundle.write(path, os.path.relpath(path, output))
        print(f"{'':12} -> {args.zip}")


def make_noises(ddb, where_regac_is):
    """Put what the adventure says about its noises where the assembler
    looks.  There is no music to put: the tracker player was taken out, and
    a noise of one's own is not music -- it is played by the speaker, or by
    the sound chip with nothing else going on."""
    noises = ddb.get("sounds") or []
    if not noises:
        return []
    folder = os.path.join(where_regac_is, "music")  # where the assembler looks
    os.makedirs(folder, exist_ok=True)
    noises_source(noises, os.path.join(folder, "noises.asm"))
    return ["WITH_OWN_NOISES"]


def makes_a_noise(ddb):
    """Whether the adventure ever asks for a noise.

    The interpreter that can make one costs the Amstrad a hundred and sixty
    three bytes, and that machine counts every one of them.  None of the eight
    adventures of 1986 asks: SOUND and QUIET are opcodes of ours and nothing
    written then could use them.  The same rule as the noises, which the
    project set long ago -- what an adventure does not do does not travel
    with it.
    """
    return uses(ddb, ("SOUND", "QUIET"))


def has_holes(ddb):
    """Whether any text of the adventure has a hole in it -- a counter, an
    object's name or the turns, printed where it stands -- which is what the
    interpreter needs -DHOLES for."""
    texts = list((ddb.get("messages") or {}).values())
    texts += [room.get("desc", "") for room in (ddb.get("locations") or {}).values()]
    texts += [one.get("name", "") for one in (ddb.get("objects") or {}).values()]
    return any(which != INK_CHAR
               for text in texts for which, _, _ in commands_of(expand(text)))


def uses(ddb, names):
    """Whether any table of the adventure has one of those opcodes."""
    tables = [ddb.get("hpcs") or [], ddb.get("lpcs") or []]
    tables += list((ddb.get("lcs") or {}).values())
    tables += list((ddb.get("procs") or {}).values())
    return any(step and step[0] in names
               for table in tables for step in table)


def make_one(target, settings, ddb, name, root, output, where_regac_is,
             noises=()):
    """One machine, end to end: its database, its interpreter, its medium."""
    tree = os.path.join(where_regac_is, target.folder)
    database = write_database(
        ddb, os.path.join(tree, target.database),
        machine=target.machine,
        banks=settings.get("banks", target.banks),
        defs=os.path.join(tree, target.defs) if target.defs else None,
    )
    screen = None
    defines = list(noises)
    if makes_a_noise(ddb):
        defines.append("NOISES")
    if uses(ddb, ("DO",)):
        # DO and what it needs travel only when the adventure says it, by
        # the same rule as the noises
        defines.append("PROCS")
    if has_holes(ddb):
        defines.append("HOLES")
    if target.machine in ("cpc", "next", "pc") and from_an_amstrad(ddb):
        # drawn with the rules of the GAC it was written with
        defines.append("AMSTRAD_PICTURES")
    if target.assembler == "nasm" and "WITH_OWN_NOISES" in defines:
        # NASM is told where the adventure's noises are, rather than finding
        # them by a path from where it sits
        where = os.path.join(where_regac_is, "music", "noises.asm")
        defines.append(f'NOISES_FILE="{where.replace(os.sep, "/")}"')
    if target.machine == "next":
        # its game goes in a file named after it, beside the .nex
        defines.append(f'SAVE_NAME="{dos_name(name)}.SAV"')
    if settings.get("screen"):
        screen = screen_for(target, settings["screen"], root)
        if target.screen_when == "assembly":
            # This machine's medium is written by the assembler itself, or
            # from pieces it saves, so the screen has to be there by then.
            with open(os.path.join(tree, "screen.bin"), "wb") as f:
                f.write(screen)
            defines.append("SCREEN")
    if settings.get("scale"):
        across, _ = wide(settings["scale"])
        defines.append(f"PICTURE_SCALE={across}")
    low = False
    try:
        assemble(target, where_regac_is, defines)
    except ProjectError:
        # The one machine with nowhere to put an overflow is the 464: no
        # banks, and a database that has to sit in one stretch.  When the two
        # together pass the firmware, the interpreter goes under $4000
        # instead and the database has everything above it -- 27392 bytes
        # rather than what is left over the code.  See z80/cpc/game.asm.
        if target.release != "cpc464":
            raise
        assemble(target, where_regac_is, list(defines) + ["LOW_CODE"])
        low = True
        print(f"  {target.machine:12} does not fit the usual way round: the "
              "interpreter goes under the database")

    where = os.path.join(output, target.machine if target.release is None
                         else target.release)
    os.makedirs(where, exist_ok=True)
    if target.machine == "pc":
        # The whole of it is one .EXE: the image NASM made, the database
        # inside it, and the header regac writes in front.
        with open(os.path.join(tree, target.binary), "rb") as f:
            image = f.read()
        path = os.path.join(where, dos_name(name) + ".EXE")
        with open(path, "wb") as f:
            f.write(mz_exe(image, stack=PC_STACK_BYTES))
        return [path]
    if target.media:
        # The assembler wrote the medium as it went; it only has to be given
        # the name the project asked for.
        written = []
        for made in target.media:
            path = os.path.join(where, name.lower() + os.path.splitext(made)[1])
            shutil.copyfile(os.path.join(tree, made), path)
            written.append(path)
        return written
    with open(os.path.join(tree, target.binary), "rb") as f:
        code = f.read()
    boot = None
    if target.boot:
        with open(os.path.join(tree, target.boot), "rb") as f:
            boot = f.read()
    with open(os.path.join(tree, target.database), "rb") as f:
        image = f.read()
    banks = banks_of(image) if target.defs else None
    load = LOADS_AT[target.release]
    if low:
        load = entry = CPC_LOW_CODE_AT
    else:
        entry = load
    written, _ = write_media(target.release, code, where, name, load, entry,
                             screen, boot, banks, image)
    return written


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
    p.add_argument("-m", "--machine", choices=sorted(MACHINE_LABELS),
                   help="which machine to read it for, for a source that "
                        "keeps some lines for some of them")
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

    p = sub.add_parser("draw", help="look at a picture in a window, drawn "
                                    "again whenever the source is saved")
    p.add_argument("input", help="source file, or JSON database")
    p.add_argument("picture", type=int, nargs="?",
                   help="which picture (default: the first)")
    p.add_argument("-m", "--machine",
                   help="which machine to draw it as: spectrum, cpc, msx, "
                        "pcw, next or cga, which is the PC's (default: the "
                        "first the adventure can be drawn on)")
    p.add_argument("-s", "--scale", type=int, default=3, help="pixel scale")
    p.add_argument("--trace", help="an image to draw over, or a folder with "
                                   "one to each picture, named 12.png")
    p.set_defaults(func=cmd_draw)

    p = sub.add_parser("play", help="play a file of orders, and say whether "
                                    "the game ended")
    p.add_argument("input", help="source file, or JSON database")
    p.add_argument("orders", help="a file of orders, one a line")
    p.add_argument("--expect", help="and it has to have said this")
    p.add_argument("-m", "--machine", default="spectrum48",
                   choices=sorted(MACHINE_LABELS),
                   help="which machine to read a source for")
    p.set_defaults(func=cmd_play)

    p = sub.add_parser("lint", help="what the adventure has that nothing "
                                    "uses: rooms, objects, words, messages")
    p.add_argument("input", help="source file, or JSON database")
    p.add_argument("-m", "--machine", default="spectrum48",
                   choices=sorted(MACHINE_LABELS),
                   help="which machine to read a source for")
    p.set_defaults(func=cmd_lint)

    p = sub.add_parser("map", help="the map of an adventure, as SVG")
    p.add_argument("input", help="source file, or JSON database")
    p.add_argument("output", help="SVG file to write")
    p.add_argument("-m", "--machine", default="spectrum48",
                   choices=sorted(MACHINE_LABELS),
                   help="which machine to read a source for, for one that "
                        "keeps some lines for some of them")
    p.set_defaults(func=cmd_map)

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
    p.add_argument("--noises",
                   help="write the source that says what noises there are, "
                        "for the assembler to include")
    p.add_argument(
        "--defs",
        help="write an assembler include saying where the banks start",
    )
    p.set_defaults(func=cmd_build)

    p = sub.add_parser("release", help="put an assembled interpreter on a disk and a tape")
    p.add_argument("input", help="the binary the assembler wrote")
    p.add_argument("output", help="where to write the disk and the tape")
    p.add_argument("-m", "--machine", default="cpc464", choices=sorted(LOADS_AT))
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

    p = sub.add_parser("make", help="build an adventure for every machine a "
                                    "project file names")
    p.add_argument("input", help="the project file")
    p.add_argument("-o", "--output", help="where the media go, if not where "
                                          "the project says")
    p.add_argument("-t", "--target", action="append",
                   help="only this machine, and again for more than one")
    p.add_argument("--zip", help="and everything it built in this zip file, "
                                 "a folder a machine")
    p.set_defaults(func=cmd_make)

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
