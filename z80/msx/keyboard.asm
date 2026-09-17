; MIT License, Copyright (c) 2025 Cronomantic
;
; Reading the keyboard on an MSX1, which hangs off the same 8255 the Amstrad's
; does: the row wanted goes in the low four bits of port C and its eight keys
; come back on port B, with a bit low while its key is held.
;
; The BIOS has a routine for this and keeps the whole matrix in memory for
; anyone to read, at $FBE5 -- which is where the eleven rows below were
; measured, one key at a time.  None of that is any use once the interpreter
; takes the machine for itself: the BIOS is paged out and its interrupt is not
; running, so nothing is scanning any more.  So this scans.
;
; The top four bits of port C are the cassette motor, the tape output, the key
; click and the caps lamp, and none of them are ours to change; whatever the
; machine had in them when we arrived is what it keeps.

PPI_B           equ $A9                 ; the eight keys of the row chosen
PPI_C           equ $AA                 ; and, in its low half, which row

KEY_ROWS        equ 11
SHIFT_ROW       equ 6                   ; and the bit of it the shift is on
SHIFT_BIT       equ %00000001

KEY_ENTER       equ 13
KEY_DELETE      equ 8
INPUT_MAX       equ 64                  ; as much of a line as is kept

; A fiftieth of a second is about 71600 clock cycles here, and one look at the
; whole keyboard is about 5780, so this many looks fill a frame.
; It was measured, and not guessed as it was at first: a wait like HOLD's with
; nothing pressed, against the processor's own cycle counter.  The guesses were
; out by up to three and a half times, which made a HOLD that long.  A look
; with a key held costs a little more, so a key repeats a little late.
LOOKS_A_FRAME   equ 12
LOOKS_HELD      equ 12                  ; a look with a key held, about 6070

; Take note of what the machine has in the top half of port C, which is not
; ours to change.
; Corrupts: AF
keyboard_init:
                in      a, (PPI_C)
                and     %11110000
                ld      (ppi_top), a
                ret

; Read the eight keys of row A, into A.  A bit high means held.
; Corrupts: AF, C
read_row:
                and     %00001111
                ld      c, a
                ld      a, (ppi_top)
                or      c
                out     (PPI_C), a
                in      a, (PPI_B)
                cpl                             ; now one means held
                ret

ppi_top:        db      0

; Look once at the whole keyboard.  The character comes back in A, and zero
; with the zero flag set when nothing useful is held.
;
; The shifts are passed over rather than reported, or holding one would look
; like nothing being typed at all; what they do is decided afterwards.
; Corrupts: BC, DE, HL
scan_keyboard:
                xor     a
                ld      (key_found), a
                ld      (key_count), a
                ld      hl, key_table
                ld      d, 0                    ; which row
.row:
                push    de
                ld      a, d
                call    read_row
                pop     de
                ld      e, 8
.key:
                rra
                jr      nc, .next_key
                push    af
                ld      a, (hl)
                or      a
                jr      z, .a_shift             ; a shift on its own says nothing
                ld      (key_found), a
                push    hl
                ld      hl, key_count
                inc     (hl)                    ; one more that is not a shift
                pop     hl
.a_shift:
                pop     af
.next_key:
                inc     hl
                dec     e
                jr      nz, .key
                inc     d
                ld      a, d
                cp      KEY_ROWS
                jr      nz, .row
                ld      a, (key_found)
                or      a
                ret     z
                call    shift_held
                ld      a, (key_found)
                ret     z                       ; plain, as it is printed
                call    to_shifted
                or      a
                ret     nz
                ld      a, (key_found)          ; shift says nothing about it
                or      a
                ret

; Whether the shift is held; zero flag clear if it is.
; Corrupts: AF, C
shift_held:
                ld      a, SHIFT_ROW
                call    read_row
                and     SHIFT_BIT
                ret

; What the key in A says with shift held, or nothing.
; Corrupts: AF, C, HL
to_shifted:
                ld      c, a
                ld      hl, shifted_pairs
