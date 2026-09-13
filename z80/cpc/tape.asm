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
                ; and on into putting the screen back

; The firmware leaves the machine as it likes it, so take it back: interrupts
; off, our mode, and the pens the picture on the screen was drawn with.
back:
                di
                push    af
                call    mode_init
                pop     af
                ret
