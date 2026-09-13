; MIT License, Copyright (c) 2025 Cronomantic
;
; A build that draws one picture on an Amstrad and stops, so the tests can
; compare the screen against what the reference renderer says it should be.
;
; There is no snapshot to load here: the test writes these bytes straight into
; a running machine and points the processor at the front of them, which is
; what the disk loader would have done.

                DEVICE  AMSTRADCPC6128

                ; above the lower ROM, which shadows anything under $4000
                ORG     $4000
start:
                di
                ld      sp, $BF00
                call    screen_init
                call    db_init
                call    config_init
                call    picture_init
                ; fall through

; Drawing again needs none of the setting up, so the tests can poke a new
; number in here, clear the flag and point the processor back at this label.
redraw:
                ld      sp, $BF00
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
                include "screen.asm"
                include "draw.asm"
                include "shapes.asm"
                include "fill.asm"
                include "../common/picture.asm"

                ALIGN   256
database:
                INCBIN  "picture.rgac"
last:

                SAVEBIN "picture.bin", start, last - start
