; MIT License, Copyright (c) 2025 Cronomantic
;
; A build that starts a tune on an MSX and then does nothing whatever, so that
; a test can see the music being played by the interrupt and not by anything
; else.
;
; It takes the whole machine first, as the interpreter does, because that is
; the condition worth proving: with RAM in all four pages there is a database
; where the ROM's interrupt went, and the tune still has to be played.  The
; main loop counts, and only counts.

                DEVICE  NOSLOT64K

                DEFINE PLY_AKM_HARDWARE_MSX 1

STACK_AT        equ $EF00
VDP_ADDR        equ $99                 ; screen.asm is not here to say it

                ORG     $8000
start:
                di
                ld      sp, STACK_AT
                call    interrupt_hertz         ; while the BIOS is still there
                call    take_the_machine
                call    music_init
                call    interrupt_init
                xor     a                       ; the one tune this has
                call    music_start
                ei
                ld      a, $FF
                ld      (playing_flag), a
.count:
                ld      hl, (spins)
                inc     hl
                ld      (spins), hl
                jr      .count

playing_flag:   db      0
spins:          dw      0

                include "slots.asm"
                include "../common/music.asm"
                include "../arkos/PlayerAkm.asm"

                include "interrupt.asm"

; The list of tunes, which here is one line long, and the tune itself: the
; author's music, which is not this project's to carry.  See music/.
music_tunes:
                MUSIC_TUNE tune, last, 0
music_tunes_end:
tune:
                include "../../music/test.asm"
last:
                ASSERT  last <= IM2_TABLE

                SAVEBIN "music.bin", start, last - start
