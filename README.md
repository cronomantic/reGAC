# reGAC

*[Leer en español](LEEME.md)*

Write a Graphic Adventure Creator adventure as a text file and publish it on
nine eighties machines with one command -- or rescue one from a 1986 tape and
read it as source.

The nine: the Spectrum 48, 128 and +3, the Amstrad CPC 464 and 6128, the
Amstrad PCW, the MSX, the Spectrum Next, and a PC with a CGA, from an XT at
4.77 MHz up.

## Installing

What it needs:

* **Python 3.11** or newer.
* **sjasmplus**, which assembles the interpreters of the Z80 machines: in the
  `tools/` folder of reGAC or anywhere on the path.
* **NASM**, only for the PC, in `tools/` or on the path.
* **ZEsarUX** in `tools/` and **DOSBox-X** on the path only to run the tests,
  to extract an adventure from a machine with `grab.py`, or to time a picture
  in `regac draw`.

From a release, download `regac-<version>.zip`, unzip it, and in its folder:

    pip install -e .

which makes `regac` a command of its own; `python -m regac` does the same
from inside the folder without installing anything.  It is installed pointing
at the folder and not copied from it, because the interpreters it builds with
are the folders beside it, `z80/` and `x86/`.  From a clone of the repository
it is the same, or `poetry install`.

The release also carries `example-faro-<version>.zip`: the example adventure
already built for the nine machines, to load in an emulator straight away.

## In five minutes

    regac make ejemplo/faro.toml

builds *El faro de Santa Bárbara*, the example, for the nine machines, into
`ejemplo/salida/`.  To play it without any machine:

    regac play ejemplo/faro.gac ejemplo/solucion.txt --expect "Fin de la aventura"

or, to type the orders yourself:

    regac compile ejemplo/faro.gac faro.json
    python runGAC.py faro.json

The example is in Spanish, like the adventures of 1986 this project started
from; an adventure can be written in any language with the Latin alphabet.

## Documentation

* **[doc/en/manual.md](doc/en/manual.md)** -- the user manual: what to
  install, how an adventure is written block by block, how it is checked,
  drawn and built for every machine.
* **[doc/en/gac.md](doc/en/gac.md)** -- the GAC language in full: the turn,
  every opcode, the parser, the reserved markers and messages, and every
  drawing command.
* **[doc/en/source-format.md](doc/en/source-format.md)** -- the source
  format, section by section.

The same three in Spanish are in [doc/](doc/manual.md).  The rest of `doc/`,
in Spanish only, is the development diary and notes on how each piece was
made: what was measured, in what order and why.

## The commands

| | |
|---|---|
| `regac compile game.gac game.json` | the source into a database, or says where it is wrong |
| `regac decompile game.json game.gac` | and back |
| `regac check game.json` | that nothing points at something that is not there |
| `regac lint game.gac` | what is there and nothing uses |
| `regac map game.gac map.svg` | the map of the rooms |
| `regac play game.gac solution.txt` | plays a file of orders and says whether the game ended |
| `regac draw game.gac 12 -m cpc` | a picture in a window: looked at, drawn on, traced, timed |
| `regac render game.json pictures/` | the pictures as PNG |
| `regac text game.json` | what the text takes, packed |
| `regac make game.toml --zip game.zip` | every machine a project names |
| `regac build`, `regac release` | one machine at a time, by hand |

## Components

* **regac**: the compiler and decompiler of the source, the renderer of the
  pictures, the database the interpreters read, the media they are shipped
  on, and the tools above.
* **z80**: the interpreters of the Z80 machines -- Spectrum, Amstrad CPC,
  Amstrad PCW, MSX and Spectrum Next.
* **x86**: the PC's interpreter, in 8086 assembler for NASM.
* **runGAC.py**, **runGAC_pygame.py**: the interpreter in Python, in a
  terminal or behind a Spectrum-like screen.
* **deGAC.py**: an adventure out of a snapshot of a Spectrum or of an Amstrad
  disk, as JSON.
* **disk.py**: a file off an Amstrad disk image, or a whole adventure off one
  laid out so that it could not be copied.
* **grab.py**: a disk, a tape or a snapshot loaded on its machine, and what it
  left in memory written out, for the decompiler to read.
* **editors/vscode**: the colours of a `.gac` source in VS Code.

## Licence

Two, on purpose.

The tools -- everything in Python -- are under the **GNU General Public
License v3**, whose text is in [LICENSE](LICENSE).

The interpreters in [z80/](z80) and [x86/](x86), which are what ends up
inside somebody's adventure, are under the **MIT licence**: see
[z80/LICENSE](z80/LICENSE) and [x86/LICENSE](x86/LICENSE).  An adventure built
with these tools carries no obligation from them.

The letters an adventure gets when it brings none of its own,
[regac/moderndos8x8.bin](regac/moderndos8x8.bin), are **Modern DOS 8x8** by
Jayvee Enaguas, dedicated to the public domain under CC0 1.0: see
[regac/moderndos.py](regac/moderndos.py).

--

MIT License

Copyright (c) 2025 Cronomantic

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
