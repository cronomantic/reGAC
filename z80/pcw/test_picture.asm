; MIT License, Copyright (c) 2025 Cronomantic
;
; A build that draws one picture on a PCW and stops, so the tests can compare
; the screen against what the reference renderer says it should be.
;
; It takes the machine as it comes out of its own loader: interrupts off, the
; banks unlocked so they can be moved, and a stack of our own under the screen.

                DEVICE  NOSLOT64K

LOCK            equ $F4
UNLOCKED        equ 0

                ORG     $0100
start:
                di
                ld      sp, $FC00
                ld      a, UNLOCKED             ; the banks are ours to move
                out     (LOCK), a
                call    db_init
                call    config_init
                call    text_init
                call    screen_init
                call    picture_init
                ; fall through

; Drawing again needs none of the setting up, so the tests can poke a new
; number in here, clear the flag and point the processor back at this label.
redraw:
                ld      sp, $FC00
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
                include "../common/textout.asm"
                include "draw.asm"
                include "../common/shapes.asm"
                include "fill.asm"
                include "../common/picture.asm"

                ALIGN   256
database:
                INCBIN  "picture.rgac"
last:

                SAVEBIN "picture.bin", start, last - start
