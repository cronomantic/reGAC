; MIT License, Copyright (c) 2025 Cronomantic
;
; A build that saves a block to the disk, rubs it out and reads it back, so a
; test can see that a 6128 writes its own sectors and finds them again.
;
; It writes to the file the builder made, and it is told where that file is
; the same way the interpreter is: in the three bytes at $8002, which the test
; fills in from the disk's own directory before it starts this.

                DEVICE  AMSTRADCPC6128

BLOCK           equ $9000               ; clear of the area the disk uses
LENGTH          equ 1000

                ORG     $8000
start:
                jr      start_up

save_where:     db      0, 0, 0         ; where disc.asm will look
                ASSERT  save_where == $8002

start_up:
                di
                ld      sp, $BF00
                ld      a, 1
                ld      (started_flag), a
                ; a block nothing else would have made
                ld      hl, BLOCK
                ld      bc, LENGTH
                ld      e, 1
.fill:
                ld      (hl), e
                inc     hl
                inc     e
                dec     bc
                ld      a, b
                or      c
                jr      nz, .fill
                ld      ix, BLOCK
                ld      de, LENGTH
                call    tape_save
                ld      a, 0
                rla                             ; what saving said of itself
                ld      (saved_flag), a
                ; rub it out, so that finding it again means something -- and
                ; rub out the area it went down from as well, or a read that
                ; did nothing at all would hand back what is still lying there
                ld      hl, BLOCK
                ld      de, BLOCK + 1
                ld      bc, LENGTH - 1
                ld      (hl), 0
                ldir
                ld      hl, SAVE_AREA
                ld      de, SAVE_AREA + 1
                ld      bc, SAVE_BYTES - 1
                ld      (hl), 0
                ldir
                ld      ix, BLOCK
                ld      de, LENGTH
                call    tape_load
                ld      a, 0
                rla                             ; and what loading said
                ld      (loaded_flag), a
                ; and see whether it is what went down
                ld      hl, BLOCK
                ld      bc, LENGTH
                ld      e, 1
.check:
                ld      a, (hl)
                cp      e
                jr      nz, .wrong
                inc     hl
                inc     e
                dec     bc
                ld      a, b
                or      c
                jr      nz, .check
                ld      a, $FF
                ld      (done_flag), a
.stop:
                jr      .stop
.wrong:
                ld      a, $EE
                ld      (done_flag), a
                jr      .stop

started_flag:   db      0
saved_flag:     db      0
loaded_flag:    db      0
done_flag:      db      0

                include "disc.asm"
last:
                ASSERT  last <= BLOCK
                ASSERT  BLOCK + LENGTH <= SAVE_AREA

                SAVEBIN "save.bin", start, last - start
