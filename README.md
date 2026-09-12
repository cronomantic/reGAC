# ReGAC

Implementation of a decompiler and simple interpreter for Graphic Adventure Creator games for Spectrum.

## Components

* deGAC.py: Parse a SNA Spectrum image file of a GAC adventure to extract data to a JSON file
* runGAC.py: Simple interpreter for the previous JSON file. Text only.
* runGAC_pygame.py: The same interpreter behind a Spectrum-like screen.
* regac: Decompiler and compiler for the editable source format, and the
  renderer for the vector graphics. See [doc/formato-fuente.md](doc/formato-fuente.md)
  and [doc/graficos.md](doc/graficos.md), plus the text storage described in
  [doc/textos.md](doc/textos.md) and the binary database in
  [doc/binario.md](doc/binario.md).

```
python -m regac decompile game.json game.gac
python -m regac compile   game.gac  game.json
python -m regac check     game.json
python -m regac render    game.json pictures/ -m spectrum
python -m regac checkgfx  game.json -m cpc
python -m regac text      game.json
python -m regac build     game.json game.rgac -m spectrum128 -b 16k
```

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

