; MIT License, Copyright (c) 2025 Cronomantic
;
; A build that plays a tune and fires a sound effect when it is told to, so
; that a test can see an effect laid over the music without either of them
; stopping.
;
; It is the Spectrum's because it may as well be: an effect is played by the
; same player from the same interrupt on every machine, and there is not one
; instruction of this that is this machine's own.
;
; The main loop counts, as the music test's does, and looks at one byte: a
; number poked into it is an effect to fire.  That is as near as a test can
; get to a player deciding to make a noise.

                DEVICE  ZXSPECTRUM128

                DEFINE PLY_AKM_HARDWARE_SPECTRUM 1
                DEFINE PLY_AKM_MANAGE_SOUND_EFFECTS 1

                ORG     $8000
start:
                di
                ld      sp, $7FF0
                call    music_init
                call    interrupt_init
                ld      hl, effects
                call    sound_init
                xor     a                       ; the one tune this has
                call    music_start
                ei
                ld      a, $FF
                ld      (playing_flag), a
.count:
                ld      hl, (spins)
                inc     hl
                ld      (spins), hl
                ld      a, (effect_wanted)
                or      a
                jr      z, .count
                ld      (effect_seen), a
                xor     a
                ld      (effect_wanted), a
                ld      a, (effect_seen)
                call    sound_play
                jr      .count

playing_flag:   db      0
spins:          dw      0
effect_wanted:  db      0               ; poked by the test
effect_seen:    db      0

                include "../common/music.asm"
                include "../arkos/PlayerAkm.asm"
                include "interrupt.asm"

; The list of tunes, one line long here, and then the tune and a handful of
; effects: the author's music, which is not this project's to carry.  See
; music/.
music_tunes:
                MUSIC_TUNE tune, 0
music_tunes_end:
tune:
                include "../../music/test.asm"
effects:
                include "../../music/effects.asm"
last:
                ASSERT  last <= IM2_TABLE

                SAVESNA "sound.sna", start
