; MIT License, Copyright (c) 2025 Cronomantic
;
; A build that makes one noise over and over on an Amstrad, so that a test can
; hear whether the sound chip is doing what a one bit speaker does everywhere
; else.
;
; What it plays is poked into `which`: nought for silence, a number for that
; effect of the table, and CLICK for the click a key makes.
;
; The table and the player travel only in a build that asked for them, which
; on this machine is what -DNOISES says; the click goes out in every build,
; because the original clicked at every key.  So NOISES is **not** set here:
; it is given on the command line, and the test builds this twice to hear
; that the click sounds either way and that the effects only sound when they
; were asked for.
;
; The word asked after here is NOISES and not WITH_NOISES, although the rest
; of the interpreter reads the second: an IFDEF is read where it stands, and
; ay.asm -- which is what turns one word into the other -- comes in at the
; bottom of this file.

CLICK           equ 200                 ; not an effect: the key click

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
                cp      CLICK
                jr      z, .click
                IFDEF NOISES
                call    beep_sound
                ENDIF
                jr      .again
.click:
                call    beep_click
                jr      .again

; A second way in, for measuring rather than listening: a test points the
; processor here and the effect in `which` is played REPEATS times, with the
; processor's own cycle counter reset around it.  How long a noise lasts is
; not something a recording can tell -- it says that something sounded, not
; for how long -- and the table says how long each one is meant to be.
;
; Why so many and not one: what the test can see is `done_flag`, and it can
; only look every so often, so the spinning between the flag going up and the
; look that catches it is counted too.  A twentieth of a second of looking is
; two hundred thousand cycles of this machine, which is the same size as the
; differences being measured.  Sixteen goes drown it.
REPEATS         equ 16
play_many:
                ld      sp, $BF00
                xor     a
                ld      (done_flag), a
                ld      b, REPEATS
.again:
                push    bc
                IFDEF NOISES
                ld      a, (which)
                call    beep_sound
                ENDIF
                pop     bc
                djnz    .again
                ld      a, $FF
                ld      (done_flag), a
.stop:
                jr      .stop

ready_flag:     db      0
done_flag:      db      0
which:          db      0
                IFDEF NOISES
how_many:       db      BEEP_SOUNDS     ; so the test need not count them
                ELSE
how_many:       db      0               ; this build was given none
                ENDIF
rounds:         dw      0

                include "ay.asm"

last:
                SAVEBIN "sound.bin", start, last - start
