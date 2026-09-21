; MIT License, Copyright (c) 2025 Cronomantic
;
; The same as spectrum/test_ay.asm and on the same chip at the same ports --
; this machine has three of them and one is what a blip wants -- built for a
; Next so that its own build is the one being listened to.

                DEVICE  ZXSPECTRUMNEXT

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
how_many:       db      BEEP_SOUNDS
rounds:         dw      0

                include "../spectrum/ay.asm"

last:
                SAVEBIN "ay.bin", start, last - start
