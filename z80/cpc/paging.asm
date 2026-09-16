; MIT License, Copyright (c) 2025 Cronomantic
;
; Paging on a 6128, which is the only Amstrad of these that has any.
;
; The gate array's RAM register takes a byte at any port whose high byte is
; $7F, and of the eight arrangements it knows only four are wanted here: $C4
; to $C7 each swap the sixteen kilobytes at $4000 for one of the four banks
; of the second sixty four and leave the rest of the map alone.  So the
; window is at $4000, which is why the interpreter lives above it and not
; where it does on a 464.
;
; The database numbers its banks from zero and knows nothing about this
; machine; the table below says which arrangement each one is.  The names
; come from the build, which puts the data in those same banks, so there is
; one list and not two.

DB_WINDOW       equ $4000
PAGE_PORT       equ $7F00               ; any port with that high byte
PAGE_NONE       equ 0                   ; no arrangement is this, so it means
                                        ; that nothing has gone out yet

db_pages:       db      DB_PAGE_0, DB_PAGE_1, DB_PAGE_2, DB_PAGE_3

; Bring bank A into the window.  Doing nothing when it is already there is
; worth the look, as it is on the Spectrum: a picture asks for its bank once
; a room and a message asks for another one line at a time.
; Corrupts: AF
db_page:
                push    hl
                push    bc
                ld      hl, db_pages
                add     a, l
                ld      l, a
                jr      nc, .found
                inc     h
.found:
                ld      a, (hl)
                ld      hl, db_paged
                cp      (hl)
                jr      z, .already
                ld      (hl), a
                ld      b, PAGE_PORT >> 8
                ld      c, a
                out     (c), c
.already:
                pop     bc
                pop     hl
                ret

db_paged:       db      PAGE_NONE
