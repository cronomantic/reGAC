; MIT License, Copyright (c) 2025 Cronomantic
;
; A build that starts a tune and then does nothing whatever, so that a test can
; see the music being played by the interrupt and not by anything else.
;
; The main loop counts, and only counts.  If the tune moves on while it counts,
; the fifty interrupts a second are arriving, the mode two table and its
; routine are where they should be, and the player is reading a tune that no
; paging can take away from it -- which is the whole of what this machine has
; to get right for music.

                DEVICE  ZXSPECTRUM128

                DEFINE PLY_AKM_HARDWARE_SPECTRUM 1

                ORG     $8000
start:
                di
                ld      sp, $7FF0
                call    music_init
                call    interrupt_init
                ld      hl, tune
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

; A tune the author made, which is not this project's to carry: see music/.
tune:
                include "../../music/test.asm"
last:
                ASSERT  last < IM2_HANDLER

                include "interrupt.asm"

                SAVESNA "music.sna", start
