# The GAC language: a complete reference

*[Leer en español](../gac.md)*

The **Graphic Adventure Creator** was published by Incentive in 1986. Its
manual explained how an adventure was typed into the machine; this explains
**the language**, all of it, to write one today.

This page stands on its own. Neither the original manual nor any other
document of `doc/` is needed: the others are development diaries -- what was
measured, in what order and why -- and they are not reference material.

Everything said here is either implemented in the interpreters of this
project or **measured on the interpreter of 1986**, running, on the real
adventures.

---

## 1. The pieces

An adventure is seven things and no more:

| | |
|---|---|
| **rooms** | description, ways out and picture |
| **objects** | weight and the room they start in |
| **vocabulary** | verbs, nouns, adverbs and pronouns, every word with its number |
| **messages** | the texts that are not descriptions |
| **markers** | 256 yes-or-no flags |
| **counters** | 128 numbers of one byte |
| **conditions** | what makes things happen |

There are no named variables, no functions, no loops. An adventure is a list
of conditions looked at in a fixed order, and that order is the first thing
to understand.

---

## 2. A turn, from start to end

There are **three tables of conditions**, and they are looked at like this:

```
  ┌─ every turn, before anything ──────────────┐
  │  1. the HIGH priority table                │
  └────────────────────────────────────────────┘
                     │
            the turn is counted
                     │
  ┌─ an order is asked for and one is taken ───┐
  │  2. does it name a way out of this room?   │
  │     if so: the player goes, and the turn   │
  │     ENDS                                   │
  │  3. the LOCAL table of this room           │
  │  4. the LOW priority table                 │
  └────────────────────────────────────────────┘
                     │
      if nothing took it: "you can't do that"
               or "pardon?"
```

Four things in there are subtler than they look, and all four are measured on
the original:

**The turn is counted after the high table, not before.** MegaCorp sets its
whole game up in a condition guarded by "the turn counter is still nought";
counting first, that condition never runs and the adventure kills the player
on the first move.

**An order that names a way out ends the turn there.** `NORTH` in a room with
a way north goes, and **neither the local table nor the low one is looked
at**.

**The local table goes between the two**, and if it takes the order the low
one is not looked at.

**A line can carry several orders**, parted by the characters and the words
the adventure declares. They are taken one at a time, each with its own whole
pass through the tables.

---

## 3. How a condition is written

A condition is a question and what is done if the answer is yes:

    IF ( VERB 7 AND NOUN 2 ) GET 2 MESS 14 WAIT END

Inside it is a stack: the values are pushed, the opcodes take them and some
leave a result. Writing it, that is not noticed, because the operands are put
where they read best: `VERB 7` in front, `2 < 5` in the middle.

Between `IF (` and `)` goes the question; from the `)` to the `END`, what is
done. A condition without `IF` is always done.

**The brackets do not group.** `AND`, `OR`, `XOR` and `NOT` take what is on
the stack in the order it was written. With questions one after another,
write them in the order they are to be worked out.

---

## 4. The opcodes, all of them

Sixty eight. Grouped by what they do, with what they take and what they
leave.

### The shape of a line

| | |
|---|---|
| `IF ( … )` | starts the question; what follows the `)` is done if it came out yes |
| `END` | ends the condition |

### Logic

| | |
|---|---|
| `a AND b` | both |
| `a OR b` | either |
| `a XOR b` | one and not the other |
| `NOT a` | the opposite |

### Where the player is and what is there

| | |
|---|---|
| `AT n` | is the player in room n? |
| `ROOM` | leaves the number of the room the player is in |
| `HERE n` | is object n here, on the floor? |
| `CARR n` | is it carried? |
| `AVAI n` | is it carried **or** here? |
| `n IN m` | is object n in room m? |
| `WEIG n` | leaves the weight of object n |
| `WITH` | leaves "what is carried", to hand to `LIST` |
| `CONN v` | is there a way out of here by verb v? Leaves the room it goes to, or nothing |

### What was typed

