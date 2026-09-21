; MIT License, Copyright (c) 2025 Cronomantic
;
; The same as spectrum/test_ay.asm on an MSX, whose chip is reached through
; two ports of its own rather than two of the Spectrum's.
;
; This one is worth having on its own and not taken on trust from the
; Spectrum's, because here register seven is not only the mixer: its top two
; bits say which way the chip's own ports face, and those ports are the
; joysticks.  A build that got that wrong would still make a noise, so what
; the recording proves is only half of it -- the other half is that the
; machine goes on running, which `rounds` says.

                DEVICE  NOSLOT64K

CLICK           equ 200                 ; not an effect: the key click

; The stack goes in the top page, which is RAM on any MSX.  Where the
; Spectrum's builds put it -- just under the code, at $7FF0 -- is the BIOS
; here, and a call would push into ROM and come back to nowhere.
STACK_AT        equ $EF00

                ORG     $8000
start:
                di
                ld      sp, STACK_AT
                ld      a, $FF
                ld      (ready_flag), a
.again:
                ld      a, (which)
                cp      CLICK
                jr      z, .click
                call    beep_sound
                jr      .round
.click:
                call    beep_click
.round:
                ld      hl, (rounds)
                inc     hl
                ld      (rounds), hl
                jr      .again

ready_flag:     db      0
which:          db      0
how_many:       db      BEEP_SOUNDS
rounds:         dw      0

                include "ay.asm"

last:
                SAVEBIN "ay.bin", start, last - start
