; MIT License, Copyright (c) 2025 Cronomantic
;
; The interrupts the music is played from, on an Amstrad.
;
; This is the one machine of the four that keeps mode one, and it can because
; of how it is set up: both ROMs are out of the way -- screen.asm turns them
; off to have the memory -- so $0038 is our own RAM, under where the lower ROM
; would be, and a jump written there is where the interrupt goes.  The
; database is above $4000 and never reaches down there.
;
; What is this machine's own is how often it happens: three hundred times a
; second, so five interrupts in six do nothing but count.  The gate array
; needs nothing said to it afterwards.
;
; One thing to remember when the music is turned on in the interpreter: the
; sound chip here is behind the same eight two five five the keyboard is read
; through, so a scan that is interrupted half way is a scan that reads the
; wrong row.  The scanning has to have them off while it lasts, and only in a
; build that has music at all -- turning them on again where there is no
; handler would jump into whatever is at $0038.

IM1_VECTOR      equ $0038               ; where a mode one interrupt goes
JUMP            equ $C3

                MACRO   INTERRUPT_ACK
                ENDM                    ; nothing to be told here

; Put the jump where the interrupt will go, and let them in.
; Corrupts: AF, HL
interrupt_init:
                di
                ld      a, JUMP
                ld      (IM1_VECTOR), a
                ld      hl, interrupt_handler
                ld      (IM1_VECTOR + 1), hl
                im      1
                ei
                ret

                include "../common/ticker.asm"
