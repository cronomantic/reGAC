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

; With -DLOW_CODE this is built the way an adventure whose database leaves no
; room above $4000 is built: the code under it and an island up by the
; firmware, because the tape routines bring the lower ROM back while they run.
; What the two directions do then is the copying up and back, which is what
; there is to watch.  A test pokes a starter above $4000 to put the ROMs out
; of the way and jump down here, which is what the real loader's does.
                IFDEF LOW_CODE
ISLAND_AT       equ $AB00
FIRMWARE_AT     equ $B100
                ORG     $0400
                ELSE
                ; above the lower ROM, which covers anything under $4000
                ORG     $4000
                ENDIF
start:
                di
                ld      sp, $BF00
                IFDEF LOW_CODE
                call    island_init
                ENDIF
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
; The block stands in for a game: in a low build tape.asm copies from here up
; to the island and back, and how much it copies is what these two say.
vm_state:
block:
                ; something recognisable to write
                db      0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15
                db      16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31
                db      32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47
                db      48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63
load_area:      ds      LOAD_LEN
vm_state_end:

                include "../common/database.asm"
                include "../common/config.asm"
                include "../common/unpack.asm"
                include "screen.asm"
                include "../common/textout.asm"
                include "tape.asm"

                IFDEF LOW_CODE
; The database is a file of its own here too, put at $4000 by whoever starts
; this, so what is saved is the code alone.
last:
database        equ $4000
                ASSERT  last <= database        ; or the database lands on it
                ELSE
                ALIGN   256
database:
                INCBIN  "text.rgac"
last:
                ENDIF

                SAVEBIN "tape.bin", start, last - start
