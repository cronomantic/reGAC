; MIT License, Copyright (c) 2025 Cronomantic
;
; Saving and loading a game on a Spectrum Next, which is a Spectrum doing it.
;
; The ROM does the work, exactly as it does on a 48K: one block of the kind a
; BASIC program would call data, with no header in front of it, so loading is
; reading whatever comes next.  What travels is the game alone, from vm_state
; to vm_state_end, because the adventure never changes.
;
; What is this machine's own is two things.  The ROM is not in the machine:
; the first sixteen kilobytes are the window a bank of the database appears
; in, so the ROM is brought back for as long as the routine takes and the
; window is put back afterwards -- paging.asm does both.  And the processor is
; not running at the speed the ROM counts in: a tape is written and read by
; counting clock cycles, so the machine goes back to three and a half
; megahertz while it happens and to twenty eight afterwards.
;
; Everything else is the Spectrum's:
; the system variables are left free at $5C00 for this and nothing else, the
; interrupts are off, which is how the interpreter runs anyway, and the block
; itself lives up with the code where no paging reaches it.

ROM_SA_BYTES    equ $04C2
ROM_LD_BYTES    equ $0556
SYSTEM_VARS     equ $5C3A
TURBO_35        equ 0                   ; and the speed the ROM was written for

; Put the block at IX, DE bytes of it, on the tape.
; Corrupts: everything
tape_save:
                di
                nextreg REG_TURBO, TURBO_35
                call    the_rom_back
                push    iy
                ld      iy, SYSTEM_VARS
                ld      a, $FF                  ; a block of data, not a header
                call    ROM_SA_BYTES
                pop     iy
                di
                call    the_window_back
                nextreg REG_TURBO, TURBO_28
                ret

; Read a block of DE bytes back into IX.  Carry set when it came in whole.
; Corrupts: everything
tape_load:
                di
                nextreg REG_TURBO, TURBO_35
                call    the_rom_back
                push    iy
                ld      iy, SYSTEM_VARS
                ld      a, $FF
                scf                             ; load it, rather than compare
                call    ROM_LD_BYTES
                pop     iy
                di
                push    af                      ; what it said of itself
                call    the_window_back
                nextreg REG_TURBO, TURBO_28
                pop     af
                ret
