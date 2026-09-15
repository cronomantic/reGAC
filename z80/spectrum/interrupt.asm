; MIT License, Copyright (c) 2025 Cronomantic
;
; The fifty interrupts a second the music is played from, on a Spectrum.
;
; Both the table and the routine live above the interpreter and below the
; window at $C000, in the page that is there whatever is paged in.  Fifty a
; second is what a tune wants, so this machine counts nothing.
;
; There is nothing to acknowledge: the interrupt comes from the display and
; goes away by itself.

IM2_TABLE       equ $BE00               ; 257 bytes of IM2_FILLER
IM2_FILLER      equ $BD                 ; whose pair, $BDBD, is under them

                MACRO   INTERRUPT_ACK
                ENDM

interrupt_init  equ im2_init            ; there is nothing else to do here

                include "../common/im2.asm"
