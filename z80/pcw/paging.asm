; MIT License, Copyright (c) 2025 Cronomantic
;
; Paging on the PCW, which is four windows of sixteen kilobytes and a port for
; each.  The database gets the second of them, from $4000: the first holds the
; interpreter, the third is whichever half of the screen is in use, and the
; fourth the mask, the stack and the tables.
;
; The port cannot be read back, so the last value is kept here.  A bank number
; is given to the machine with bit seven on, which is what BANK_MARK is.
;
; The database numbers its banks from zero and knows nothing about this
; machine; the table below says which of the machine's own banks each one
; becomes.  The names come from the build, which is also what tells the loader
; where to put them, so there is only one list and not two.

DB_WINDOW       equ $4000
DB_SLOT         equ $F1                 ; the port for that window

db_pages:       db      DB_PAGE_0, DB_PAGE_1, DB_PAGE_2
                db      DB_PAGE_3, DB_PAGE_4, DB_PAGE_5

; Bring bank A into the window.  Doing nothing when it is already there is
; worth the look: a picture asks for its bank once a room and a message asks
; for another one line at a time.
; Corrupts: AF
db_page:
                push    hl
                ld      hl, db_pages
                add     a, l
                ld      l, a
                jr      nc, .found
                inc     h
.found:
                ld      a, (hl)
                or      BANK_MARK
                ld      hl, db_paged
                cp      (hl)
                jr      z, .already
                ld      (hl), a
                out     (DB_SLOT), a
.already:
                pop     hl
                ret

db_paged:       db      $FF             ; nothing has been asked for yet
