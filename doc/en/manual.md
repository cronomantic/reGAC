# reGAC manual

*[Leer en español](../manual.md)*

This and [`gac.md`](gac.md) are all that is needed. Between them is the whole
road: what to install, how an adventure is written, how it is checked and how
it is built for nine machines. [`source-format.md`](source-format.md) is the
source format in full, and [`project.md`](project.md) the project file.

The rest of `doc/`, in Spanish only, is the **development diary** -- what was
measured, in what order and why -- and it is not reference material.

---

## 1. What this is

A text adventure in the manner of the **Graphic Adventure Creator** of 1986,
written in a text file, and published with a single command on:

| machine | what comes out |
|---|---|
| Spectrum 48 | tape `.tap` |
| Spectrum 128 | tape `.tap` |
| Spectrum +3 | disk `.dsk` |
| Amstrad CPC 464 | tape `.cdt` |
| Amstrad CPC 6128 | disk `.dsk` |
| Amstrad PCW | disk `.dsk` that starts by itself |
| MSX | tape `.cas` |
| Spectrum Next | `.nex` |
| PC with a CGA | DOS `.EXE` |

It can be started from nothing or **from an adventure that already exists**:
there is a decompiler that turns what is inside a tape, a disk or a snapshot
of 1986 into readable source.

---

## 2. What it needs

- **Python 3.11 or newer.** From 3.11 the standard library reads TOML, which
  is what the project files are written in.
- **`sjasmplus`, in `tools/` or on the path**, which assembles the
  interpreters. Without it an adventure can be written and checked, but not
  built.
- **NASM, in `tools/` or on the path**, only for the PC, which is an 8086 and
  not a Z80. It is a zip of a little over half a megabyte at nasm.us;
  `nasm.exe` is enough.
- **ZEsarUX in `tools/`**, only to run the tests, to extract an adventure from
  its machine with `grab.py` and to time a picture in `regac draw`; and
  **DOSBox-X** on the path for the tests of the PC.

`tools/` is where **every program that is not this project's own** goes, and
it is not in the repository.

Everything is called with `python -m regac` **from the folder of reGAC**.
From another folder it says `No module named regac`; the files it is given
can be anywhere.

Or it is installed as a command, **from its own folder**, and then `regac` on
its own works from anywhere:

    pip install -e .          # or: poetry install

It is installed pointing at the folder and not copied from it, because the
interpreters it builds with are the folders beside it, `z80/` and `x86/`:
that is why it is not on PyPI. A release of reGAC is that folder, zipped.

What the tools say --the errors, the warnings, the help of each command, what
`regac draw` puts under the picture-- comes out in English or in Spanish, in
the language of the system. The variable `REGAC_LANG` chooses one over it:
`REGAC_LANG=es` for Spanish, `REGAC_LANG=en` for English.

---

## 3. In five minutes

There is an example adventure, **El faro de Santa Bárbara** (*the lighthouse
of Santa Bárbara*): five rooms, four objects and one puzzle, commented from top
to bottom to be read as a tutorial. It is in Spanish, like the adventures of
1986 this project started from.

    python -m regac make ejemplo/faro.toml

builds it for the nine machines and leaves them in `ejemplo/salida/`, a folder
for each. Load one in the emulator you have and it is playing. With `--zip
faro.zip` they go into a zip as well, as they are on the disk, to hand out.

And to see it with no emulator at all:

    python -m regac compile ejemplo/faro.gac faro.json
    python runGAC.py faro.json

---

## 4. The two halves

An adventure is **two files**:

- **`faro.gac`** is *what the adventure is*: rooms, objects, words, messages,
  conditions and pictures. It says nothing of what machine it goes to.
- **`faro.toml`** is *where it goes*: what machines, with what loading
  screen, at what size the pictures, how the banks are shared out.

**What is the adventure's goes in the source; what is the machine's goes in
the project.** A source is taken to a new machine without touching it.

The whole project of the lighthouse:

    name   = "faro"
    source = "faro.gac"
    output = "salida"

    [targets.spectrum48]
    [targets.spectrum128]
    [targets.plus3]
    [targets.cpc464]
    [targets.cpc6128]
    [targets.msx]
    [targets.next]
    [targets.pcw]
    [targets.pc]

Each target can carry its own:

    [targets.spectrum128]
    screen = "loading.scr"      # a loading screen

    [targets.pcw]
    scale  = 2                  # the size the pictures are drawn at

