; MIT License, Copyright (c) 2025 Cronomantic
;
; A build that makes one noise over and over on an Amstrad, so that a test can
; hear whether the sound chip is doing what a one bit speaker does everywhere
; else.
;
; What it plays is poked into `which`: nought for silence, and a number for
; that effect of the table.

                DEVICE  AMSTRADCPC6128

GATE_ARRAY      equ $7F00
BOTH_ROMS_OUT   equ %10001101           ; mode 1, and the memory to ourselves

                ORG     $4000
start:
                di
                ld      sp, $BF00
                ld      bc, GATE_ARRAY
                ld      a, BOTH_ROMS_OUT
                out     (c), a
                ld      a, $FF
                ld      (ready_flag), a
.again:
                ld      hl, (rounds)
                inc     hl
                ld      (rounds), hl
                ld      a, (which)
                call    beep_sound
                jr      .again

ready_flag:     db      0
which:          db      0
how_many:       db      BEEP_SOUNDS     ; so the test need not count them
rounds:         dw      0

                include "ay.asm"

last:
                SAVEBIN "sound.bin", start, last - start
