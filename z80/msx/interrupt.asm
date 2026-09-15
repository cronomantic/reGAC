; MIT License, Copyright (c) 2025 Cronomantic
;
; The interrupts the music is played from, on an MSX.
;
; Mode two, and not because the ROM's handler would be in the way: on this
; machine the interpreter takes all sixty four kilobytes, so what is at $0038
; is the database.  A mode one interrupt would run it as instructions.
;
; The table and the routine go just under $C000, above everything the
; interpreter itself uses and below the copy of the screen -- which is to say
; in the half of the map the BIOS never comes back into.  That matters here
; more than anywhere: the BIOS returns to the bottom half for as long as a
; save takes, and the database is down there with it.
;
; Two things are this machine's own.  The video chip only interrupts if it is
; told to -- screen.asm sets it up not to, because nothing wanted it before --
; so register one is written again with the bit on; and the interrupt is only
; over when the chip's status has been read, or it would arrive again the
; moment we let it.
;
; The other is the rate.  A machine built for a European television interrupts
; fifty times a second and one built for a Japanese or American television
; sixty, and the only way to know which is to ask the BIOS -- bit seven of
; $002B, which is set on a fifty hertz machine.  That has to be read before
; the machine is taken, because by then the BIOS is not there to ask; so it is
; read where the interpreter starts and kept in a byte.

IM2_TABLE       equ $BE00               ; 257 bytes of IM2_FILLER
IM2_FILLER      equ $BD                 ; whose pair, $BDBD, is under them

ROM_VERSION     equ $002B               ; bit 7: this is a fifty hertz machine
VDP_INTERRUPTS  equ $E0                 ; register one, with the bit on

                MACRO   INTERRUPT_ACK
                in      a, (VDP_ADDR)   ; the status, which is the chip told
                ENDM

; What television this machine was built for, asked of the BIOS while the BIOS
; is still there.  Call it before take_the_machine and not after.
; Corrupts: AF, HL
interrupt_hertz:
                ld      hl, 60
                ld      a, (ROM_VERSION)
                and     %10000000
                jr      z, .keep
                ld      hl, 50
.keep:
                ld      (machine_hertz), hl
                ret

; Then the mode two setting up, with the rate that was found put where the
; music will look for it and the chip told to interrupt at all.
; Corrupts: AF, BC, DE, HL
interrupt_init:
                ld      hl, (machine_hertz)
                ld      (music_rate), hl
                ld      a, VDP_INTERRUPTS
                out     (VDP_ADDR), a
                ld      a, $80 | 1
                out     (VDP_ADDR), a
                jp      im2_init

machine_hertz:  dw      50              ; until the ROM has been asked

                include "../common/im2.asm"
