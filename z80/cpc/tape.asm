; MIT License, Copyright (c) 2025 Cronomantic
;
; Saving and loading a game on the Amstrad, which is not written yet.
;
; The Spectrum hands its block to the ROM, which is two calls and nothing
; more.  Here the firmware is paged out while the interpreter runs, so the
; cassette routines would have to be brought back in around the call, or
; written from scratch; and a disk is another thing again.  Until then these
; say they did nothing, which leaves the game as it was.

; Put the block at IX, DE bytes of it, on the tape.
tape_save:
                ret

; Read a block of DE bytes back into IX.  Carry clear: nothing came in.
tape_load:
                or      a
                ret
