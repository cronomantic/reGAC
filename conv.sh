#!/bin/bash
for f in ./snapshots/*.sna; do
    ./ungac-0.2/ungacw32.exe -o${f/%sna/txt} "$f"
done