.each:
                ld      a, (hl)
                or      a
                jr      z, .none
                cp      c
                inc     hl
                ld      a, (hl)
                inc     hl
                jr      nz, .each
                or      a
                ret
.none:
                xor     a
                ret

; Wait for a key to be typed and give it back in A.  What counts as typing one
; is the ROM's rules, in common/keys.asm.
; Corrupts: everything
read_key:
                call    next_key
                push    af                      ; the original clicked at every
                call    beep_click              ; key, and so does this
                pop     af
                ret

; Wait for a key, or for HL fiftieths of a second, whichever comes first.
;
; What is already held when the wait starts does not count, or the enter that
; ended the order would end the wait as well.
; Corrupts: everything
wait_or_key:
                ld      c, 0                    ; nothing let go yet
.each_frame:
                ld      a, h
                or      l
                ret     z                       ; the time went
                dec     hl
                push    hl
                ld      b, LOOKS_A_FRAME
.look:
                push    bc
                call    scan_keyboard
                pop     bc
                or      a
                jr      nz, .something
                ld      c, 1                    ; the keyboard came clear
                jr      .keep_looking
.something:
                ld      a, c
                or      a
                jr      nz, .a_key
.keep_looking:
                djnz    .look
                pop     hl
                jr      .each_frame
.a_key:
                pop     hl
                ret

; Read a line into input_buffer, as this adventure's codes.  The length comes
; back in BC.  What is typed is shown as it goes.
; Corrupts: everything
read_line:
                ld      hl, input_buffer
                ld      (line_ptr), hl
                xor     a
                ld      (line_length), a
.next_key:
                call    read_key
                cp      KEY_ENTER
                jr      z, .finished
                cp      KEY_DELETE
                jr      z, .rub_out
                cp      32
                jr      c, .next_key            ; nothing else is worth having
                ld      b, a
                ld      a, (line_length)
                cp      INPUT_MAX
                jr      nc, .next_key           ; the line is full
                ld      a, b
                call    store_key
                jr      .next_key
.rub_out:
                ld      a, (line_length)
                or      a
                jr      z, .next_key
                dec     a
                ld      (line_length), a
                ld      hl, (line_ptr)
                dec     hl
                ld      (line_ptr), hl
                call    backspace
                jr      .next_key
.finished:
                call    new_line
                ld      a, (line_length)
                ld      c, a
                ld      b, 0
                ld      hl, input_buffer
                ret

; Put the character in A into the line and show it.
; Corrupts: everything
store_key:
                call    ascii_to_code
                cp      NO_CHARACTER
                ret     z                       ; not a character this one has
                ld      hl, (line_ptr)
                ld      (hl), a
                inc     hl
                ld      (line_ptr), hl
                ld      hl, line_length
                inc     (hl)
                jp      print_char

; The eleven rows of eight, in the order the bits come out of each byte, as
; they were measured key by key.  Letters come back in upper case because the
; vocabulary is stored that way; a nought is a key with nothing to say here --
; a shift, a cursor, a function key.
key_table:
                db      '0', '1', '2', '3', '4', '5', '6', '7'
                db      '8', '9', '-', '^', '\', '[', ']', ';'
                db      39, '`', ',', '.', '/', '_', 'A', 'B'
                db      'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J'
                db      'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R'
                db      'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z'
                db      0, 0, 0, 0, 0, 0, 0, 0          ; shift, control, the rest
                db      0, 0, 0, 0, 0, KEY_DELETE, 0, KEY_ENTER
                db      ' ', 0, 0, 0, 0, 0, 0, 0
                db      0, 0, 0, 0, 0, 0, 0, 0          ; the number pad
                db      0, 0, 0, 0, 0, 0, 0, 0

; What a key says with shift held, as far as an adventure ever needs: the
; marks that part one order from the next and have no key of their own.
shifted_pairs:  db      '1', '!'
                db      '/', '?'
                db      ';', ':'
                db      '2', '"'
                db      0

key_found:      db      0
line_ptr:       dw      0
line_length:    db      0
input_buffer:   ds      INPUT_MAX

                include "beep.asm"

                include "../common/keys.asm"
