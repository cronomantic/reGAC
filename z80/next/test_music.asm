; MIT License, Copyright (c) 2025 Cronomantic
;
; A build that starts a tune on a Spectrum Next and then does nothing whatever,
; so that a test can see the music being played by the interrupt and not by
; anything else.
;
; The sound chip here is the Spectrum's, at the same two ports and the same
; clock, so the player is the Spectrum's as well; what is this machine's own
; is where the interrupt can live, because the map is fuller.  The main loop
; counts, and only counts.
;
; It is loaded as a .nex file, which the assembler writes itself.

                DEVICE  ZXSPECTRUMNEXT

                DEFINE PLY_AKM_HARDWARE_SPECTRUM 1

STACK_AT        equ $BF00
REG_TURBO       equ $07
TURBO_28        equ 3

                ORG     $8000
start:
                di
                ld      sp, STACK_AT
                nextreg REG_TURBO, TURBO_28     ; the speed this machine has
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

                include "../common/music.asm"
                include "../arkos/PlayerAkm.asm"
                include "interrupt.asm"

; The list of tunes, which here is one line long, and the tune itself: the
; author's music, which is not this project's to carry.  See music/.
music_tunes:
                MUSIC_TUNE tune, 0
music_tunes_end:
tune:
                include "../../music/test.asm"
last:
                ASSERT  last <= IM2_TABLE

                SAVENEX OPEN "music.nex", start, STACK_AT
                SAVENEX CORE 3, 0, 0
                SAVENEX CFG  0
                SAVENEX AUTO
                SAVENEX CLOSE
