#!/bin/bash
# Every snapshot through the reference decompiler, for comparing against ours.
# ungac lives in tools/ with the assembler and the emulator, because it is
# somebody else's program and not part of this one.
for f in ./snapshots/*.sna; do
    ./tools/ungac-0.2/ungacw32.exe -o${f/%sna/txt} "$f"
done
