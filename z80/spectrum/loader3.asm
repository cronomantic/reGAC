; MIT License, Copyright (c) 2025 Cronomantic
;
; What a Spectrum +3 gets: a disk, and its own menu to start it.
;
; A +3 with a disk in it offers Loader as the first thing on its menu, and
; what Loader runs is the BASIC program called DISK.  So this is that program:
; line 0 is a REM with the loader inside it and line 10 calls it, the same
; trick as the tape's.
;
; From there it is +3DOS that does the work.  One file with no header in front
; of it is opened and read in pieces, and the pieces go where the same table
; the tape loader reads says -- the interpreter at $8000, and then a bank at a
; time into the window.  +3DOS pages each bank itself when it is told which
; one, which is why there is no paging here at all.
;
; What it does have to do first is ask +3DOS to let go.  Of the eight banks it
; keeps one for itself, the seventh, and holds the odd ones for its RAM disk
; and its cache; SET 1346 is how it is told to keep the cache and give the
; rest back.  That leaves nought, one, three and four for the adventure, which
; is what the build hands out.

                include "basic.asm"

DOS_OPEN        equ $0106
DOS_CLOSE       equ $0109
DOS_READ        equ $0112
DOS_SET_1346    equ $013F
DOS_OFF_MOTOR   equ $019C

BANKM           equ $5B5C               ; what was last sent out of $7FFD
BANK678         equ $5B67               ; and out of $1FFD
NAME_END        equ $FF                 ; what a name ends with here

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
                call    take_the_banks
                ld      bc, $0001               ; file nought, opened to read
                ld      de, $0002               ; it must be there, and it has
                ld      hl, filename            ; no header in front of it
                call    DOS_OPEN
                jr      nc, .again
                ld      hl, load_table
.each:
                ld      e, (hl)
                inc     hl
                ld      d, (hl)
                inc     hl                      ; DE = where the block goes
                ld      a, d
                or      e
                jr      z, .done                ; nowhere, so that was the last
                ld      c, (hl)
                inc     hl
                ld      b, (hl)
                inc     hl                      ; BC = how many bytes
                ld      a, (hl)
                inc     hl                      ; and which page it goes in
                push    hl
                ex      de, hl
                ld      e, c
                ld      d, b
                ld      c, a
                ld      b, 0                    ; file nought, into page C
                call    DOS_READ
                pop     hl
                jr      c, .each
.again:
                ; Something went wrong and there is nothing to be done about
                ; it, so leave the machine as it was found.
                xor     a
                ld      bc, $7FFD
                out     (c), a
                ld      b, $1F
                out     (c), a
                jp      0
.done:
                ld      b, 0
                call    DOS_CLOSE
                call    DOS_OFF_MOTOR
                call    the_48_rom
                di
                jp      start

; Put the machine the way +3DOS wants it -- its own ROM, and its own page in
; the window -- and then ask it for the banks back: no RAM disk at all, and
; four kilobytes of cache at the top of bank six.
; Corrupts: everything
take_the_banks:
                ld      a, (BANKM)
                and     %11101000
                or      %00000111               ; page seven in the window
                ld      bc, $7FFD
                out     (c), a
                ld      (BANKM), a
                ld      a, (BANK678)
                and     %11111000
                or      %00000100               ; and with that, the +3DOS ROM
                ld      b, $1F
                out     (c), a
                ld      (BANK678), a
                ld      hl, $7800               ; nothing kept for a RAM disk
                ld      de, $7E02               ; and the cache in bank six
                jp      DOS_SET_1346

; And put it back the way the interpreter wants it: the 48K ROM, which is
; where the tape routines it saves a game with live.
; Corrupts: everything
the_48_rom:
                ld      a, (BANKM)
                set     4, a
                ld      bc, $7FFD
                out     (c), a
                ld      (BANKM), a
                ld      a, (BANK678)
                res     0, a
                set     2, a
                ld      b, $1F
                out     (c), a
                ld      (BANK678), a
                ret

filename:
                db      "GAME", NAME_END

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
