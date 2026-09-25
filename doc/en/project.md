# The project file

*[Leer en español](../proyecto.md)*

An adventure says nothing of banks, nor of loading screens, nor of the size
its pictures are drawn at. Those are decisions about **where it goes**, not
about what it is, and they go together in one file; a single command builds
everything that file names:

    python -m regac make faro.toml

It is the same principle that parts the `.gac` source from the target
machine, already written in [`source-format.md`](source-format.md): *what is
the adventure's goes in the source; what is the machine's goes in the project
file*.

## What it looks like

TOML, which Python's standard library reads from 3.11 on, with nothing to
install:

    name    = "faro"             # what the media that come out are called
    source  = "faro.gac"         # the adventure: a .gac source or a .json
    output  = "salida"           # where they are left, a folder a machine

    [targets.spectrum48]

    [targets.spectrum128]
    screen = "loading.scr"

    [targets.plus3]
    screen = "loading.scr"

    [targets.cpc6128]
    screen = "loading.cpc"

    [targets.pcw]
    screen = "loading.pcw"
    scale  = 2

The paths are counted from the project file itself. `name` and `source` have
to be said; `output`, if it is not said, is `release`. The machines are called
`spectrum48`, `spectrum128`, `plus3`, `cpc464`, `cpc6128`, `msx`, `next`,
`pcw` and `pc`.

## The knobs

| key | what it says | by default |
|---|---|---|
| `banks` | the size of a bank: `none`, `8k`, `16k` or `64k` | what that machine usually uses |
| `screen` | the screen dump seen while it loads | none |
| `scale` | how many of the machine's pixels a point of the picture takes: a number, or two as `[2, 1]` | 1 |

The three are a machine's. At the top, for the whole project, go only `name`,
`source`, `output` and `targets`.

A name not in that list is a mistake and is said, instead of something else
being built in silence; the same with a machine that does not exist, or with a
scale that machine cannot draw at.

**The scale goes to both ends.** It is not a label: the interpreter is
assembled with it (`PICTURE_SCALE`) and the reference renderer is given the
same number, so the test that compares the one with the other still holds.
Today only the PCW has anything to choose from -- one or two points wide --
because it is the only machine whose screen is wider than the picture; the
others draw at their natural size, and telling them otherwise is a mistake.

**The loading screen is checked**: if it does not measure what that machine's
screen measures, it complains and writes nothing. The MSX also takes the
`.SC2` as a drawing program writes it, which is the dump with seven bytes of
header in front.

## What does *not* go here

Nothing the machine decides for itself. Which pages of a Spectrum the banks
fall in, where the interpreter loads, how much a screen dump takes, which file
of each tree is assembled: those are facts of the machine and they live in the
table of `regac/project.py` or in the machine's own source. The project file
chooses among what the machine offers; it does not reinvent it.

Nor the noises: the ones an adventure asks for go in its source, in `/SOUND`.

## What it does for each machine

1. **The database** that machine reads, with the banks asked for, and the
   `.inc` the assembler needs to share it out.
2. **The loading screen**, if there is one: checked, and put where it has to
   be -- beside the source when the medium is written by the assembler, or
   handed to `release` when it writes it.
3. **The interpreter**, assembled with what the project said and with what
   the adventure uses: `DO`, the holes in the text, the noises.
4. **The medium**, in `salida/<machine>/`. Each machine in its own folder,
   which is needed: they all call their files the same.

With `-t` only one is built, and with `--zip` what was built goes into a zip
as well, a folder a machine:

    python -m regac make faro.toml -t pcw
    python -m regac make faro.toml --zip faro.zip

## What comes out

    cpc464       -> cpc464\faro.cdt
    cpc6128      -> cpc6128\faro.dsk
    msx          -> msx\faro.cas
    next         -> next\faro.nex
    pc           -> pc\FARO.EXE
    pcw          -> pcw\faro.dsk
    plus3        -> plus3\faro.dsk
    spectrum128  -> spectrum128\faro.tap
    spectrum48   -> spectrum48\faro.tap
