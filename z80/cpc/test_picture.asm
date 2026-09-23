; MIT License, Copyright (c) 2025 Cronomantic
;
; A build that draws one picture on an Amstrad and stops, so the tests can
; compare the screen against what the reference renderer says it should be.
;
; There is no snapshot to load here: the test writes these bytes straight into
; a running machine and points the processor at the front of them, which is
; what the disk loader would have done.

                DEVICE  AMSTRADCPC6128
                DEFINE  PICTURE_INKS            ; its pictures carry their inks

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

; Drawing again is asked for with go_flag: a test writes the picture's number,
; clears done_flag and sets go_flag, and the loop the build parks in sees it
; and comes back here.  It used to be asked for by writing this label into the
; program counter while the processor ran, and that is not safe: the emulator
; takes its orders on a thread of its own, and a program counter changed
; between an instruction's first byte and the rest of it finishes the
; instruction with bytes from here.  In the parking loop that instruction can
; be a CALL, whose address then comes out of the LD SP in front of this -- a
; call into the database, which fits what the Next's test caught now and then:
; the processor and the stack both down in the database, and code trampled.
; Asked with this byte instead, ten rounds of that test in a row came out
; clean, and none of them needed asking twice.  A byte of memory has nothing
; in the middle to be caught in.
redraw:
                ld      sp, $BF00
                xor     a
                ld      (go_flag), a
                ld      hl, (picture_wanted)
                call    draw_picture
                ld      a, $FF
                ld      (done_flag), a
.stop:
                ld      a, (go_flag)
                or      a
                jr      z, .stop
                jr      redraw

done_flag:      db      0
go_flag:        db      0
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
