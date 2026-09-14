; MIT License, Copyright (c) 2025 Cronomantic
;
; A build that puts a block on the tape, or takes one off it, so that a test
; can watch the part of it that is this machine's own.
;
; On a Spectrum the ROM is simply there; here the first sixteen kilobytes are
; the window a bank of the database appears in, so the ROM has to be brought
; back for as long as the routine takes and the window put back afterwards.
; Both halves are watched: what the ROM said of itself, and what is in the two
; registers that own the window when it is over.
;
; Which of the two it does is the byte `wanted`, poked before it is started.

                DEVICE  ZXSPECTRUMNEXT

REG_TURBO       equ $07                 ; named in screen.asm, which this
TURBO_28        equ 3                   ; build has no other use for
STACK_AT        equ $BF00
BLOCK_LEN       equ 64
WINDOW_PAGE     equ 32                  ; something of ours to put back

                ORG     $8000
start:
                di
                ld      sp, STACK_AT
                ; a page of ours in the window, as the interpreter would have
                ld      a, WINDOW_PAGE
                ld      (db_paged), a
                nextreg MMU0, a
                inc     a
                nextreg MMU1, a
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
                ld      bc, $243B               ; and whose the window is now
                ld      a, MMU0
                out     (c), a
                ld      b, $25
                in      a, (c)
                ld      (mmu0_after), a
                ld      a, $FF
                ld      (done_flag), a
.stop:
                jr      .stop

wanted:         db      0
ready_flag:     db      0
carry_seen:     db      0
mmu0_after:     db      0
done_flag:      db      0

block:
                ; something recognisable to write
                db      0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15
                db      16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31
                db      32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47
                db      48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63
load_area:      ds      BLOCK_LEN

; The paging this build needs, and the tape that uses it.  db_page itself is
; never called here, but the window it remembers is what is put back.
DB_PAGE_0       equ WINDOW_PAGE
DB_PAGE_1       equ WINDOW_PAGE
DB_PAGE_2       equ WINDOW_PAGE
DB_PAGE_3       equ WINDOW_PAGE
DB_PAGE_4       equ WINDOW_PAGE
DB_PAGE_5       equ WINDOW_PAGE
                include "paging.asm"
                include "tape.asm"
last:

; A plain binary and not a .nex: this one is written straight into a machine
; that is already running, because inserting a tape and then loading a file
; over it leaves the tape where nothing can read it.
                SAVEBIN "tape.bin", start, last - start
