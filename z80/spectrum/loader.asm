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

                include "basic.asm"

DATA_BLOCK      equ $FF
; The ROM's own tape read.  tape.asm knows it by another name for saving a
; game, and the two are kept apart on purpose: a build may have either.
LOADER_LD_BYTES equ $0556

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
                call    LOADER_LD_BYTES
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

                include "blocks.asm"
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
