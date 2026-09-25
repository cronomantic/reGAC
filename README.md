# ReGAC

Write a Graphic Adventure Creator adventure as a text file and publish it on
nine eighties machines with one command -- or rescue one from a 1986 tape and
read it as source.

The nine: the Spectrum 48, 128 and +3, the Amstrad CPC 464 and 6128, the
Amstrad PCW, the MSX, the Spectrum Next, and a PC with a CGA, from an XT at
4.77 MHz up.

## Documentation

Two documents, in Spanish, and between them they are the whole of it:

* **[doc/manual.md](doc/manual.md)** -- the user manual: what to install, how
  an adventure is written block by block, how it is checked and how it is
  built for every machine.
* **[doc/gac.md](doc/gac.md)** -- the GAC language in full: the turn, all
  sixty eight opcodes, the parser, the reserved markers and messages, and
  every drawing command.

The rest of `doc/` is the development diary -- what was measured, in what
order and why. It is not reference material.

## Components

* deGAC.py: Parse a SNA Spectrum image file of a GAC adventure to extract data to a JSON file
* runGAC.py: Simple interpreter for the previous JSON file. Text only.
* runGAC_pygame.py: The same interpreter behind a Spectrum-like screen.
* regac: Decompiler and compiler for the editable source format, the renderer
  for the vector graphics, the binary database the 8 bit interpreters read and
  the media they are shipped on. See [doc/manual.md](doc/manual.md).
* disk.py: Read a file off an Amstrad disk image, or a whole adventure off one
  that was laid out so that it could not be copied.
* grab.py: Load a disk, a tape or a snapshot on the machine it belongs to and
  write out what it left in memory, for the decompiler to read.
* z80: The interpreters themselves, for the Spectrum, the Amstrad CPC, the
  Amstrad PCW, the MSX and the Spectrum Next. The Spectrum ones write their own
  tape as they assemble and the Next its own .nex; the Amstrad's disk and tape,
  the PCW's self-starting disk and the MSX's cassette are made with
  `regac release`.
* x86: The PC's interpreter, in 8086 assembler for NASM. `regac make` puts it
  and the adventure together in one DOS .EXE named after the project.

`poetry install` (or `pip install -e .`) in the checkout makes `regac` a
command of its own, the same as `python -m regac` from anywhere; it is
installed pointing at the checkout, because the interpreters it builds with
are the folders beside it.

What has to be installed besides Python -- sjasmplus for the Z80 machines,
NASM for the PC, and ZEsarUX and DOSBox-X only to run the tests -- is in
[doc/manual.md](doc/manual.md).

```
python -m regac decompile game.json game.gac
python -m regac compile   game.gac  game.json
python -m regac check     game.json
python -m regac render    game.json pictures/ -m spectrum
python -m regac draw      game.gac  12 -m cpc
python -m regac checkgfx  game.json -m cpc
python -m regac text      game.json
python -m regac make      game.toml
python -m regac make      game.toml --zip game.zip
python -m regac build     game.json game.rgac -m spectrum128 -b 16k
python -m regac build     game.json game.rgac -m pc -b 64k
python -m regac release   game.bin  release/ -m cpc
python -m regac release   game_code.bin release/ -m pcw        --boot boot.bin --database game.rgac
python -m regac release   game.bin  release/ -m msx           --database game.rgac
```

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