| | |
|---|---|
| `VERB v` | is the verb of the order v? |
| `NOUN n` | is **either** of the two nouns n? |
| `ADVE a` | is the adverb a? |
| `VBNO` | leaves the number of the verb typed |
| `NO1`, `NO2` | leave the first and the second noun |

`NOUN` answers for both nouns and not only for the first: `COGE DISCO AGUJA`
(*take disc needle*) answers to `NOUN` of the needle. Measured on the
original.

### Markers

| | |
|---|---|
| `SET f` | set marker f |
| `RESE f` | clear it |
| `SET? f` | is it set? |
| `RES? f` | is it clear? |

### Counters and numbers

| | |
|---|---|
| `n CSET c` | set counter c to n |
| `CTR c` | leaves what it holds |
| `INCR c`, `DECR c` | up or down one |
| `n EQU? c` | does counter c hold n? |
| `TURN` | leaves the number of the turn |
| `a + b`, `a - b` | add and subtract |
| `a < b`, `a > b`, `a = b` | comparisons |
| `RAND n` | leaves a number at random from 0 to n-1 |

`<` and `>` look at **the sign of the subtraction**, which is what the
original does: a difference that has gone below nought counts as less.

### Moving and describing

| | |
|---|---|
| `GOTO n` | takes the player to room n **and describes it there and then** |
| `DESC n` | describes room n |
| `LOOK` | describes where the player is |

`GOTO` describes at once, not on the next turn: `GOTO 20` followed by a
message prints room 20 first. And a room described by `LOOK` in the high
table is not described again: that is how an adventure opens in the room it
wants.

### Objects

| | |
|---|---|
| `GET n` | take object n |
| `DROP n` | drop it |
| `n SWAP m` | each goes where the other was |
| `n TO m` | put object n in room m |
| `BRIN n` | bring it to where the player is |
| `FIND n` | go to where the object is, describing on arrival |
| `OBJ n` | writes the name of object n |
| `LIST n` | writes what is in room n, or the word for "nothing" |
| `STRE n` | sets to n what the player can carry; it starts at 250 |

`GET` looks in the hand first, then around, and last at the weight, and **any
of the three refusals ends the turn**: the conditions below it in the same
table are not looked at. `BRIN` says 245 if it is already carried and 252 if it
is nowhere, and it ends the turn as well. `FIND` says nothing of what is
already carried, and of what is nowhere it says 252.

### Text and screen

| | |
|---|---|
| `MESS n` | writes message n |
| `PRIN n` | writes the number n |
| `LF` | goes to a new line |
| `TEXT` | the text takes the whole screen and pictures are no longer drawn |
| `PICT` | lets the pictures be drawn again |

`TEXT` clears nothing and moves no cursor: all it changes is how far the
scrolling reaches. `PICT` redraws nothing either; the window goes back to its
place **when the next picture is drawn**. Measured on the original.

### Sound

| | |
|---|---|
| `SOUND n` | makes noise n |
| `QUIET` | silence |

These two are additions of this project, not GAC's. The sound chip makes them
where there is one -- 128, +3, Amstrad, MSX and Next -- and the speaker of one
bit on the Spectrum 48 and the PC; the engines read the same table and last
the same. A machine with nothing to sound with -- the PCW -- reads them and
does nothing, so that **the same adventure is good for every machine**.

Every noise also says what it comes out of -- tone, noise or both -- and that
is the one thing that does not sound the same everywhere: where there is a
chip, a door or a fall come out of the noise generator; on the 48, which has
none, they come out as the swept tone the rest of the line describes. The
adventure does not change.

### The end of the turn and of the game

| | |
|---|---|
| `WAIT` | ends the turn here |
| `OKAY` | says "okay" and ends the turn |
| `EXIT` | the game is over |
| `QUIT` | asks first, and it is over if the answer is yes |
| `HOLD n` | waits n fiftieths of a second, or until a key is pressed |
| `SAVE`, `LOAD` | save and restore the game |

