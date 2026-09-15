; MIT License, Copyright (c) 2025 Cronomantic
;
; A build that makes one noise over and over, so that a test can watch the
; speaker move.
;
; The speaker of this machine cannot be read back, but the emulator keeps the
; last value written to the port it is on, and that is enough to see three
; things: that the bit moves at all, that it stops moving when nothing is
; being played, and that the three bits of border in the same port come
; through untouched -- which is the whole reason the border is kept in memory.
;
; What it plays is poked into `which`: nought for silence, a number for that
; effect, and CLICK for the click a key makes.

                DEVICE  ZXSPECTRUM48

CLICK           equ 200                 ; not an effect: the key click
A_BORDER        equ 5                   ; something that is not black

                ORG     $8000
start:
                di
                ld      sp, $7FF0
                ld      a, A_BORDER
                ld      (gfx_border), a
                out     ($FE), a
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
how_many:       db      BEEP_SOUNDS     ; so the test need not count them
rounds:         dw      0
gfx_border:     db      0               ; screen.asm keeps this in a real build

                include "beep.asm"

                SAVESNA "beep.sna", start