All of it is in [`project.md`](project.md).

---

## 5. The work cycle

Write, check, build. The checks are quick and ask for no assembler:

    python -m regac compile  faro.gac faro.json     # is it well written?
    python -m regac check    faro.gac               # does it point at nothing?
    python -m regac checkgfx faro.json -m cpc       # does a picture spill?
    python -m regac text     faro.gac               # what does the text take?
    python -m regac render   faro.json pictures/    # the pictures as PNG
    python -m regac draw     faro.gac 1             # a picture, live
    python -m regac lint     faro.gac               # is anything left over?
    python -m regac map      faro.gac map.svg       # the map
    python -m regac play     faro.gac solution.txt  # can it be won?
    python -m regac make     faro.toml              # build

**`compile`** turns the source into the database and complains about what it
does not understand, saying file, line and column. **`check`** checks that the
database survives a whole round trip -- what was compiled, decompiled and
compiled again, comes out the same -- and that nothing points at a room, an
object or a message that is not there. **`text`** says what the packed text
takes, which is what decides whether an adventure fits in a 464.

`check`, `text`, `lint`, `map`, `play` and `draw` read the source or the
database, either; `-m` says which machine to read a source for when it keeps
lines for some. `decompile`, `render`, `checkgfx` and `build` read only the
database, and given a source they say to compile it first.

**`lint`** looks the other way from `check`: at what is there and nothing
uses. A room no way leads to and no `GOTO` names, an object nothing can pick
up, a word no condition asks for, a message nobody prints, a picture no room
shows, a `/PROC` table no `DO` runs. It does not stop anything being built,
and some of it may be on purpose -- scenery nobody takes -- so these are
notes. A number worked out while the game plays (`MESS ( RAND 3 + 10 )`)
cannot be followed, and rather than say something false, it says so.

**`map`** draws the map as SVG, which any browser opens: the rooms on a grid
by the compass -- NORTH, SOUTH, EAST, WEST and the four between, read in the
vocabulary, in English or in Spanish -- a line where one can go both ways, an
arrow where only one way, and what is not the compass -- UP, IN -- as a curved
arrow with its word. The room the game starts in has a thick border.

**`play`** plays a file of orders, one a line, on the interpreter in Python,
writes what the adventure says, and ends with 0 if the game ends -- and, with
`--expect`, if it said that -- and with 1 if the orders run out with the
adventure still asking. Keeping the solution beside the adventure and playing
it after every change is a test that needs no machine. The lighthouse's is in
`ejemplo/solucion.txt`:

    python -m regac play ejemplo/faro.gac ejemplo/solucion.txt --expect "Fin de la aventura"

To write, **`editors/vscode/`** is a VS Code extension that colours the
source: sections, directives, conditions, drawing orders and the commands of
the text. It is installed by copying the folder into `.vscode/extensions/`, in
the user's folder, and starting VS Code again.

To try it without starting a machine:

    python runGAC.py faro.json          # in the terminal
    python runGAC_pygame.py faro.json   # behind a screen like the Spectrum's

Both play the whole adventure, `SAVE` and `LOAD` included. A machine saves on
its tape or disk and asks nothing; here a file needs a name, so one is asked
for, and what is written is a JSON that can be opened and read. **It is not
the file a machine saves**, nor could it be: the block of the Z80 carries
addresses of its own memory.

---

## 6. The source, block by block

A **UTF-8** text file. The sections start with `/` in the first column. `;`
opens a comment to the end of the line, except inside a text of the
adventure, where everything is literal.

### The texts

The messages, the names of the objects and the descriptions of the rooms are
literal text. Several lines are joined with a space; a backslash at the end
joins them with nothing between. A line of text that starts with `#`, `/`, `;`
or `|`, or that looks like a directive, is written with a `|` in front, which
the compiler takes off.

Inside a text there are commands, with a backslash:

| | |
|---|---|
| `\ink n` | what follows **in this message** is printed in colour n |
| `\\` | a backslash of one's own |

    #14
    The dragon is \ink 2 red \ink 7 and asleep.

The command **eats the spaces that follow it**, so that they do not come out
twice. The colours are the Spectrum's sixteen; every machine reads them its own
way, and the PCW, which has no colour, reads the command and goes on.

**The change lasts to the end of the message** and no longer: the next one
starts in the ink of the adventure again. So there is no need to give the ink
back before the end, and a message cannot colour the description of the room
that comes after it.

And there are **holes**: something only known when it is printed, printed
where it stands.

