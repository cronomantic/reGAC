; MIT License, Copyright (c) 2025 Cronomantic
;
; A build that makes one noise over and over on a 128, so that a test can hear
; whether the sound chip does what the speaker of one bit does on a 48.
;
; A chip's output cannot be watched at a port the way a flipped bit can -- the
; two ports it is on are write only -- so what is listened to is the recording
; the emulator writes of everything it plays.  Silence is a recording that
; never moves.
;
; What it plays is poked into `which`: nought for silence, a number for that
; effect of the table, and CLICK for the click a key makes.

                DEVICE  ZXSPECTRUM128

CLICK           equ 200                 ; not an effect: the key click

                ORG     $8000
start:
                di
                ld      sp, $7FF0
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

                include "ay.asm"

last:
                SAVEBIN "ay.bin", start, last - start
