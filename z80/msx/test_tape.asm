; MIT License, Copyright (c) 2025 Cronomantic
;
; A build that puts a block on the cassette, or takes one off it, so that a
; test can watch the part of it that is this machine's own: the BIOS has to be
; lent back for as long as the routine takes, and taken away again with the
; interrupts off.
;
; Getting that wrong is not a small thing here.  The machine is taken whole
; before either of them is called, exactly as the interpreter runs, so there is
; nothing at $0038 but the database -- and there is no database in this build
; at all.  An interrupt let through would go straight into whatever the memory
; happens to hold, and nothing would ever reach `done_flag`.
;
; Which of the two it does is the byte `wanted`, poked before it is started.

                DEVICE  NOSLOT64K

STACK_AT        equ $EF00
BLOCK_LEN       equ 64

                ORG     $8000
start:
                di
                ld      sp, STACK_AT
                call    take_the_machine
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
                ld      de, BLOCK_LEN
                call    tape_load
.said:
                ld      a, 0
                rla                             ; what it said of itself
                ld      (carry_seen), a
                in      a, (PPI_SLOTS)
                ld      (slots_after), a        ; and whose the machine is now
                ld      a, $FF
                ld      (done_flag), a
.stop:
                jr      .stop

wanted:         db      0
ready_flag:     db      0
carry_seen:     db      0
slots_after:    db      0
done_flag:      db      0

block:
                ; something recognisable to write
                db      0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15
                db      16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31
                db      32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47
                db      48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63
load_area:      ds      BLOCK_LEN

                include "slots.asm"
                include "tape.asm"
last:

                SAVEBIN "tape.bin", start, last - start