`WAIT` and `OKAY` end the table as well: what comes below **in the same
table** is not even looked at. `QUIT` reads one key: `N` calls it off and
anything else -- a letter, a space, the enter key -- goes ahead.

### Tables of one's own

| | |
|---|---|
| `DO n` | runs the table `/PROC n` as if it were written here |

An addition of this project, not GAC's: what is repeated in several rooms is
written once, in a block `/PROC #n`, and called with `DO n`.

- **It is as if it were written where it stands.** What comes out true in it
  counts as the order having been understood, and what ends the turn in it --
  `WAIT`, `OKAY`, `EXIT`, a refusal of `GET` -- ends it outside too: the table
  that ran `DO` goes no further.
- What the table outside had on the stack is still there when it comes back.
- A table can call another, or itself, **up to eight deep**, as a picture can
  call another; beyond that, `DO` does nothing. Nor does a `DO` of a table
  that does not exist, and `regac check` says so.
- It travels only in the interpreter of an adventure that uses it, like the
  noises.

### Close ups

| | |
|---|---|
| `DRAW n` | draws picture `n` where the room's goes |

An addition of this project, not GAC's: a picture in the middle of a turn,
the close up of what is examined, say.

- **It is drawn as a room's is**: it takes its rows back from the text, and
  with a `TEXT` in force it draws nothing. `DRAW 0` is what a room with no
  picture does: the text takes the whole screen, and nothing is wiped.
- **Nothing is kept.** The room's picture comes back when the room is
  described again -- going out by a way out, with `GOTO`, `LOOK` or `DESC` --
  and costs its drawing, not a copy of the screen. To bring it back without
  saying the text again, `DRAW` the room's picture, the next turn with a flag,
  say.
- **It draws in the dark as well**: it is not the room being described.
- A `DRAW` of a picture that does not exist wipes the picture's window, as a
  room pointing at it would, and `regac check` says so.
- It travels only in the interpreter of an adventure that uses it: 28 bytes
  on the Z80.

### Unused

`NOP` and `NOP29` do nothing. They are here because the original had them.

And one more that is never written: `ENDTABLE` is the mark the compiler puts
at the end of a table. With it, sixty nine.

---

## 5. Markers and counters that are not yours

This is the one that is hardest to find out alone. **Some markers and
counters belong to the interpreter**, and writing over them breaks things
that seem to have nothing to do with it:

| | |
|---|---|
| marker 0 | a room has just been described |
| marker 1 | this place has light |
| marker 2 | the player carries something alight |
| marker 3 | do not tell the score at the end |
| counter 0 | the score |
| counter 126 | the turns, **low** byte |
| counter 127 | the turns, **high** byte |

The turns go in that order -- 126 is the low one -- and they go up one at a
time with every order.

**In the dark** -- markers 1 and 2 both clear -- nothing is described: the
window of the picture is cleared, message 251 is said and **marker 0 is not
set**, because nothing was described.

Marker 1 is set from the start. An adventure that keeps a flag of its own in
it -- a door that is open -- finds it open before anybody opened it: the
flags of an adventure begin at 4.

---

## 6. The messages the interpreter uses

From 240 to 255 the interpreter says them by itself. Write them all:

| | | | |
|---|---|---|---|
| 240 | what it asks with | 248 | too heavy |
| 241 | you can't do that | 249 | your score is |
| 242 | pardon? | 250 | and you took |
| 243 | another game? | 251 | it is dark |
| 244 | are you sure? | 252 | I can't find it |
| 245 | you already have it | 253 | I can also see |
| 246 | you don't have it | 254 | okay |
| 247 | I can't see it | 255 | turns |

---

## 7. How it understands what is typed

- **Beginnings of words match.** With `EXAMINE` in the vocabulary, `EX`, `EXA`
  and `EXAMINE` are good; `EXAMINES` is **not**, which is longer than the word
  kept. The price is that `LA` is eaten by `LAMP`, and the original pays it
  too.
- Of the words that start the same, **the shortest wins**.
- An order is **verb, noun, second noun and adverb**, and any of them may be
  missing.
