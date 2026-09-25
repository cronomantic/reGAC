# The reGAC source format (`.gac`)

*[Leer en español](../formato-fuente.md)*

The text format of the project. It is where an adventure stops being a binary
dump and becomes something that can be edited, kept under version control, and
compiled again for any of the target machines.

    SNA/VSF  --deGAC-->  JSON  --regac decompile-->  .gac source
    .gac source  --regac compile-->  database (JSON, or the machines' binary)

## Principles

1. **Compatible with the original GAC.** The conditions are written with the
   exact syntax of Incentive's manual: `IF ( VERB 7 AND NOUN 5 ) MESS 14 HOLD
   200 EXIT END`. Whoever knows GAC learns nothing new.
2. **An exact round trip.** Decompiling and compiling again has to give back
   the original database. It is the acceptance test of the compiler and the
   safety net of everything else.
3. **Extensible without breaking.** Every new feature comes in as something
   optional. A source without the new things compiles as classic GAC.
4. **What is the adventure's goes in the source; what is the machine's goes in
   the project file.** Compression, memory banks and targets do not dirty the
   text of the adventure. The project file is in [`project.md`](project.md).

## The tool

    python -m regac decompile game.json game.gac
    python -m regac compile   game.gac  game.json
    python -m regac check     game.json      ; checks the round trip

## The overall shape

A UTF-8 text file. The sections start with `/` in the first column. `;` starts
a comment to the end of the line, except inside a block of the adventure's
text, where everything is literal. Blank lines are ignored outside the blocks
of text.

### Blocks of text

The messages, the names of the objects and the descriptions of the rooms are
literal text. If they take several lines, the lines are joined with a space;
a backslash at the end of a line joins it to the next with nothing between. A
line of text that starts with `#`, `/`, `;` or `|`, or that is a directive --
`.if`, `.else`, `.end`, `.def`, `.include` -- is written with a `|` in front,
which the compiler takes off.

Inside the text there are **commands**, which start with a backslash:

| Command | What it does |
|---|---|
| `\ink n` | what follows **in this message** is printed in colour n |
| `\ctr n` | what counter n holds, from 0 to 127 |
| `\obj n` | the name of object n, from 1 to 255 |
| `\turns` | the turns played, which take counters 126 and 127 |
| `\\` | a backslash of one's own |

    #14
    The dragon is \ink 2 red \ink 7 and asleep.

The command **eats the spaces that follow it**, as in any other language with
commands inside the text, so that `red \ink 2 and black` comes out with one
space between the words and not two.

The colours are the Spectrum's sixteen, the same as in the pictures: from 8 up
it is the same colour bright. Every machine reads them its own way -- the MSX
takes the nearest of its own, the Amstrad takes the number as one of its four
pens, and the PCW, which has no colour, reads the command and goes on -- which
is exactly what they do already with the colours of a picture.

**The change lasts to the end of the message.** Every message starts in the
usual ink, so there is no need to give it back before the end, and one that
leaves it changed does not colour what comes after. What is given up is
painting across several messages, which costs a `\ink` in the second.

The other three are **holes**, and they are not GAC's: they are filled when
they are printed. A hole is text and part of the word it stands in -- `\obj 3.`
is not parted from its full stop when the line is broken -- so it does not eat
the spaces after it. They ride, like `\ink`, behind code 1, with a letter the
colours do not use (`T`, `C` and `O`) and the number in two characters of four
bits, so that they are packed like the rest of the text. They are good in
every text; the name of an object may carry `\ctr` and `\turns` but not
`\obj`, which could name itself, and the build refuses it. The number is
written in digits: a `.def` name is not good inside the text. And a digit
straight after the number would be read as part of it: `\ctr 5` followed by
`0 times` cannot be written touching.

| Section  | What it holds                                               |
|----------|-------------------------------------------------------------|
| `/CTL`   | The settings of the adventure                               |
| `/VOC`   | Vocabulary: verbs, nouns, adverbs                           |
| `/MSG`   | Messages                                                    |
| `/OBJ`   | Objects                                                     |
| `/LOC`   | One to each room, with its ways out and local conditions    |
| `/HIGH`  | High priority conditions                                    |
| `/LOW`   | Low priority conditions                                     |
| `/PROC`  | A numbered table of conditions, run by `DO`                 |
| `/GFX`   | Vector pictures                                             |
| `/FONT`  | The lettering                                               |
| `/SOUND` | The noises it asks for                                      |

### `/CTL`

    /CTL
    model    SPECTRUM
    start    5000
    width    32
    ink      4
    punct    "\0" " " "." "," "-" "!" "?" ":"
    sep      "THEN" "AND"
    nothing  "Nothing"

`punct` is the table of eight sentence terminators GAC codes in three bits
inside every word of text. The first, the null, marks the end of a string.

`sep` are the words that part a line into two orders, and they are **all**
there are: the interpreter knows none of its own. The original did know two,
`THEN` and `AND`, built into its interpreter; `deGAC` writes them here when it
decompiles, so that an original compiled again parts the orders where it
always did, and a new adventure says its own and nothing else:

    sep      "y" "luego"

They are compared as whole words -- `ANDY` is not `AND` with a tail -- and
kept without marks and in capitals, which is how they come from the keyboards
of these machines. Without `sep`, only the marks of `punct` part orders.

`ink` is the colour of all the text of the adventure, one of the Spectrum's
sixteen. Every message starts in it and goes back to it at its end, so it is
the place where what `\ink` says inside a sentence is said once. If it is not
said, every machine uses its own. **Nought is not allowed**, and that is what
let the setting be added without breaking anything: on all these machines
nought is the paper, so it is left free to mean "nothing was said", which is
what a database that does not carry it holds.

### `/VOC`

A word a line: word, number and kind. Synonyms share a number. The kind is
`verb`, `noun` or `adverb`.

    NORTH                      1  verb
    N                          1  verb

### `/MSG`

`#n` opens the message; the text goes on the lines below, literal.

    #14
    The snake bites you and you die.

### `/OBJ`

    #1  weight=1  start=nowhere
    a metal disc

`start` takes the number of a room, `nowhere` (0) or `carried` (255).

### `/LOC`

    /LOC #1  gfx=1
    A wide street of the City.
      /CONN
        NORTH        6
        EAST         2
      /LOCAL
        IF ( VERB 2 ) MESS 63 WAIT END

In `/CONN` the direction is a verb, as in GAC, and it is written as the word
instead of the number.

### `/SOUND`

A noise a line, in the order `SOUND` counts them from one:

    /SOUND
    ; pitch  steps  step
       200    150     -1    ; taken
        60    150      1    ; refused
       250    100      0    ; a door

The **pitch** is how long half a wave lasts -- a bigger one is a lower note --
the **steps** are how many times it is repeated, and the **step** is what is
added to the pitch at each: a step that takes the pitch down takes the note
up. The three are numbers like any other, so `.def` names are good.

And an optional fourth column, which is **what it comes out of**: `tone`,
`noise` or `both`. A sound chip has a tone generator and a noise generator and
can use either or both together; a speaker of one bit has neither, and there
the word is read and the tone played. A line without it is a tone, so a source
written before this existed is good as it is.

**The sound chip makes them on the machines that have one** -- 128, +3, the
two Amstrads, MSX and Next -- and the speaker of one bit on the Spectrum 48 and
the PC, which have none. One table and two engines: a pitch is half a wave of
the speaker and half of that as the period of the chip, so the same number
lasts the same and sounds the same everywhere -- on the PC, counted on the
system's clock and not on the processor. The PCW has nothing to sound with,
and there `SOUND` does nothing. An adventure that says nothing here keeps the
five the interpreter comes with.

### `/HIGH`, `/LOW`, `/LOCAL`

A condition a line, ended by `END`. The syntax is the manual's. The bytecode
is a postfix stack machine, but the source is written in the original prefix
and infix form and the compiler reorders it. The opcodes, their shape and the
kind of their operands are in [`regac/opcodes.py`](../../regac/opcodes.py),
which is the one place the language is written down.

GAC has no operator precedence: it evaluates strictly from left to right.
That is why the operand of a prefix operator is not greedy, and `NOT VERB 1
AND NOUN 2` negates only the test of the verb. When the right operand of an
infix operator is itself an infix expression, it goes in brackets.

Some original adventures leave values on the stack that they never use. The
decompiler writes them as a number on its own where they were pushed, so as
not to change the code when it is compiled again.

### `/PROC`

    /PROC #7
    IF ( AT 3 ) MESS 20 END
    IF ( AT 4 ) MESS 21 WAIT END

A numbered table of conditions, written like `/HIGH` or `/LOW`, which runs
wherever a condition says `DO 7`. The number may be a `.def` name, and it goes
from 0 to 32767. How it behaves is in [`gac.md`](gac.md), "Tables of one's
own". In the database it goes in the same list as the conditions of each
room, with its number and the top bit set, which no room has: an adventure
without `/PROC` comes out exactly as before.

### `/GFX`

    #1
      PAPER 5
      LINE 128 159 128 79
      CALL 1000

A picture of an adventure off an Amstrad also carries its four inks in the
header, as the firmware's numbers, from 0 to 26: one pen to each comma, and a
pen that flashes as its two colours with a stroke between them, in the order
the picture keeps them.

    #9 inks=0,13,17/0,20

They are the ones the original puts up when it draws the picture of a room --
the border in the first -- and the ones a picture called with `CALL` does not
put up. A picture without `inks=` in an adventure that carries them gets the
firmware's at start: 1, 24, 20 and 6.

### `/FONT`

The lettering of the adventure, whole or a letter at a time.

**Whole**: `file` says where it is, relative to the source, and what it is is
worked out by looking at it.

    /FONT file="letters.bin"
    /FONT file="sheet.png" layout=latin1
    /FONT file="charset.64c" order=c64

What it recognises:

| | |
|---|---|
| a plain dump | eight bytes a character; 768 are the ninety six from the space -- the shape a Spectrum's font comes in -- 1024 and 2048 are a hundred and twenty eight and two hundred and fifty six from nought |
| with a load address | two bytes in front, which is how a C64 charset travels |
| with an AMSDOS or +3DOS header | the 128 bytes those systems put on everything |
| a console font | both PSF headers, taking the glyphs and not the table of meanings behind them |
| PNG | the letters in a grid of cells of eight by eight, read as a page is read; whatever is darker than half is ink, so it does not matter what two colours it is drawn in |
| written as source | a C header or an assembly listing -- Z80, 6502, x86, 68000 -- which is how the same fonts are published for a program to use |
| BDF | the standard format for bitmap fonts, and the only one that says by itself which character every glyph is |
| VDU 23 | the string of orders that redefines a character on a BBC Micro: the 23, the character and its eight rows |
| BASIC with `SYMBOL` | the same on an Amstrad CPC, which is how its file comes in these collections |
| RS-DOS | the wrapping of five bytes in front and five behind of a CoCo |

From a listing it takes what is on the lines with a bytes directive -- `db`,
`defb`, `.byte`, `dc.b` -- and, if there are none, what is between braces;
between the two it leaves out the size of `font[768]` and the address of an
`org`. The comments are taken off **before** the braces are looked for, and
it is not a detail: these listings put in a comment the letter each row
draws, so the line with the opening brace has an opening brace.

**Tried on a real font.** From a ZIP of
[ZX Origins](https://damieng.com/typography/zx-origins/) these come in, all
giving the same letters: the Spectrum's `.ch8`, the Atari's `.fnt` with
`order=atascii`, the C64's `.64c`, the `.psf`, the five listings of `Source`,
the `.bbc`, the Amstrad's `.bas`, the `.bdf`, the GameBoy's sheet with
`first=32` and even the sample image with `layout=ascii`. Left out are the
C64's `.bin` -- two fonts in one file, and `first=` has to say which -- the
CoCo's `.CHR`, whose order is not known, and the `.fzx`, which is
proportional.

**Every letter is known by its cell**, and that is what `layout` is for: it
says at once where the sheet starts and how many cells it has:

| `layout` | cells |
|---|---|
| `ascii` | 96, from the space to the copyright sign |
| `latin1` | 256, the whole of Latin-1 |
| `latin1-high` | 96, only the top half of Latin-1, which is where the accents are |

**Draw the sheet in Latin-1.** Every letter this prints is there, in the place
any font editor puts it, so the artist never has to hear about reGAC's codes:
the `á` drawn where Latin-1 keeps the `á` falls where it should. A sheet of
Latin-1 is 16 by 16 cells, and the blank cells are no letter: they are
composed, or left as they were.

Knowing how many cells there are has a second advantage, and it is what makes
this work in earnest: **a sheet drawn large reads the same**. Nobody draws at
eight pixels a letter; if the sheet is at twice or three times the size, the
number of cells says which of the two it is, instead of reading it as four or
nine times as many letters.

`first` says what character the first cell is when there is no `layout`, and
`order` in what order they are, for the machines that do not use ASCII's:
`c64` keeps `@ABC...` at nought and `atascii` puts the punctuation in front.
Without `order`, as it is.

**A letter at a time**: eight bytes in hexadecimal to a character, with the
glyph as a comment. They win over the file, so a letter can be changed without
drawing the rest again, and blank characters are left out. A character is
named by its number or by itself:

    /FONT chars=128
    #65    00 3C 42 42 7E 42 42 00   ; A
    #"Ñ"   18 00 7E 63 63 63 63 00

The table grows by itself as far as the highest character drawn, so to put in
an Ñ of one's own nothing else has to be declared. And what the author draws
is used as it is: nothing is composed over a glyph that was drawn.

## Latin characters

The source is UTF-8 and whatever is written in Spanish can be written in it:
«La señora Muñoz te miró con desdén», «¿Qué año es?». Nothing has to be
declared.

How it works, which is what makes that so: **the character set is fixed and
the same in every adventure**. Below the space go the letters ASCII has not
-- the accented ones, the ñ, the ç, the opening marks -- and from 32 to 127
goes ASCII as it is, so the code of an ordinary letter is its own ASCII. From
128 up is the compressor's, always. An ñ costs what an n costs and takes
nothing from anybody. This is where the original is left behind: it packed the
characters in seven bits and used the eighth to mark the end of a word, and
there was no room for a single accent.

**The glyphs are not drawn by hand.** An accented letter is the adventure's
own letter with a mark on it, so that it looks like the lettering it is in;
all that is kept is the five marks. Unicode says which letter and which mark
-- NFD parts the á into a and accent, the ñ into n and tilde -- and where the
mark fits comes from the letter: a small letter takes rows two to six and has
two to spare above, a capital takes rows nought to six and comes down a row,
since the bottom one is always free. The ¿ and the ¡ are the ? and the ! upside
down, which is exactly what they are. It is in
[`regac/glyphs.py`](../../regac/glyphs.py).

**The vocabulary loses its marks.** No keyboard of these machines has a key
for an accent, so a vocabulary that said ARAÑA could be typed by nobody: the
binary keeps ARANA, and the player types ARANA. Only the words the parser
compares; the text keeps all its marks, because the text is printed and not
typed. If two words become the same one -- PEÑA and PENA -- the build says so
instead of letting the second never be reached.

What is not in the table cannot be used, and the build says so, with the
character in hand, instead of printing a blank. The whole of Spanish fits, the
accented small letters of Catalan, Portuguese and Italian, and the marks.

The `charset` directive is still accepted so that sources written before
compile, and today it chooses nothing; the day an alphabet is needed that does
not fit -- French, for one -- it will be what chooses which thirty go below the
space.

## Compression of the text

Always. It is nobody's decision: the text is compressed by pairs -- the
commonest pair of codes is replaced by a spare code, over and over -- and the
table is worked out, never written by hand. In MegaCorp the text comes down to
46% of what it took. Unpacking is a table lookup and a small stack, and every
message unpacks on its own, without touching the ones before, which is what
the interpreter needs to print message 137 and nothing else. It is in
[`regac/text.py`](../../regac/text.py).

## What only some machines have

An adventure is one source and nine machines, and now and then they do not
all want the same. A Spectrum 48K may have to go without what fits in the
others, the Amstrad's pens are not the Spectrum's colours, and a machine
without a sound chip has no need of the line that starts a tune. For that, the
source can **keep lines back**:

    #14
    The switch clicks    .if cpc msx
     and that is all.
    .else
     and the screen flickers.
    .end

It is worked out **when the source is read**, not when the game is played:
what a machine is not to have never reaches its database, which is the whole
point on the machines where room is what runs out. It works anywhere -- a whole
section, an entry, a line of a table of conditions, a word of the vocabulary
-- because it works on lines before anything else looks at them, and it can be
nested.

The machine can be named, and the family it belongs to:

| family | machines |
|---|---|
| `spectrum` | `spectrum48`, `spectrum128`, `plus3` |
| `amstrad` | `cpc`, `pcw` |
| `msx` | `msx`, `msx2` |

and on their own are `next`, `pc` and `sam`. A name that does not exist is a
mistake and is said: a typo that quietly takes half an adventure with it is
the worst thing that could happen here. The same for a `.if` never ended, an
`.else` on its own or a `.if` with no machines.

A source with conditionals **has to be read for a machine**: `regac compile
game.gac game.json -m cpc`. `regac make` does it by itself, once for every
machine it builds. A source without conditionals is the same for everybody and
nothing has to be said.

The lines kept back are not taken out: they are emptied, so that any mistake
further on still counts the lines as the author wrote them. And an empty line
inside a block of text is not a space -- a line with a space in it is, which
one of the eight adventures has.

## When something is wrong

An adventure is thousands of lines and whoever writes it is not whoever wrote
the compiler, so a mistake says four things: which file, which line, the line
as it is in the file, and a finger under the word. And when the word is
*nearly* right -- which is what always happens -- what was meant:

    game.gac:147: unknown word 'MESSS' -- did you mean MESS?
        IF ( VERB 7 ) MESSS 14 END
                      ^

The language is sixty eight words, so guessing the one it was comes nearly
free and saves the search. If the word looks like none, nothing is guessed:
a bad suggestion sends one looking where it is not.

The same with the sections (`/MSGG`), the kinds of the vocabulary (`verbo`),
the drawing orders (`LINEA`) and the machines of a `.if` (`cpcc`). And the
number of the line is the file's even when what fails is read all at once --
a picture is read whole, and still the mistake says the line of the order
that is wrong.

## Checking an adventure

    python -m regac check game.json

It says two different things. One is the tool's: decompiled and compiled
again, does it come out the same? The other is the adventure's: **does every
number that points at something point at something that is there?** A `MESS
99` compiles just as well whether there is a message 99 or not, and what the
player sees is a blank, a room closed or silence, with nothing to say why.

Everything that points is looked at: messages, rooms, objects, counters, words
of the vocabulary, pictures -- including a picture that calls another --
where one goes out of each place, where each object starts, the noises the
adventure says it has, and the tables `DO` runs. What cannot be known is not
said: `MESS ( CTR 3 )` changes every game and there is nothing to check there.
What is doubtful comes out as a warning; what cannot be anything but a fault,
as a fault.

The messages the interpreter says by itself are looked at too: without 240 it
has nothing to ask for an order with, and neither the compiler nor the
machine says so.

That is what found a fault of 1987: **Los pájaros de Bangkok** says `MESS 130`
in a room of its first part, and that message was never written.

And the other way round, what is there that nothing uses -- a room nothing
leads to, an object nothing picks up, a message nobody prints -- is what
`regac lint` says.

## Names for the numbers

    .def DOOR_OPEN   5
    .def WELCOME    14
    .def STREET      7

And from there on the name is good **wherever the number would be**: in a
condition (`IF ( SET? DOOR_OPEN ) MESS WELCOME END`), in a way out, as the
number of a message or a room (`#WELCOME`, `/LOC #STREET`), in `start`, in the
attributes of an object and in the arguments of a drawing order. A source
written like that says what it means instead of what it counts, and what
reaches the machine is still the number.

The value may be decimal, hexadecimal (`0x0A`) or **another name already
given**. The name is letters, digits and underscores, not starting with a
digit, and it may not be a word of the language -- `.def MESS 5` is a mistake,
and it is said. A `.def` inside a `.if` exists only for the machines of that
`.if`, which is how one name can be three on one machine and six on another.

The decompiler writes numbers: the JSON does not keep the names, which are
the source's and not the adventure's.

## Taking in files

    .include "common.gac"

To share between the two parts of an adventure -- or between two adventures --
what does not change: the names, the vocabulary, the low priority conditions.
It is what GAC did with its quick start file `QS.ADV`.

The path is counted from the file that includes. A file can include another,
up to sixteen deep, and a file that includes itself is stopped dead and said.
**A mistake inside an included file says that file and its own line**, not a
line of the one that brought it in:

    common.gac:2: there is no word type called 'verbo' -- did you mean verb?
        NORTH   1  verbo
                   ^