| | |
|---|---|
| `\ctr n` | what counter n holds |
| `\obj n` | the name of object n |
| `\turns` | the turns played |

    #15
    You have \ctr 0 points after \turns turns, and in your hand \obj 3.

A hole is text: it is part of the word it stands in, so `\obj 3.` is not parted
from its full stop when the line is broken, and **the spaces after it stay**,
unlike with `\ink`. They are good in the messages, in the rooms and in the
names of the objects; a name may hold a counter but not another name, which
could be its own, and that is not built. The number is written as a number,
not as a `.def` name.

### `/CTL` -- the settings

    /CTL
    model    SPECTRUM
    start    5000
    width    32
    ink      4
    punct    "\0" " " "." "," "-" "!" "?" ":"
    sep      "THEN" "AND"
    nothing  "Nothing"

`punct` are the eight word terminators GAC codes in three bits inside every
word of text; the first, the null, marks the end of a string.

`sep` are the words that part a line into two orders, and they are **all**
there are: the interpreter knows none of its own. They are compared as whole
words -- `ANDY` is not `AND` with a tail. Without `sep`, only the marks of
`punct` part orders.

`nothing` is the word for "nothing", which is what `LIST` writes when it finds
no object.

`ink` is **the colour of all the text of the adventure**, one of the
Spectrum's sixteen. Every message starts in it and goes back to it at its end,
so a `\ink` inside a message colours a word and not the rest of the game. If
it is not said, each machine uses its own -- white on the Spectrum, the Next
and the MSX; pen two on the Amstrad -- and the PCW, which has no colour,
ignores it. Nought is not allowed: on all these machines it is the paper, and
text the colour of the paper is not seen.

### `/VOC` -- the vocabulary

A word a line: word, number and kind. Synonyms share a number. The kind is
`verb`, `noun` or `adverb`.

    /VOC
    NORTH   1  verb
    N       1  verb
    KEY     2  noun

### `/MSG` -- the messages

`#n` opens the message, and the text goes on the lines below.

    /MSG
    #14
    The snake bites you and you die.

### `/OBJ` -- the objects

    /OBJ
    #1  weight=1  start=nowhere
    a metal disc

`start` takes the number of a room, `nowhere` (0) or `carried` (255).

### `/LOC` -- the rooms

    /LOC #1  gfx=1
    A wide street of the City.
      /CONN
        NORTH        6
        EAST         2
      /LOCAL
        IF ( VERB 2 ) MESS 63 WAIT END

In `/CONN` the direction is **a verb**, written as its word instead of its
number. `/LOCAL` carries the conditions of that room.

### `/HIGH` and `/LOW` -- the conditions

A condition a line, ended by `END`. All the opcodes are in
[`gac.md`](gac.md).

    /HIGH
    IF ( CTR 126 = 0 ) MESS 1 SET 5 END

What is repeated in several rooms is written once, in a numbered table, and
called with `DO`:

    /LOW
    IF ( VERB LOOK_VERB ) DO DESCRIBE_THE_SEA END

    /PROC #DESCRIBE_THE_SEA
    IF ( AT PATH ) MESS THE_SEA END
    IF ( AT STAIRS ) MESS NOTHING_TO_SEE END

It runs as if it were written where the `DO` is: if there is a `WAIT` in it,
the turn ends there. The detail is in [`gac.md`](gac.md).

GAC **has no precedence**: it evaluates strictly from left to right. That is
why the operand of a prefix operator is not greedy, and `NOT VERB 1 AND NOUN
2` negates only the test of the verb. When the right operand of an infix
operator is itself infix, it goes in brackets.

### `/GFX` -- the pictures

`#n` opens a picture and its orders go below. All the drawing commands are in
[`gac.md`](gac.md).

    /GFX
    #1
      PAPER 5
      LINE 128 159 128 79
      CALL 1000

To draw, **`regac draw`** opens the picture in a window and paints it again
every time the source is saved, so it is written in the editor and looked at
beside it:

    python -m regac draw faro.gac 1 -m cpc

It comes out as that machine shows it -- `spectrum`, `cpc`, `msx`, `pcw`,
`next` or `cga`, which is the PC's -- and `m` goes to the next. The arrows
walk it an order at a time (with shift ten at a time, with control a hundred),
and what the last order laid comes out in magenta: a fill that gets out through
a gap says where. What `CALL` calls is walked inside, where it stands. Below
it says the order before and the order after, and **where the pointer is in
the coordinates of the orders**, `x` from the left and `y` from the bottom,
which is what has to be written. Page Up and Page Down change the picture. If
the source saved has a mistake, it says so and keeps the last good picture.

