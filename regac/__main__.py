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
from .binary import MACHINES, SECTION_NAMES, Database, Reader
from .devices import DEVICES, device_for, make
from .gfx import Renderer
from .media import (MSX_SCREEN_BYTES, PCW_SCREEN_BYTES, banks_of, cpc6128_disk,
                    cpc_low_tape, cpc_tape, msx_screen, msx_tape,
                    pcw_release, CPC_LOW_CODE_AT, CPC_LOW_ROOM,
                    plus3_banked_disk, plus3_disk)
from .project import (TARGETS, ProjectError, assemble, screen_for,
                      wide)
from .project import read as read_project
from .png import save_picture
from .srcgen import generate
from .text import TextStore
from .srcparse import MACHINE_LABELS, SourceError, parse

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
LOADS_AT = {"cpc464": 0x4000, "cpc6128": 0x8000, "plus3": 0x8000,
            "pcw": 0x0100, "msx": 0x8000}

# And how big a dump of each machine's screen is, which is what a loading
# screen has to be.
SCREEN_BYTES = {"cpc464": 0x4000, "cpc6128": 0x4000, "plus3": 6912,
                "pcw": PCW_SCREEN_BYTES, "msx": MSX_SCREEN_BYTES}


# What Arkos Tracker's own exporter is called, for an author who would rather
# name their tracker's file than export it by hand.  It is looked for in
# tools/, where this project keeps the things it did not write -- the
# assembler and the emulator are there too -- and a project may name another
# command instead.
AKS_EXPORTER = "SongToAkm"


def exporter(root, tree, named=None):
    """The command that turns a tracker's own file into assembly, or None."""
    if named:
        return shlex.split(named)
    for folder in (os.path.join(root, "tools"), os.path.join(tree, "tools")):
        for suffix in (".exe", ""):
            path = os.path.join(folder, AKS_EXPORTER + suffix)
            if os.path.exists(path):
                return [path]
    return None


def exported(name, folder, out, tool):
    """Where the assembly for one tune is.

    A file the tracker has already exported is used where it stands.  The
    tracker's own file is converted first, which is the whole of what an
    author has to do by hand otherwise, and needs Arkos Tracker's exporter:
    without it the build says so and says what to do instead, rather than
    failing somewhere further on with a file the assembler cannot read.
    """
    if not name.lower().endswith(".aks"):
        return os.path.join(folder, name)
    if tool is None:
        raise ProjectError(
            f"{name} is a tracker's own file, and turning one into assembly "
            f"needs Arkos Tracker's exporter: put {AKS_EXPORTER} in tools/, or "
            f"say music-tool in the project, or export the song from the "
            f"tracker yourself and name the .asm in /MUSIC"
        )
    made = os.path.join(out, os.path.splitext(os.path.basename(name))[0] + ".asm")
    done = subprocess.run(tool + [os.path.join(folder, name), made],
                          capture_output=True, text=True)
    if done.returncode or not os.path.exists(made):
        raise ProjectError(
            f"{' '.join(tool)} could not export {name}:\n"
            + (done.stderr or done.stdout).strip()
        )
    return made


def music_source(tunes, folder, out, tool=None):
    """The little source that says what tunes a build has, written from the
    adventure's own /MUSIC.

    It comes in two halves because the two live in different places: the list
    is read at any moment and stays with the player, and the tunes themselves
    go wherever that machine has room -- a page of their own, or under $4000,
    or beside the player on a machine with memory to spare.  The build says
    which half it wants where.

    A file named twice is included once and pointed at twice, because that is
    what subsongs are for: two tunes out of one export share its instruments
    and cost a few hundred bytes instead of a few thousand.
    """
    where = os.path.dirname(os.path.abspath(out))
    labels, seen = [], {}
    for tune in tunes:
        name = tune["file"]
        if name not in seen:
            seen[name] = (f"tune_{len(seen)}",
                          exported(name, folder, where, tool))
        labels.append(seen[name][0])

    lines = [
        "; Written by regac build from the adventure's own /MUSIC.  Run it",
        "; again rather than editing this: what it does and why is in",
        "; doc/pendiente.md and in z80/common/music.asm.",
        "",
        "                IFDEF MUSIC_LIST",
        "music_tunes:",
    ]
    for label, tune in zip(labels, tunes):
        lines.append(f"                MUSIC_TUNE {label}, {label}_end,"
                     f" {tune.get('subsong', 0)}")
    lines += ["music_tunes_end:", "                ENDIF", "",
              "                IFDEF MUSIC_STORE"]
    for label, whole in seen.values():
        try:
            path = os.path.relpath(whole, where)
        except ValueError:      # different drives, so nothing relative to say
            path = whole
        path = path.replace("\\", "/")
        lines += [
            f"{label}:",
            "                IFDEF MUSIC_PAGED",
            "                DISP    music_buffer",
            "                ENDIF",
            # The tracker names an export's labels after the song, and a song
            # nobody named is exported as Untitled: two of those in one build
            # would be the same label twice.
            f"                MODULE  {label}_song",
            f'                include "{path}"',
            "                ENDMODULE",
            "                IFDEF MUSIC_PAGED",
            "                ENT",
            "                ENDIF",
            f"{label}_end:",
        ]
    lines += ["                ENDIF", ""]
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return seen


