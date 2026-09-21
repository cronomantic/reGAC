; MIT License, Copyright (c) 2025 Cronomantic
;
; Paging on a Spectrum Next, which has eight windows and not one.
;
; Any eight kilobytes of the machine's memory can be shown in any of the eight
; slots, by writing the page into the register that owns the slot.  A bank of
; the database is sixteen kilobytes, so it is two pages and they go into the
; two slots the window at $0000 is made of.
;
; The database numbers its banks from zero and knows nothing about this
; machine; the table below says which of its pages each one starts at.  The
; names come from the build, which puts the data in those same pages, so there
; is only one list and not two.

DB_WINDOW       equ $0000
MMU0            equ $50
MMU1            equ $51
ROM_BACK        equ $FF                 ; what a slot is given to show the ROM

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
                ld      hl, db_paged
                cp      (hl)
                jr      z, .already
                ld      (hl), a
                nextreg MMU0, a
                inc     a
                nextreg MMU1, a
.already:
                pop     hl
                ret

db_paged:       db      $FF             ; nothing has been asked for yet

; The 48K ROM back where it always was, and then the window again.  This is
; for the tape: the ROM is the only thing on this machine that knows how to
; talk to one, and it expects to be at $0000 while it does.
; Corrupts: AF
the_rom_back:
                ld      a, ROM_BACK
                nextreg MMU0, a
                nextreg MMU1, a
                ret

; And ours, whichever bank was in the window before the ROM took its place.
; Corrupts: AF
the_window_back:
                ld      a, (db_paged)
                cp      $FF
                ret     z                       ; nothing was in it
                nextreg MMU0, a
                inc     a
                nextreg MMU1, a
                ret