And **one draws in it**, with the mouse, and what is drawn is written into the
source at once, as one more line of the picture:

| key | what a click does |
|---|---|
| `l`, `r`, `e` | a line, a rectangle or an ellipse: two clicks |
| `p`, `f`, `b`, `s` | a point, `FILL`, `BGFILL` or `SHADE`: one click |
| `v` | move: a point of an order, marked with a small square, is dragged |

A new order goes **after the order the cursor is on**, and not at the end:
with the arrows one goes back and puts a line in before a fill, which is what
decides how far it reaches. Enter lets an order be typed (`INK 3`, `CALL 10`),
Delete takes out the order at the cursor, Ctrl+Z undoes, `g` snaps the clicks
to the corners of the cells of eight, and the right button or Esc let go of
what was being drawn.

It is written as a person would write it: one line in, out or changed, with
the indent of the lines beside it, and the comment at the end of a line kept.
A point dragged writes the numbers of its line again, and **a `.def` name that
was there becomes a number**. The source may be open in the text editor at the
same time. It does not write into a picture that is in another file -- taken in
by `.include`: that one is opened -- nor into one that keeps lines for some
machines with `.if`, which is edited by hand; and what is drawn belongs to the
picture being looked at, even when the cursor is inside another that it calls.

To **trace**, an image over the picture, half seen through:

    python -m regac draw faro.gac 1 --trace sketch.png
    python -m regac draw faro.gac 1 --trace sketches/

A file goes over every picture; a folder, the one named as the number of the
picture (`12.png`, `12.jpg`), which changes by itself going from one picture to
another. The image is made as big as it fits **without being put out of
shape**, and centred. `t` hides it and shows it, and `+` and `-` let more or
less of it be seen.

While drawing, the window **warns**:

- of a fill that **gets out** through a gap or a passage one pixel high, which
  in GAC comes out as a ray of one row as far as the next thing that stops it;
- of a fill that **fills nothing**, because its seed falls on a pixel already
  set;
- and of **how many bytes** the picture takes, and all of them together.

`n` takes the cursor to the next order there is something to say about. And
`c` **measures how long the picture takes to draw** on the machine being
looked at -- the Spectrum, the CPC or the MSX -- with the interpreter itself in
the emulator, in seconds of the real machine, against the budget of four or
five: it takes as long as the emulator takes to come up, some fifteen seconds,
and it needs `tools/`, like the tests.

### `/FONT` -- the lettering

Whole, with `file`, or a letter at a time.

### `/SOUND` -- the noises

One a line, in the order `SOUND` counts them **from one**:

    /SOUND
    ; pitch  steps  step  out of
       200    150     -1          ; taken
       250    100      0  both    ; a door
        30    110      2  noise   ; a fall

The **pitch** is how long half a wave lasts -- bigger, a lower note -- the
**steps** are how many times it is repeated and the **step** what is added to
the pitch at each.

The fourth column is **what it comes out of**, and it may be left blank: `tone`
is a note, `noise` the hiss the chip makes with no note in it, and `both` the
two together. A door, a fall or an alarm are not notes, and a chip has what it
takes to say so. **The Spectrum 48 has not**, and there the word is read and
the tone played -- the nearest thing there is -- so using it leaves no machine
out: it only sounds better where there is something to sound it with.

**They sound through the sound chip on the machines that have one** -- 128,
+3, the two Amstrads, MSX and Next -- and through the speaker of one bit on
the Spectrum 48 and the PC, which have none. Two engines and **one table**: a
pitch is half a wave of the speaker and half of that as the period of the
chip, so `SOUND 2` lasts the same and sounds the same everywhere -- on the PC
counted on the system's clock and not on the processor, which may run at any
speed. Where there is a chip the note is cleaner and nothing is touched that
shares a port with the speaker -- the border on the Spectrum, the tape motor
and the caps lock light on the MSX.

An adventure that says nothing here keeps the five the interpreter comes with,
and the PCW, which has nothing to sound with, reads the order and goes on.

---

## 7. Three things that save work

### Names for the numbers

    .def DOOR_OPEN   5
    .def WELCOME    14

