; MIT License, Copyright (c) 2025 Cronomantic
;
; Saving and loading a game on an MSX, which means borrowing the BIOS back.
;
; The interpreter runs with RAM in all four pages, so the BIOS is not there any
; more -- and the BIOS is the only thing on this machine that knows how to talk
; to a cassette.  So for as long as a save takes, the two low pages go back to
; the slot they came from, the routines are called, and the machine is taken
; again.  What travels is the game alone, which lives up here with the code and
; is not touched by any of that.
;
; The five entries are the ones every MSX has at the same addresses:
;
;       $00E1 TAPION   find the lead and get in step, to read
;       $00E4 TAPIN    one byte in
;       $00E7 TAPIOF   and stop
;       $00EA TAPOON   write a lead, A saying long or short
;       $00ED TAPOUT   one byte out
;       $00F0 TAPOOF   and stop

TAPION          equ $00E1
TAPIN           equ $00E4
TAPIOF          equ $00E7
TAPOON          equ $00EA
TAPOUT          equ $00ED
TAPOOF          equ $00F0

LEAD_LONG       equ 1                   ; the lead that goes before a file

; Put the block at IX, DE bytes of it, on the cassette.  Carry set when it
; went.
; Corrupts: everything
tape_save:
                call    the_bios_back
                push    ix
                push    de
                ld      a, LEAD_LONG
                call    TAPOON
                pop     de
                pop     ix
                jr      c, .gave_up
.each:
                ld      a, (ix+0)
                push    ix
                push    de
                call    TAPOUT
                pop     de
                pop     ix
                jr      c, .gave_up
                inc     ix
                dec     de
                ld      a, d
                or      e
                jr      nz, .each
                call    TAPOOF
                call    the_machine_back
                scf
                ret
.gave_up:
                call    TAPOOF
                call    the_machine_back
                or      a
                ret

; Read the block back into IX, DE bytes of it.  Carry set when it came.
; Corrupts: everything
tape_load:
                call    the_bios_back
                push    ix
                push    de
                call    TAPION
                pop     de
                pop     ix
                jr      c, .gave_up
.each:
                push    ix
                push    de
                call    TAPIN
                pop     de
                pop     ix
                jr      c, .gave_up
                ld      (ix+0), a
                inc     ix
                dec     de
                ld      a, d
                or      e
                jr      nz, .each
                call    TAPIOF
                call    the_machine_back
                scf
                ret
.gave_up:
                call    TAPIOF
                call    the_machine_back
                or      a
                ret

; The two low pages back to the slot the BIOS is in, and then ours again.
; Which slot that is was noted when the machine was taken.
; Corrupts: AF
the_bios_back:
                ld      a, (bios_slots)
                out     (PPI_SLOTS), a
                ret

the_machine_back:
                ld      a, (our_slots)
                out     (PPI_SLOTS), a
                ret
