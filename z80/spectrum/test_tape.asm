; MIT License, Copyright (c) 2025 Cronomantic
;
; A build that does nothing but put a block on the tape and read one back, so
; a test can watch the two directions of SAVE and LOAD without a whole
; adventure around them.
;
; It waits to be told which of the two to do -- a one for writing, anything
; else for reading -- because a snapshot starts running the moment it is
; loaded and the test wants the tape in place first.

                DEVICE  ZXSPECTRUM48

BLOCK_LEN       equ 64
LOAD_LEN        equ 64

                ORG     $8000
start:
                di
                ld      sp, $7FF0
                ld      a, 1
                ld      (ready_flag), a
.waiting:
                ld      a, (wanted)
                or      a
                jr      z, .waiting
                dec     a
                jr      nz, .reading
                ld      ix, block
                ld      de, BLOCK_LEN
                call    tape_save
                scf                             ; the ROM says nothing of a save
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

                include "tape.asm"
last:

                SAVESNA "tape.sna", start
                SAVEBIN "tape.bin", start, last - start
