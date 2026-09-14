; MIT License, Copyright (c) 2025 Cronomantic
;
; What a real Spectrum gets: a tape, not a snapshot.
;
; The tape is a BASIC program and then the blocks of the adventure with no
; header in front of them.  The trick, which is the usual one, is that the
; loader itself travels inside the BASIC program: line 0 is a REM and the
; machine code sits in it, so loading the BASIC loads the loader.  Line 10
; clears below the interpreter and calls it.
;
; What the loader does is walk a table of blocks -- where each one goes, how
; long it is, and on a 128 which page it goes in -- asking the ROM for each.
; A block that does not come in whole starts the machine again, which is what
; the original did too.
;
; The table is built here from what the build said, so a 48 has one block and
; a 128 has one plus a page each for the banks.

BASIC_START     equ 23755               ; where a BASIC program begins
DATA_BLOCK      equ $FF                 ; ROM_LD_BYTES is in tape.asm, which
                                        ; is where the ROM's tape calls live
TOKEN_REM       equ 234
TOKEN_CLEAR     equ 253
TOKEN_RANDOMIZE equ 249
TOKEN_USR       equ 192
NUMBER_MARK     equ 14                  ; what hides a number after its digits
ENTER           equ 13

                ORG     BASIC_START
basic:
; Line 0, a REM with the loader inside it.  Nobody is meant to read it.
                db      0, 0                    ; the line number, high first
                dw      line0_end - line0
line0:
                db      TOKEN_REM
loader:
                di
                ld      sp, start               ; below the interpreter
                IFDEF BANKED
                ld      a, PAGE_FIXED           ; the 48K ROM, so that the
                call    loader_page             ; call below is the ROM's
                ENDIF
                ld      hl, load_table
.each:
                ld      c, (hl)
                inc     hl
                ld      b, (hl)
                inc     hl                      ; BC = where the block goes
                ld      a, b
                or      c
                jr      z, .run                 ; nowhere, so that was the last
                ld      e, (hl)
                inc     hl
                ld      d, (hl)
                inc     hl                      ; DE = how many bytes
                IFDEF BANKED
                ld      a, (hl)
                inc     hl
                or      PAGE_FIXED
                call    loader_page             ; the page it goes in
                ENDIF
                push    bc
                pop     ix
                push    hl
                ld      a, DATA_BLOCK
                scf                             ; load it, rather than compare
                call    ROM_LD_BYTES
                pop     hl
                jr      c, .each
                jp      0                       ; it came in wrong: start again
.run:
                IFDEF BANKED
                ld      a, PAGE_FIXED           ; a known page in the window
                call    loader_page
                ENDIF
                jp      start

                IFDEF BANKED
; Put A out of the paging port, keeping our place in the table.
; Corrupts: AF
loader_page:
                push    bc
                ld      bc, PAGE_PORT
                out     (c), a
                pop     bc
                ret
                ENDIF

; Where each block goes, how long it is, and on a 128 which page.  A block
; that goes nowhere ends it.
load_table:
                dw      start
                dw      last - start
                IFDEF BANKED
                db      2               ; the interpreter's own page, always in
                IF DB_BANK_COUNT > 0
                dw      DB_WINDOW
                dw      DB_BANK_USED_0
                db      DB_PAGE_0
                ENDIF
                IF DB_BANK_COUNT > 1
                dw      DB_WINDOW
                dw      DB_BANK_USED_1
                db      DB_PAGE_1
                ENDIF
                IF DB_BANK_COUNT > 2
                dw      DB_WINDOW
                dw      DB_BANK_USED_2
                db      DB_PAGE_2
                ENDIF
                IF DB_BANK_COUNT > 3
                dw      DB_WINDOW
                dw      DB_BANK_USED_3
                db      DB_PAGE_3
                ENDIF
                IF DB_BANK_COUNT > 4
                dw      DB_WINDOW
                dw      DB_BANK_USED_4
                db      DB_PAGE_4
                ENDIF
                IF DB_BANK_COUNT > 5
                dw      DB_WINDOW
                dw      DB_BANK_USED_5
                db      DB_PAGE_5
                ENDIF
                ENDIF
                dw      0
                db      ENTER
line0_end:

; Line 10: clear below the interpreter and call the loader.  The numbers are
; written as a full stop because what the machine reads is the five bytes
; after it, not the digits, and those come from the labels themselves.
line10:
                db      0, 10
                dw      line10_end - line10_body
line10_body:
                db      TOKEN_CLEAR
                db      '.', NUMBER_MARK, 0, 0
                dw      start - 1
                db      0
                db      ':'
                db      TOKEN_RANDOMIZE
                db      TOKEN_USR
                db      '.', NUMBER_MARK, 0, 0
                dw      loader
                db      0
                db      ENTER
line10_end:
basic_end:
