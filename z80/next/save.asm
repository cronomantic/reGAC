; MIT License, Copyright (c) 2025 Cronomantic
;
; Saving and loading a game on a Spectrum Next, in a file on its card.
;
; The game, and not the adventure, in one file: what travels is vm_state to
; vm_state_end, because the adventure never changes.  The file is the
; project's name with .SAV for its last part -- MEGACORP.SAV beside
; megacorp.nex -- and the build says which, with SAVE_NAME; a build nobody
; told calls it GAME.SAV.  No name is asked for, as none is on the 6128, the
; PCW or the PC: the original saved one block and said nothing.  The name has
; no folder in it, so it goes wherever the machine is standing, which is the
; folder the .nex was started from.
;
; A .nex is only ever started by the Next's own system, NextZXOS, and that
; answers the calls esxDOS answered on the Spectrums before it: RST $08 and a
; byte after it that says which.  Two things of this machine's own:
;
; - The first sixteen kilobytes are the window a bank of the database appears
;   in, and the system only takes the call when the ROM is there -- without
;   it the machine is lost at SAVE, seen on NextZXOS booted off its card -- so
;   the ROM is brought back for as long as the calls take and the window put
;   back afterwards.  paging.asm does both.
; - A load is read into a place of its own first, and only copied over the
;   game once all of it has come: one that goes wrong -- no file, or less of
;   it than a game -- leaves the game as it was.  The place is the free
;   memory at $4000, where a Spectrum keeps its screen and this machine does
;   not.
;
; The interrupts stay off, which is how the interpreter runs anyway.

F_OPEN          equ $9A
F_CLOSE         equ $9B
F_READ          equ $9D
F_WRITE         equ $9E
FA_READ         equ $01
FA_WRITE        equ $02
FA_CREATE_AL    equ $0C                 ; made anew, whatever was there
DRIVE_CURRENT   equ '*'
LOAD_AREA       equ $4000

; Put the block at IX, DE bytes of it, in the file.  Carry set when all of it
; was written.
; Corrupts: everything
tape_save:
                ld      (save_block), ix
                ld      (save_length), de
                call    system_in
                ld      b, FA_WRITE | FA_CREATE_AL
                call    save_open
                jr      c, .failed
                ld      ix, (save_block)
                ld      bc, (save_length)
                rst     $08
                db      F_WRITE
                call    save_close              ; and whether all went out
                jp      system_out
.failed:
                or      a                       ; it did not
                jp      system_out

; Read a block of DE bytes back into IX.  Carry set when it came in whole;
; when it did not, what is at IX is as it was.
; Corrupts: everything
tape_load:
                ld      (save_block), ix
                ld      (save_length), de
                call    system_in
                ld      b, FA_READ
                call    save_open
                jr      c, .failed
                ld      ix, LOAD_AREA
                ld      bc, (save_length)
                rst     $08
                db      F_READ
                call    save_close
                jr      nc, .failed
                ld      hl, LOAD_AREA           ; all of it: over the game
                ld      de, (save_block)
                ld      bc, (save_length)
                ldir
                scf
                jp      system_out
.failed:
                or      a                       ; it did not
                jp      system_out

; Open the file, in the way B says.  Carry set, as the system sets it, when
; it would not open.
; Corrupts: everything
save_open:
                ld      a, DRIVE_CURRENT
                ld      ix, save_name
                rst     $08
                db      F_OPEN
                ret     c
                ld      (save_handle), a
                ret

; After a read or a write: BC is what went, carry is the system's word on it.
; Close the file and say, with carry set, whether all of it went and nothing
; was wrong.
; Corrupts: everything
save_close:
                push    af
                push    bc
                ld      a, (save_handle)
                rst     $08
                db      F_CLOSE
                pop     bc
                pop     af
                ccf
                ret     nc                      ; the system said no
                ld      hl, (save_length)
                or      a
                sbc     hl, bc
                ret     nz                      ; less of it than a game
                scf
                ret

; The machine as the system wants it: the ROM where the window is.
; Corrupts: AF
system_in       equ the_rom_back

; And ours again, carry kept.
; Corrupts: nothing
system_out:
                di
                push    af
                call    the_window_back
                pop     af
                ret

save_name:
                IFDEF   SAVE_NAME
                db      SAVE_NAME, 0
                ELSE
                db      "GAME.SAV", 0
                ENDIF
save_block:     dw      0
save_length:    dw      0
save_handle:    db      0
