; MIT License, Copyright (c) 2025 Cronomantic
;
; A build that starts a tune on an Amstrad and then does nothing whatever, so
; that a test can see the music being played by the interrupt and not by
; anything else.
;
; The ROMs go out of the way first, as the interpreter's screen setting up
; does, because that is what puts RAM at $0038 where the interrupt goes.  The
; main loop counts, and only counts -- three hundred times a second something
; else happens, and one time in six of those the tune moves on.

                DEVICE  AMSTRADCPC6128

                DEFINE PLY_AKM_HARDWARE_CPC 1
                DEFINE MUSIC_RATE 300   ; how often this machine interrupts

GATE_ARRAY      equ $7F00
BOTH_ROMS_OUT   equ %10001101           ; mode 1, and the memory to ourselves

                ORG     $4000
start:
                di
                ld      sp, $BF00
                ld      bc, GATE_ARRAY
                ld      a, BOTH_ROMS_OUT
                out     (c), a
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
                MUSIC_TUNE tune, last, 0
music_tunes_end:
tune:
                include "../../music/test.asm"
last:

                SAVEBIN "music.bin", start, last - start
