; MIT License, Copyright (c) 2025 Cronomantic
;
; A build that draws one picture and stops, so the tests can compare the
; screen against what the reference renderer says it should be.

                DEVICE  ZXSPECTRUM48

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
                call    picture_init
                ; fall through

; Drawing again needs none of the setting up, so the tests can poke a new
; number in here, clear the flag and point the processor back at this label
; instead of loading the snapshot all over again.
redraw:
                ld      sp, $7FF0
                ld      hl, (picture_wanted)
                call    draw_picture
                ld      a, $FF
                ld      (done_flag), a
.stop:
                jr      .stop

done_flag:      db      0
picture_wanted: dw      1

                include "../common/database.asm"
                include "../common/config.asm"
                include "../common/unpack.asm"
                include "screen.asm"
                include "draw.asm"
                include "shapes.asm"
                include "fill.asm"
                include "../common/picture.asm"

                ALIGN   256
database:
                INCBIN  "picture.rgac"

                SAVESNA "picture.sna", start