- A **pronoun** stands for the noun of the order before.
- A word it knows with which there is nothing to do gives "you can't do
  that"; a line with **neither** a verb nor a noun it knows gives "pardon?".

---

## 8. The pictures

They are not bitmaps: they are **lists of drawing orders**. That is why a
whole adventure fits on a tape, and why the same picture comes out on nine
different machines.

### The canvas

As in the Spectrum's BASIC: **`x` from 0 to 255** from left to right, **`y`
from 0 at the bottom to 175 at the top**. The picture takes the top sixteen
rows of characters -- 128 rows of pixels, `y` from 48 to 175 -- and the eight
below are the text's. The row on the screen is `175 - y`.

### The colour

The values are BASIC's: **0 to 7** the colours, **8** leaves whatever was
there, **9** picks black or white, whichever reads better. The colour goes by
cells of eight by eight, with the Spectrum's limit of attributes.

### The orders

| | |
|---|---|
| `BORDER c` | colour of the border |
| `INK c` | the ink in force |
| `PAPER c` | the paper in force |
| `BRIGHT b` | the brightness in force |
| `FLASH f` | the flashing in force |
| `PLOT x y` | sets a pixel |
| `LINE x1 y1 x2 y2` | a line between two points |
| `RECT x1 y1 x2 y2` | the outline of a rectangle |
| `ELLIPSE x y x2 y2` | an ellipse centred on x y; the second point gives the radii, which are how far it is from it |
| `FILL x y` | colours the region, without touching the pixels |
| `BGFILL x y` | colours the region and clears its pixels as well |
| `SHADE x y` | fills the region with a half tone |
| `CALL n` | runs another picture, for what is repeated, like frames |
| `PENS a b` | the two pens a fill weaves together (Amstrad only) |

The three fills spread from a point and are stopped by **the pixels already
set** and the edges of the picture.

Things worth knowing when drawing, measured on the original:

- **A gap of one pixel in a wall lets the fill out**, but only along that
  row: a ray one pixel high goes out as far as the next thing that stops it,
  and does not widen. If a wall of yours has a hole, it will show as a line,
  not as a stain. `regac draw` warns of it.
- **A passage one pixel wide is filled.**
- **A diagonal for a wall does not let it through**: the fill stops at the
  steps.
- And if the seed falls **on a pixel that is set**, nothing at all happens.

`CALL` is how backgrounds are shared: one picture with the frame, and the
others call it.

---

## 9. What limits an adventure

Not the format: **where it has to fit**. The room is shared between the
interpreter and the database, and every machine has its own. The tightest is
the **CPC 464**: no banks, and the database in one stretch.

Two commands say it before anything is built:

    python -m regac text  adventure.json      # what the texts take
    python -m regac check adventure.json      # and that nothing points at nothing

---

## 10. What this has that the GAC of 1986 had not

The principle of the project is that **the interpreters do what the original
did**, even in what looks like a fault: where a line breaks, what it answers
to a word it does not know, in what order it looks at the tables. What is
added sits on top and does not change what is below:

- **accents and ñ**, which the original had not;
- **noises**, with `SOUND` and `QUIET`;
- **tables of one's own**, with `/PROC` and `DO`;
- **close ups**, with `DRAW`;
- **holes in the text**, `\ctr n`, `\obj n` and `\turns`, which write a
  counter, the name of an object or the turns where they stand;
- **nine machines**;
- **a text source**, kept under version control, instead of the adventure
  typed into the machine.

And one thing the original does that is **not copied**, said so that it does
not come as a surprise: deciding where to break a line, it looks one
character past the end of the message and goes on counting whatever was left
in the buffer of the message before. That is not a behaviour, it is an
accident of its memory.

---

## Where next

| if you are looking for | see |
|---|---|
| building your first adventure | [`manual.md`](manual.md) |
| the source format, section by section | [`source-format.md`](source-format.md) |
| a whole adventure written to be read | [`../../ejemplo/faro.gac`](../../ejemplo/faro.gac) |
