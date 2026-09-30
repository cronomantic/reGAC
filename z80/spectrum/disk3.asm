; MIT License, Copyright (c) 2025 Cronomantic
;
; Saving and loading a game on a Spectrum +3, in a file on its disk.
;
; The +3 is delivered on a disk, and a game goes where the adventure came
; from, as it does on the PCW and the 6128.  Those two write the sectors of a
; file the builder sets aside, because nothing of theirs is left to ask; a +3
; has +3DOS, which its own loader already asks for the adventure, so a game is
; a file like any other: the project's name with .SAV for its last part --
; MEGACORP.SAV beside the rest of Megacorp -- and the build says which, with
; SAVE_NAME; a build nobody told calls it GAME.SAV.  No name is asked for, as
; none is on the other machines: the original saved one block and said
; nothing.  A save makes the file anew, whatever was there.
;
; What travels is vm_state to vm_state_end.  With banks it is in page five,
; which is always in; without them it is in the code, under the window.
; Either way +3DOS reads and writes it without paging anything of ours.  What
; it does want is its own ROM and its own page in the window while it works,
; so both are put in for as long as the calls take -- which is why everything
; here has to be under $C000, see the ASSERT at the end -- and what was there
; is put back afterwards.  With banks that is the page the database had in
; the window, which the interpreter keeps in db_paged because the port cannot
; be read back; without them it is page nought, and BASIC left it in BANKM.
;
; Nothing is said when it goes wrong -- no disk, a disk that is protected or
; full, no game to load -- because the original said nothing either: +3DOS is
; told not to ask its "Retry, Ignore or Cancel?" over the picture, a save
; that did not go comes back with carry clear, and a load is read into a place
; of its own first and only copied over the game once all of it has come, so
; one that fails leaves the game as it was.  The place is in page five too,
; after the game: see LOAD_AREA in game3.asm.
;
                include "dos3.asm"

SYSTEM_VARS     equ $5C3A               ; where IY points for the ROM
SAVE_FILE       equ 0                   ; the number the file is opened as
OPEN_TO_READ    equ $0001               ; B the number, C to read
OPEN_TO_WRITE   equ $0002               ; and to write
MUST_BE_THERE   equ $0002               ; D: an error if it is not; E: no header
MADE_ANEW       equ $0204               ; D: made with no header; E: whatever
                                        ; was there under the name goes

; Put the block at IX, DE bytes of it, in the file.  Carry set when all of it
; was written.
; Corrupts: everything but IY
tape_save:
                push    iy
                call    save_it
                pop     iy
                ret

save_it:
                ld      (save_block), ix
                ld      (save_length), de
                call    dos_in
                ld      bc, OPEN_TO_WRITE
                ld      de, MADE_ANEW
                ld      hl, save_name
                call    DOS_OPEN
                jr      nc, .failed
                ld      b, SAVE_FILE
                ld      c, 0                    ; nothing of it is in the window
                ld      hl, (save_block)
                ld      de, (save_length)
                call    DOS_WRITE
                jr      nc, .abandoned
                ld      b, SAVE_FILE
                call    DOS_CLOSE               ; which is when it is written
                jp      dos_out                 ; and whether it all went
.abandoned:
                ld      b, SAVE_FILE
                call    DOS_ABANDON
.failed:
                or      a                       ; it did not
                jp      dos_out

; Read a block of DE bytes back into IX.  Carry set when it came in whole;
; when it did not, what is at IX is as it was.
; Corrupts: everything but IY
tape_load:
                push    iy
                call    load_it
                pop     iy
                ret

load_it:
                ld      (save_block), ix
                ld      (save_length), de
                call    dos_in
                ld      bc, OPEN_TO_READ
                ld      de, MUST_BE_THERE
                ld      hl, save_name
                call    DOS_OPEN
                jr      nc, .failed
                ld      b, SAVE_FILE
                ld      c, 0
                ld      hl, LOAD_AREA
                ld      de, (save_length)
                call    DOS_READ                ; less of it than a game is
                push    af                      ; carry clear, and so is none
                ld      b, SAVE_FILE
                call    DOS_CLOSE
                pop     af
                call    dos_out                 ; ours again, and then
                ret     nc
                ld      hl, LOAD_AREA           ; all of it: over the game
                ld      de, (save_block)
                ld      bc, (save_length)
                ldir
                scf
                ret
.failed:
                or      a                       ; it did not
                jp      dos_out

; The machine as +3DOS wants it: its own page in the window, its own ROM, the
; ROM's IY, and no questions of its own on the screen.  The same as the
; loader's take_the_banks, but the banks are already given.
; Corrupts: everything, and IY is the ROM's
dos_in:
                di
                ld      iy, SYSTEM_VARS
                IFNDEF  BANKED
                ld      a, (BANKM)              ; to be put back as they were
                ld      (paged_before), a
                ld      a, (BANK678)
                ld      (paged_before + 1), a
                ENDIF
                ld      a, (BANKM)
                and     %11101000
                or      %00000111               ; page seven in the window
                ld      bc, $7FFD
                out     (c), a
                ld      (BANKM), a
                ld      a, (BANK678)
                and     %11111000
                or      %00000100               ; and with that, the +3DOS ROM
                ld      b, $1F
                out     (c), a
                ld      (BANK678), a
                xor     a                       ; nothing asked, nothing said
                jp      DOS_SET_MESSAGE

; And ours again, carry kept: the motor off, the 48K ROM, and the page the
; database had in the window -- or, before it has had one, the one the loader
; left there.
; Corrupts: everything but AF
dos_out:
                push    af
                call    DOS_OFF_MOTOR
                IFDEF   BANKED
                ld      a, (BANK678)
                res     0, a
                set     2, a
                ELSE
                ld      a, (paged_before + 1)
                ENDIF
                ld      bc, $1FFD
                out     (c), a
                ld      (BANK678), a
                IFDEF   BANKED
                ld      a, (db_paged)
                cp      $FF
                jr      nz, .paged
                ld      a, (BANKM)
                set     4, a                    ; the 48K ROM, page seven
.paged:
                ELSE
                ld      a, (paged_before)
                ENDIF
                ld      b, $7F
                out     (c), a
                ld      (BANKM), a
                pop     af
                di                              ; whatever +3DOS did with them
                ret

save_name:
                IFDEF   SAVE_NAME
                db      SAVE_NAME, NAME_END
                ELSE
                db      "GAME.SAV", NAME_END
                ENDIF
save_block:     dw      0
save_length:    dw      0
                IFNDEF  BANKED
paged_before:   db      0, 0                    ; BANKM and BANK678, as found
                ENDIF
                ; Page seven is in the window for as long as +3DOS works, so
                ; nothing it comes back to may be there.
                ASSERT  $ <= $C000
