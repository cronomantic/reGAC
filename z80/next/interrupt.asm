; MIT License, Copyright (c) 2025 Cronomantic
;
; The fifty interrupts a second the music is played from, on a Spectrum Next.
;
; Mode two for the Spectrum's reason -- $0038 is the ROM's handler, and here
; it is not even the ROM but a bank of the database in the window at $0000 --
; and fifty a second, so there is nothing to count.
;
; Where it goes is the one thing this machine has to think about, because its
; map is fuller than any other's.  What never moves is $8000 to $BFFF: below
; that is the window, above it is whichever piece of layer 2 is being drawn.
; Of that, the interpreter has $8000 up, the fill's mask has the four
; kilobytes at $A000 -- it must be on that boundary -- and the stack comes
; down from $BF00.  That leaves the kilobytes from $B000, and the table goes
; at the bottom of them with the routine just above it, as far from the stack
; as they can be.

IM2_TABLE       equ $B000               ; 257 bytes of IM2_FILLER
IM2_FILLER      equ $B1                 ; whose pair, $B1B1, is just above them

                MACRO   INTERRUPT_ACK
                ENDM                    ; the display interrupt clears itself

interrupt_init  equ im2_init            ; there is nothing else to do here

                include "../common/im2.asm"
