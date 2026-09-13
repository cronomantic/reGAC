; MIT License, Copyright (c) 2025 Cronomantic
;
; Reading the keyboard, on the Spectrum.
;
; The matrix is eight half rows of five keys, each read from a port, with a
; bit low while its key is held.  Letters come back in upper case because the
; vocabulary is stored that way, and caps shift with zero rubs a letter out.

CAPS_ROW        equ $FE
KEY_ENTER       equ 13
KEY_DELETE      equ 8
INPUT_MAX       equ 64                  ; as much of a line as is kept

; A fiftieth of a second is about seventy thousand clock cycles, and one look
; at the whole keyboard is about nineteen hundred, so this many looks fill a
; frame.  Nothing here turns on it being exact.
LOOKS_A_FRAME   equ 38

; Look once at the whole keyboard.  The character comes back in A, and zero
; with the zero flag set when nothing useful is held.
; Corrupts: BC, DE, HL
scan_keyboard:
                ld      hl, key_table
                ld      bc, $FEFE
                ld      d, 8
.row:
                in      a, (c)
                cpl
                and     $1F                     ; five keys, now one means held
                ld      e, 5
.key:
                rra
                jr      c, .found
                inc     hl
                dec     e
                jr      nz, .key
                jr      .next_row
.found:
                ld      a, (hl)
                or      a
                ret
.next_row:
                rlc     b                       ; on to the next half row
                dec     d
                jr      nz, .row
                xor     a
                ret

; Whether caps shift is held; zero flag clear if it is.
; Corrupts: A, BC
caps_held:
                ld      bc, $FEFE
                in      a, (c)
                cpl
                and     1
                ret

; Wait for a key and give it back in A, having waited for the last one to be
; let go first.
; Corrupts: BC, DE, HL
read_key:
.wait_release:
                call    scan_keyboard
                or      a
                jr      nz, .wait_release
.wait_press:
                call    scan_keyboard
                or      a
                jr      z, .wait_press
                ; caps shift with zero means rub out
                cp      '0'
                jr      nz, .done
                push    af
                call    caps_held
                jr      z, .not_delete
                pop     af
                ld      a, KEY_DELETE
                ret
.not_delete:
                pop     af
.done:
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
                ld      b, a                    ; the character, kept safe
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

; Wait for a key, or for HL fiftieths of a second, whichever comes first.
; There is no interrupt to count frames with, the runtime keeps them off, so
; the time is counted in looks at the keyboard.
;
; What is already held when the wait starts does not count, or the enter that
; ended the order would end the wait as well.  The keyboard has to come clear
; first, which is the same courtesy read_key does.
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

line_ptr:       dw      0
line_length:    db      0
input_buffer:   ds      INPUT_MAX

; The five keys of each half row, in the order their bits come out.  A zero
; is a shift key, which is not a character on its own.
key_table:
                db      0, 'Z', 'X', 'C', 'V'
                db      'A', 'S', 'D', 'F', 'G'
                db      'Q', 'W', 'E', 'R', 'T'
                db      '1', '2', '3', '4', '5'
                db      '0', '9', '8', '7', '6'
                db      'P', 'O', 'I', 'U', 'Y'
                db      KEY_ENTER, 'L', 'K', 'J', 'H'
                db      ' ', 0, 'M', 'N', 'B'
