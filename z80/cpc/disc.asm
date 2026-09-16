; MIT License, Copyright (c) 2025 Cronomantic
;
; Saving and loading a game on a 6128, which is the disk and not the tape.
;
; Not written yet, and what goes here is decided: the same thing the PCW
; does.  A file the builder made, of the right size and empty, whose first
; track and record it wrote down; the runtime reads those numbers and writes
; the sectors, without ever touching the directory.  The controller is the
; same PD765, at ports $FB7E and $FB7F with the motor at $FA7E, so what
; changes from z80/pcw/disc.asm is the ports and the format of a track --
; nine sectors of five hundred and twelve numbered $C1 to $C9 on an Amstrad
; data disk.
;
; It cannot go through the firmware, which is what a 464 does: an entry of
; the jumpblock is a restart and a restart brings the lower ROM back, and on
; this machine the lower ROM covers the resident half of the database.  That
; is the whole reason this file exists rather than tape.asm being included.
;
; Until it is written, saying so honestly beats pretending: both come back
; with the carry clear, which is what every other machine says when the
; medium would not have it.

; Put the block at IX, DE bytes of it, on the disk.  Carry set when it went.
; Corrupts: nothing yet
tape_save:
                or      a
                ret

; Read the block back into IX, DE bytes of it.  Carry set when it came.
; Corrupts: nothing yet
tape_load:
                or      a
                ret