def noises_source(noises, out):
    """The three bytes a noise is, written where the interpreter reads them.

    A pitch, how many steps it lasts and what to add to the pitch every step:
    the same three the five that come with the interpreter are, because an
    author's noises are not a different kind of thing from ours.
    """
    lines = ["; Written by regac build from the adventure's own /SOUND.",
             "; A bigger pitch is a lower note; the step is what to add to it."]
    for number, (pitch, steps, step) in enumerate(noises, 1):
        lines.append(f"                db      {pitch}, {steps}, {step}"
                     f"{'':<{max(1, 12 - len(str(pitch) + str(steps) + str(step)))}}"
                     f"; {number}")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


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
    noises = ddb.get("sounds") or []
    if noises and args.music_defs:
        # Beside the tunes, because they are the same kind of thing: what the
        # adventure asks for, written where the assembler looks.
        where = os.path.join(os.path.dirname(os.path.abspath(args.music_defs)),
                             "noises.asm")
        noises_source(noises, where)
        print(f"{args.input} -> {where}")
        print(f"  noises      {len(noises)}")
    tunes = ddb.get("music") or []
    if args.music_defs:
        root = os.path.dirname(os.path.abspath(args.input))
        tree = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        try:
            songs = music_source(tunes, root, args.music_defs,
                                 exporter(root, tree, args.music_tool))
        except ProjectError as e:
            sys.exit(f"ERROR: {e}")
        print(f"{args.input} -> {args.music_defs}")
        print(f"  tunes       {len(tunes)}, out of {len(songs)} exported")
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
                boot=None, banks=None, database=None, music=None):
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
                                 music))
        written.append(path)
        how = f'RUN"{name}" on the disk, with {len(banks or [])} banks behind it'
        if music:
            how += f", and {len(music)} bytes of music"
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
                                     music))
            else:
                f.write(cpc_tape(code, name, load, entry, screen, music))
        written.append(path)
        how = 'RUN"" on the tape'
        if entry == CPC_LOW_CODE_AT:
            how += ", with the interpreter under the database"
        if music:
            how += f", with {len(music)} bytes of music in front of it"
    else:
        path = os.path.join(where, name.lower() + ".dsk")
        with open(path, "wb") as f:
            if boot is not None:
                # A banked one: the loader is machine code, because paging is
                # not something BASIC can do, and the database follows the
                # interpreter in one file -- with the music between them, when
                # there is any, because that is where its table asks for it.
                f.write(plus3_banked_disk(boot, code, banks or [], screen,
                                          music or ()))
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
    music = None
    if args.music:
        with open(args.music, "rb") as f:
            music = f.read()
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
                               database, music)
    print(f"{args.input} -> " + ", ".join(written))
    print(f"  loads at    ${load:04X}, {len(code)} bytes")
    print(f"  starts with {how}")


def write_database(ddb, path, machine, banks, music_buffer=0, defs=None):
    """The binary database one machine reads, and the include an assembler
    needs to cut it up."""
    database = Database(ddb, machine=machine, page_bits=BANK_SIZES[banks],
                        music_buffer=music_buffer)
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
            music = make_music(ddb, root, tree, project.get("effects"),
                               project.get("music-tool"))
            written = make_one(TARGETS[which], settings, ddb, name, root, output,
                               tree, music)
        except ProjectError as e:
            sys.exit(f"ERROR: {which}: {e}")
        print(f"{which:12} -> " + ", ".join(
            os.path.relpath(path, output) for path in written))


