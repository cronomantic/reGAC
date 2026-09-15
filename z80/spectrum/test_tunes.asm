; MIT License, Copyright (c) 2025 Cronomantic
;
; A build with more than one tune in it, so that a test can see the right one
; being played and then another one taking over.
;
; The two tunes here are the same export included twice, because one tune is
; all this project has to test with and any two would do: what is looked at is
; not what is played but *where the player is reading*, and two copies are two
; addresses.  A build of an adventure would name two different songs, or the
; same song twice with a different subsong on each line, which costs almost
; nothing because the subsongs of one export share their instruments.
;
; Each one is wrapped in a module of its own, and that is not tidiness.  The
; tracker names the labels of an export after the song's title, and a song
; nobody has named is exported as Untitled: two of those in one build is the
; same label twice and the assembler stops.  A module puts a prefix on all of
; them, and the tune's own address is the label outside it.
;
; It is the Spectrum's because there is nothing machine-dependent here.

                DEVICE  ZXSPECTRUM128

                DEFINE PLY_AKM_HARDWARE_SPECTRUM 1

                ORG     $8000
start:
                di
                ld      sp, $7FF0
                call    music_init
                call    interrupt_init
                ld      a, (tune_wanted)
                call    music_start
                ei
                ld      a, $FF
                ld      (playing_flag), a
.count:
                ld      hl, (spins)
                inc     hl
                ld      (spins), hl
                ld      a, (tune_asked)
                inc     a                       ; $FF is nothing asked for
                jr      z, .count
                dec     a
                ld      (tune_wanted), a
                ld      hl, tune_asked
                ld      (hl), $FF
                ld      a, (tune_wanted)
                call    music_start
                jr      .count

playing_flag:   db      0
spins:          dw      0
tune_wanted:    db      0               ; the one it started with
tune_asked:     db      $FF             ; poked by the test

                include "../common/music.asm"
                include "../arkos/PlayerAkm.asm"
                include "interrupt.asm"

; The list of tunes, and the tunes: the author's music, which is not this
; project's to carry.  See music/.
music_tunes:
                MUSIC_TUNE first, first_end, 0
                MUSIC_TUNE second, second_end, 0
music_tunes_end:

first:
                MODULE  song_one
                include "../../music/test.asm"
                ENDMODULE
first_end:

second:
                MODULE  song_two
                include "../../music/test.asm"
                ENDMODULE
second_end:
last:
                ASSERT  last <= IM2_TABLE

                SAVESNA "tunes.sna", start
