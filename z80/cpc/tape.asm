; MIT License, Copyright (c) 2025 Cronomantic
;
; Saving and loading a game, on the Amstrad's tape.
;
; The firmware does the work, as the ROM does on the Spectrum: one block of
; data with no name and no header in front of it, so loading is reading
; whatever comes next.  What travels is the game alone, from vm_state to
; vm_state_end, because the adventure never changes.
;
; It is the tape and not the disc on purpose.  The thirteen cassette entries
; that open a named file are the ones the disc firmware takes over, and they
; all want a two kilobyte buffer of ours to work in; there is no room for one
; here, with the database reaching up to the screen.  CAS WRITE and CAS READ
; are the two the disc leaves alone, want no buffer, and are the exact pair of
; the Spectrum's.
;
; Nothing has to be paged in.  The jumpblock entry is a restart that brings
; the lower ROM back for as long as the routine takes, even though we run with
; both ROMs out of the way; what it does not do is put the screen back as we
; had it, so the mode and the four pens are set again afterwards.

CAS_WRITE       equ $BC9E               ; HL where, DE how long, A the mark
CAS_READ        equ $BCA1
DATA_MARK       equ $16                 ; what the firmware calls data

                IFDEF LOW_CODE
; In a low build the interpreter is under $4000, and that is exactly where the
; lower ROM comes back while the firmware has the tape: the call would run
; into ROM and the bytes handed over would be read out of it.  So the two
; calls live in the island above the database, with the game beside them, and
; all that happens down here is the carrying up and back.
;
; The island is put there at the start, by island_init: it is ten bytes of
; code twice over and a hole the size of a game, so it travels inside the
; interpreter rather than as a file of its own.  Nothing in it names its own
; address -- the two jumps are the firmware's and the hole is an address
; worked out here -- so it is assembled where it lies and run where it is
; carried, with no displacement to arrange.
STATE_BYTES     equ vm_state_end - vm_state

; Copy the island's two calls up to where they can be made.
; Corrupts: AF, BC, DE, HL
island_init:
                ld      hl, island_image
                ld      de, ISLAND_AT
                ld      bc, ISLAND_CODE
                ldir
                ret

island_image:
.save:
                ld      hl, game_copy
                ld      de, STATE_BYTES
                ld      a, DATA_MARK
                call    CAS_WRITE
                jr      .ours
.load:
                ld      hl, game_copy
                ld      de, STATE_BYTES
                ld      a, DATA_MARK
                call    CAS_READ
; And the machine back to ours before the return, because the return goes
; under $4000.  The firmware puts back the paging **it** believes in, and what
; it believes is that the lower ROM is in: the interpreter never told it
; otherwise, it moves the gate array itself.  So a return from here with its
; idea of the map in force lands in ROM, which is a machine off into the weeds
; -- which is exactly what it did before this.
.ours:
                push    af                      ; what it said of itself
                ld      bc, GATE_ARRAY
                ld      a, MODE_1
                out     (c), a
                pop     af
                ret
.end:
ISLAND_CODE     equ island_image.end - island_image
island_save     equ ISLAND_AT + island_image.save - island_image
island_load     equ ISLAND_AT + island_image.load - island_image
game_copy       equ ISLAND_AT + ISLAND_CODE     ; the hole the game goes in
                ASSERT  game_copy + STATE_BYTES <= FIRMWARE_AT

; Put the block at IX, DE bytes of it, on the tape, by way of the island.
; Carry set when it went.
; Corrupts: everything
tape_save:
                push    ix
                pop     hl
                ld      de, game_copy
                ld      bc, vm_state_end - vm_state
                ldir
                call    island_save
                jr      back

; Read a block of DE bytes back into IX, the same way round.  Carry set when
; it came in whole.
; Corrupts: everything
tape_load:
                push    ix
                pop     de
                push    de
                call    island_load
                pop     de
                jr      nc, back                ; nothing came in to copy back
                push    af
                ld      hl, game_copy
                ld      bc, vm_state_end - vm_state
                ldir
                pop     af
                jr      back
                ELSE
; Put the block at IX, DE bytes of it, on the tape.  Carry set when it went.
; Corrupts: everything
tape_save:
                push    ix
                pop     hl
                ld      a, DATA_MARK
                call    CAS_WRITE
                jr      back

; Read a block of DE bytes back into IX.  Carry set when it came in whole.
; Corrupts: everything
tape_load:
                push    ix
                pop     hl
                ld      a, DATA_MARK
                call    CAS_READ
                ENDIF
                ; and on into putting the screen back

; The firmware leaves the machine as it likes it, so take it back: interrupts
; off, our mode, and the pens the picture on the screen was drawn with.
back:
                di
                push    af
                call    mode_init
                pop     af
                ret