def make_music(ddb, root, where_regac_is, effects=None, tool=None):
    """Put what the adventure says about its music where the assembler looks.

    The author's part is a line a tune in the adventure's own /MUSIC and the
    files the tracker exported; the rest is written here.  Nothing is copied
    but the bank of effects, which is small and has a fixed name in the
    builds: the tunes stay where the author keeps them and are named by path.
    """
    tunes = ddb.get("music") or []
    noises = ddb.get("sounds") or []
    folder = os.path.join(where_regac_is, "music")
    if noises:
        os.makedirs(folder, exist_ok=True)
        noises_source(noises, os.path.join(folder, "noises.asm"))
    if not tunes:
        # Noises of one's own are not music: they are played by the speaker,
        # or by the sound chip with nothing else going on, so they go in
        # whether or not there is a tune.
        return ["WITH_OWN_NOISES"] if noises else []
    os.makedirs(folder, exist_ok=True)
    music_source(tunes, root, os.path.join(folder, "tunes.asm"),
                 exporter(root, where_regac_is, tool))
    defines = ["WITH_MUSIC"] + (["WITH_OWN_NOISES"] if noises else [])
    if effects:
        shutil.copyfile(os.path.join(root, effects),
                        os.path.join(folder, "effects.asm"))
        defines.append("WITH_EFFECTS")
    return defines


def makes_a_noise(ddb):
    """Whether the adventure ever asks for a noise.

    The interpreter that can make one costs the Amstrad a hundred and sixty
    three bytes, and that machine counts every one of them.  None of the eight
    adventures of 1986 asks: SOUND and QUIET are opcodes of ours and nothing
    written then could use them.  The same rule as the music, which the
    project set long ago -- what an adventure does not do does not travel
    with it.
    """
    tables = [ddb.get("hpcs") or [], ddb.get("lpcs") or []]
    tables += list((ddb.get("lcs") or {}).values())
    return any(step and step[0] in ("SOUND", "QUIET")
               for table in tables for step in table)


def make_one(target, settings, ddb, name, root, output, where_regac_is,
             music=()):
    """One machine, end to end: its database, its interpreter, its medium."""
    tree = os.path.join(where_regac_is, target.folder)
    database = write_database(
        ddb, os.path.join(tree, target.database),
        machine=target.machine,
        banks=settings.get("banks", target.banks),
        music_buffer=settings.get("music-buffer", 0),
        defs=os.path.join(tree, target.defs) if target.defs else None,
    )
    screen = None
    # A machine with no sound chip gets no tunes, but noises of the
    # adventure's own are not tunes: they are played by a speaker, and every
    # machine but the PCW has one.
    defines = [word for word in music
               if target.music is not None or word == "WITH_OWN_NOISES"]
    if makes_a_noise(ddb):
        defines.append("NOISES")
    if music and target.music is None and (ddb.get("music") or []):
        print(f"  {target.machine:12} carries no music: it is left out")
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
    tunes = None
    if defines and target.music:
        # A machine whose music does not travel inside the interpreter: the
        # Amstrad, where it is a file of its own with a mover in front, and
        # the +3, where it is two more pieces of the one file the loader
        # reads.  One name or several, in the order they are wanted.
        names = ([target.music] if isinstance(target.music, str)
                 else list(target.music))
        pieces = []
        for named in names:
            with open(os.path.join(tree, named), "rb") as f:
                pieces.append(f.read())
        tunes = pieces[0] if len(pieces) == 1 else pieces
    if low:
        load = entry = CPC_LOW_CODE_AT
    else:
        entry = load
    written, _ = write_media(target.release, code, where, name, load, entry,
                             screen, boot, banks, image, tunes)
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
    p.add_argument("--music-tool",
                   help="the command that turns a tracker's own file into "
                        "assembly, if the tunes are named as .aks")
    p.add_argument("--music-defs",
                   help="write the source that says what tunes there are, for "
                        "the assembler to include")
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
    p.add_argument("--music", help="the assembled music, for a machine that "
                                   "loads it as a file of its own")
    p.set_defaults(func=cmd_release)

    p = sub.add_parser("make", help="build an adventure for every machine a "
                                    "project file names")
    p.add_argument("input", help="the project file")
    p.add_argument("-o", "--output", help="where the media go, if not where "
                                          "the project says")
    p.add_argument("-t", "--target", action="append",
                   help="only this machine, and again for more than one")
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
