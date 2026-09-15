; MIT License, Copyright (c) 2025 Cronomantic
;
; A build that runs the high priority conditions of whatever database is
; alongside it and then stops, so the tests can read the flags, the counters
; and where the player ended up.
;
; With -DWITH_MUSIC it is built again on a 128, with the music in it, and then
; the three opcodes that need a sound chip do something rather than nothing.
; The conditions are run once and the build stops; the music goes on playing
; from the interrupt while it stops, which is the whole point of it.

                IFDEF WITH_MUSIC
                DEVICE  ZXSPECTRUM128
                DEFINE  PLY_AKM_HARDWARE_SPECTRUM 1
                DEFINE  PLY_AKM_MANAGE_SOUND_EFFECTS 1
                ELSE
                DEVICE  ZXSPECTRUM48
                ENDIF

                ORG     $8000
start:
                di
                ld      sp, $7FF0
                xor     a
                out     ($FE), a
                call    db_init
                call    config_init
                call    text_init
                call    screen_init
                call    vm_init
                IFDEF WITH_MUSIC
                call    music_init
                ld      hl, effects
                call    sound_init
                call    interrupt_init
                ENDIF
                ; the player starts where the config says
                ld      a, SECTION_CONFIG
                call    db_section
                ld      e, (hl)
                inc     hl
                ld      d, (hl)
                ld      (vm_location), de

                ld      a, SECTION_CONDITIONS
                call    db_section
                push    hl
                ld      e, (hl)
                inc     hl
                ld      d, (hl)                 ; where the high priority ones are
                pop     hl
                add     hl, de
                call    run_conditions

                ld      a, $FF
                ld      (done_flag), a
.stop:
                jr      .stop

done_flag:      db      0

                include "../common/database.asm"
                include "../common/config.asm"
                include "../common/unpack.asm"
                include "screen.asm"
                include "../common/textout.asm"
                include "keyboard.asm"
                include "tape.asm"
                include "../common/conditions.asm"
                include "draw.asm"
                include "../common/shapes.asm"
                include "fill.asm"
                include "../common/opcodes.asm"
                include "../common/picture.asm"

                IFDEF WITH_MUSIC
                include "../common/music.asm"
                include "../arkos/PlayerAkm.asm"
                include "interrupt.asm"

; The list of tunes and the music itself, which is the author's and not this
; project's to carry.  See music/.
music_tunes:
                MUSIC_TUNE tune, 0
music_tunes_end:
tune:
                include "../../music/test.asm"
effects:
                include "../../music/effects.asm"
                ENDIF

                ALIGN   256
database:
                INCBIN  "conditions.rgac"

                IFDEF WITH_MUSIC
last:
                ASSERT  last <= IM2_TABLE
                SAVESNA "conditions_music.sna", start
                ELSE
                SAVESNA "conditions.sna", start
                ENDIF
