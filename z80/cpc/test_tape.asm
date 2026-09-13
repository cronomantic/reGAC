; MIT License, Copyright (c) 2025 Cronomantic
;
; A build that puts a block on the tape, or takes one off it, so a test can
; see that the firmware takes the machine and hands it back the way it was:
; our mode, our pens, and interrupts still off.
;
; Which of the two it does is the byte `wanted`, poked before it is started.

                DEVICE  AMSTRADCPC6128

BLOCK_LEN       equ 64
LOAD_LEN        equ 256

                ; above the lower ROM, which covers anything under $4000
                ORG     $4000
start:
                di
                ld      sp, $BF00
                call    db_init
                call    config_init
                call    text_init
                call    screen_init
                ld      a, 1
                ld      (ready_flag), a
                ld      a, (wanted)
                or      a
                jr      nz, .reading
                ld      ix, block
                ld      de, BLOCK_LEN
                call    tape_save
                jr      .said
.reading:
                ld      ix, load_area
                ld      de, LOAD_LEN
                call    tape_load
.said:
                ld      a, 0
                rla                             ; what it said of itself
                ld      (carry_seen), a
                ld      a, $FF
                ld      (done_flag), a
.stop:
                jr      .stop

wanted:         db      0
ready_flag:     db      0
carry_seen:     db      0
done_flag:      db      0
block:
                ; something recognisable to write
                db      0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15
                db      16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31
                db      32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47
                db      48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63
load_area:      ds      LOAD_LEN

                include "../common/database.asm"
                include "../common/config.asm"
                include "../common/unpack.asm"
                include "screen.asm"
                include "../common/textout.asm"
                include "tape.asm"

                ALIGN   256
database:
                INCBIN  "text.rgac"
last:

                SAVEBIN "tape.bin", start, last - start