From there on the name is good **wherever the number would be**: in a
condition, in a way out, as the number of a message or a room (`#WELCOME`,
`/LOC #STREET`), in `start`, in the attributes of an object and in the
arguments of a drawing order. The value may be decimal, hexadecimal (`0x0A`)
or another name already given.

### Taking in files

    .include "common.gac"

To share between the two parts of an adventure, or between two adventures,
what does not change. The path is counted from the file that includes, and a
mistake inside an included file says **that** file and its own line.

### Lines only some machines have

With `.if`, `.else` and `.end` part of the source exists only for the targets
named, which is how what does not fit the same everywhere is adjusted.

---

## 8. Starting from an adventure that already exists

    python deGAC.py game.sna game.json        # from a snapshot
    python disk.py  game.dsk                  # from an Amstrad disk
    python grab.py  ...                       # loading it on its machine

**`deGAC.py`** recognises by itself a snapshot of a Spectrum, one of CPCEMU
and one of VICE; a plain image of memory has to be told what machine it comes
from with `-m`. From there to readable source:

    python -m regac decompile game.json game.gac

**`disk.py`** reads a file off an Amstrad disk image, or a whole adventure off
one laid out so that it could not be copied. **`grab.py`** loads a medium on
its machine and writes out what it left in memory.

An adventure off an **Amstrad** does not keep its lettering: the Amstrad's GAC
wrote with the firmware's, which is in the machine's ROM and not ours.
`deGAC.py` gives it **Modern DOS 8x8**, the CGA lettering by Jayvee Enaguas,
which is in the public domain (CC0), and says so. The same for one off a
Spectrum that wrote with the ROM's letters. Without that, they would print
blanks on every machine.

---

## 9. The machines, and what each has of its own

- **Spectrum 48 and 128.** The 128 shares the text and the pictures out into
  pages of their own, and so adventures fit in it that do not fit in the 48;
  and it has a sound chip, so the noises and the key click come out of it. The
  48 is the one machine that makes them on the speaker.
- **Spectrum +3.** Disk, with the loader in the machine's menu.
- **Amstrad CPC 464.** The tightest: no banks, and the database in one
  stretch. If an adventure does not fit the usual way, `regac` **builds it the
  other way round by itself** -- the interpreter under `$4000` and the database
  above -- and says so while building. It is also the only one where the table
  of noises travels only if the adventure asks for one: a hundred and four
  bytes on the machine that counts them one by one. The key click always
  travels.
- **Amstrad CPC 6128.** Disk and banks: the big ones fit here.
- **Amstrad PCW.** A disk that starts by itself, without CP/M. Monochrome, 64
  columns.
- **MSX.** Tape, and the whole machine in RAM.
- **Spectrum Next.** `.nex`, in layer 2 and with a colour to every pixel.
  `SAVE` and `LOAD` use a file on the card, beside the `.nex`, with the name of
  the project and `.SAV`: `faro.nex` saves in `FARO.SAV`.
- **PC with a CGA.** A DOS `.EXE` with the name of the project, which runs on
  any PC from an XT at 4.77 MHz with a CGA or something that does its mode of
  320 by 200. Four colours **chosen for every picture** among those the CGA
  allows; the text, as on the Amstrad, forty columns under the picture. An
  adventure off an Amstrad is drawn with the Amstrad's rules and flashes what
  the CGA lets it: the background, or the whole trio when nothing else moves.
  `SAVE` and `LOAD` use a file beside the program, with its name and `.SAV`; at
  the end of the game, a key goes back to DOS. The key pressed is the one of
  the layout DOS has (`KEYB SP` and the rest).

The **width of the screen** is not the same everywhere -- 32 columns on the
Spectrum, the MSX and the Next; 40 on the Amstrad and the PC; 64 on the PCW --
and that changes where lines break. A text that looks right on one may come
out differently on another.

---

## 10. The two licences, which are on purpose

The tools -- everything that is Python -- are under the **GPL v3**. The
interpreters in [`z80/`](../../z80) and [`x86/`](../../x86), which are what
ends up inside somebody else's adventure, are under the **MIT licence**: an
adventure built with this **carries no obligation** from the tools that built
it.

---

## Where next

| if you are looking for | see |
|---|---|
| the whole language: opcodes, drawing, the turn, the parser | [`gac.md`](gac.md) |
| the source format, section by section | [`source-format.md`](source-format.md) |
| the project file | [`project.md`](project.md) |
| an adventure written to be read | [`../../ejemplo/faro.gac`](../../ejemplo/faro.gac) |
