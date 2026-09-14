; MIT License, Copyright (c) 2025 Cronomantic
;
; Talking to a cassette on an MSX, which means borrowing the BIOS back.
;
; The interpreter runs with RAM in all four pages, so the BIOS is not there any
; more -- and the BIOS is the only thing on this machine that knows how to talk
; to a cassette.  So for as long as a save takes, the map the machine came with
; goes back, the routines are called, and the machine is taken again; slots.asm
; does that part.  What travels is the game alone, which lives up here with the
; code and is not touched by any of it.
;
; Nothing needs putting back afterwards, which is worth saying because the
; Amstrad's firmware does need it: these routines leave the video chip exactly
; as they found it, display on and registers untouched.  That was watched on
; the machine, with a screen up and a block written over it, and not assumed.
;
; The six entries are the ones every MSX has at the same addresses:
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



; Find the lead and get in step.  Carry set when nothing came.
; Corrupts: AF
start_reading:
                push    bc
                push    de
                push    hl
                push    ix
                call    TAPION
                jr      tape_done
; Stop the motor.  The interrupts come back on with it, and they are not
; wanted: the routine that answers them is about to be paged out.
; Corrupts: AF
stop_reading:
                push    bc
                push    de
                push    hl
                push    ix
                call    TAPIOF
                jr      tape_done
; One byte off the cassette, into A.  Carry set when it did not come.
; Corrupts: AF
read_byte:
                push    bc
                push    de
                push    hl
                push    ix
                call    TAPIN
tape_done:
                pop     ix
                pop     hl
                pop     de
                pop     bc
                di
                ret

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
