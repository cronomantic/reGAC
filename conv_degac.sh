#!/bin/bash
for f in ./snapshots/*.sna; do
    python ./deGAC.py "$f" "${f/%sna/json}"
done
