; MIT License, Copyright (c) 2025 Cronomantic
;
; The speaker of an MSX, which is bit seven of the same port as the keyboard
; row -- the machine's own key click, which is what the BIOS uses it for.
;
; The rest of that port is not ours: the cassette motor, the cassette output
; and the caps lamp are in the three bits below it, and keyboard_init noted
; what the machine had in them.  The row goes out as nought, which costs
; nothing: the next look at the keyboard writes its own.

BEEP_BIT        equ %10000000

                MACRO   BEEP_BASE
                ld      a, (ppi_top)
                and     %01110000       ; what is not ours, with the click off
                ENDM

                MACRO   BEEP_OUT
                out     (PPI_C), a
                ENDM

                include "../common/beep.asm"
