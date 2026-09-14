# ReGAC

Implementation of a decompiler and simple interpreter for Graphic Adventure Creator games for Spectrum.

## Components

* deGAC.py: Parse a SNA Spectrum image file of a GAC adventure to extract data to a JSON file
* runGAC.py: Simple interpreter for the previous JSON file. Text only.
* runGAC_pygame.py: The same interpreter behind a Spectrum-like screen.
* regac: Decompiler and compiler for the editable source format, the renderer
  for the vector graphics, the binary database the 8 bit interpreters read and
  the media they are shipped on. See [doc/formato-fuente.md](doc/formato-fuente.md)
  and [doc/graficos.md](doc/graficos.md), plus the text storage described in
  [doc/textos.md](doc/textos.md) and the binary database in
  [doc/binario.md](doc/binario.md).
* disk.py: Read a file off an Amstrad disk image, or a whole adventure off one
  that was laid out so that it could not be copied.
* grab.py: Load a disk, a tape or a snapshot on the machine it belongs to and
  write out what it left in memory, for the decompiler to read.
* z80: The interpreters themselves. The Spectrum ones write their own tape as
  they assemble; the Amstrad's disk and tape are made with `regac release`.

```
python -m regac decompile game.json game.gac
python -m regac compile   game.gac  game.json
python -m regac check     game.json
python -m regac render    game.json pictures/ -m spectrum
python -m regac checkgfx  game.json -m cpc
python -m regac text      game.json
python -m regac build     game.json game.rgac -m spectrum128 -b 16k
python -m regac release   game.bin  release/ -m cpc
```

## Licence

Two, on purpose.

The tools -- everything in Python -- are under the **GNU General Public
License v3**, whose text is in [LICENSE](LICENSE).

The interpreters in [z80/](z80), which are what ends up inside somebody's
adventure, are under the **MIT licence**: see [z80/LICENSE](z80/LICENSE).  An
adventure built with these tools carries no obligation from them.

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

