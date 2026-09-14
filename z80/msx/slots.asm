; MIT License, Copyright (c) 2025 Cronomantic
;
; Which slot each page of memory shows, which on this machine is the whole of
; paging: four pages, two bits each, in one port.
;
; The interpreter runs with RAM in all four of them, so that a database and an
; interpreter both fit; the BIOS is then not there at all.  That is fine until
; something is wanted of the BIOS -- a cassette is the only such thing here --
; and then the map it came with goes back for as long as the routine takes.
;
; What is never done is coming back to our own map with the interrupts on.  An
; interrupt then is a jump to $0038, which by then is the database, and the
; machine is gone in a moment; so the way back turns them off itself.

PPI_SLOTS       equ $A8                 ; two bits a page: which slot it sees

; Put RAM in all four pages, and remember both maps: the one the machine had,
; which is the one the BIOS is in, and ours.  Which slot the RAM is in is not
; assumed -- it is the one pages two and three are already showing, because
; that is where a machine of this size keeps it.
; Corrupts: AF, C
take_the_machine:
                in      a, (PPI_SLOTS)
                ld      (bios_slots), a
                and     %00110000               ; the slot page two is in
                rrca
                rrca
                rrca
                rrca
                ld      c, a
                add     a, a
                add     a, a
                or      c                       ; the same in pages nought and one
                ld      c, a
                ld      a, (bios_slots)
                and     %11110000
                or      c
                ld      (our_slots), a
                out     (PPI_SLOTS), a
                ret

; The two low pages back to the slot the BIOS is in, and then ours again.
; Which slot that is was noted when the machine was taken.
; Corrupts: AF
the_bios_back:
                ld      a, (bios_slots)
                out     (PPI_SLOTS), a
                ret

the_machine_back:
                di                              ; before the BIOS goes away
                ld      a, (our_slots)
                out     (PPI_SLOTS), a
                ret

bios_slots:     db      0
our_slots:      db      0
