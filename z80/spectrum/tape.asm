; MIT License, Copyright (c) 2025 Cronomantic
;
; Saving and loading a game, on the Spectrum's tape.
;
; The ROM does the work, as it did for the original: one block of the kind a
; BASIC program would call data, with no header in front of it, so loading is
; simply reading whatever comes next.  GAC saved its whole database that way,
; from $5DC0 to wherever it ended; we only have to save what changes, because
; the adventure and the state of the game are kept apart here.
;
; The routines want interrupts off, which is how the runtime runs anyway, and
; the system variables where the ROM expects them.

ROM_SA_BYTES    equ $04C2
ROM_LD_BYTES    equ $0556
SYSTEM_VARS     equ $5C3A

; Put the block at IX, DE bytes of it, on the tape.
; Corrupts: everything
tape_save:
                di
                push    iy
                ld      iy, SYSTEM_VARS
                ld      a, $FF                  ; a block of data, not a header
                call    ROM_SA_BYTES
                pop     iy
                di
                ret

; Read a block of DE bytes back into IX.  Carry set when it came in whole.
; Corrupts: everything
tape_load:
                di
                push    iy
                ld      iy, SYSTEM_VARS
                ld      a, $FF
                scf                             ; load it, rather than compare
                call    ROM_LD_BYTES
                pop     iy
                di
                ret
