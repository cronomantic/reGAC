; MIT License, Copyright (c) 2025 Cronomantic
;
; A build that saves a block to the disc, rubs it out and reads it back, so a
; test can see that a PCW writes its own sectors and finds them again.
;
; It has to come off a real disk, because what it writes to is the file the
; builder made: where that file starts is in the boot sector, at $F1FC, which
; is still sitting where the machine put it.

                DEVICE  NOSLOT64K

LOCK            equ $F4
UNLOCKED        equ 0
BLOCK           equ $D800               ; clear of the area the disc uses
LENGTH          equ 1000

                ORG     $0100
start:
                di
                ld      sp, $FC00
                ld      a, UNLOCKED
                out     (LOCK), a
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
                ld      a, 1
                ld      (saved_flag), a
                ; rub it out, so that finding it again means something
                ld      hl, BLOCK
                ld      de, BLOCK + 1
                ld      bc, LENGTH - 1
                ld      (hl), 0
                ldir
                ld      ix, BLOCK
                ld      de, LENGTH
                call    tape_load
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

saved_flag:     db      0
done_flag:      db      0

                include "disc.asm"
last:

                SAVEBIN "save.bin", start, last - start
