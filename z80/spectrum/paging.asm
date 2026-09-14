; MIT License, Copyright (c) 2025 Cronomantic
;
; Paging on the 128, which is the only Spectrum that has any.
;
; There is a single window, from $C000, and the byte that chooses what appears
; there goes out of a port that cannot be read back, so the last value is kept
; here.  Bit four asks for the 48K ROM and bit three for the screen in page 5,
; which is where it is; neither of them ever changes.
;
; The database numbers its banks from zero and knows nothing about this
; machine; the table below says which of the machine's own pages each one
; becomes.  The names come from the build, which puts the data in those same
; pages, so there is only one list and not two.

DB_WINDOW       equ $C000
PAGE_PORT       equ $7FFD
PAGE_FIXED      equ %00010000           ; the 48K ROM, and the screen in five

db_pages:       db      DB_PAGE_0, DB_PAGE_1, DB_PAGE_2
                db      DB_PAGE_3, DB_PAGE_4, DB_PAGE_5

; Bring bank A into the window.  Doing nothing when it is already there is
; worth the look: a picture asks for its bank once a room and a message asks
; for another one line at a time.
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
                or      PAGE_FIXED
                ld      hl, db_paged
                cp      (hl)
                jr      z, .already
                ld      (hl), a
                ld      bc, PAGE_PORT
                out     (c), a
.already:
                pop     bc
                pop     hl
                ret

db_paged:       db      $FF             ; nothing has been asked for yet
