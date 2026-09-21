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

; A fiftieth of a second is 69888 clock cycles, and one look at the whole
; keyboard with nothing held is about 1840, so this many looks fill a frame.
; It was measured, and not guessed as it was at first: a wait like HOLD's with
; nothing pressed, against the processor's own cycle counter.  This one the guess
; had right; the other machines' were out by up to three and a half times.  A look
; with a key held costs a little more, so a key repeats a little late.
;
; The Next reads this same keyboard at eight times the speed, so it says its
; own number before it includes this, as a define: a label asked about with
; IFNDEF is there on the assembler's second pass whoever defined it.
; With a key held a look is about 2370 cycles, which is what a key repeating
; is counted in.
                IFDEF NEXT_LOOKS_A_FRAME
LOOKS_A_FRAME   equ NEXT_LOOKS_A_FRAME
LOOKS_HELD      equ NEXT_LOOKS_HELD
                ELSE
LOOKS_A_FRAME   equ 38
LOOKS_HELD      equ 29
                ENDIF

; Look once at the whole keyboard.  The character comes back in A, and zero
; with the zero flag set when nothing useful is held.
;
; The two shifts are passed over rather than reported, or holding one would
; look like nothing being typed at all; what they do is decided afterwards.
; Symbol shift turns a key into the mark printed on it in red, which is the
; only way to type the full stop and the comma that part one order from the
; next.
; Corrupts: BC, DE, HL
scan_keyboard:
                xor     a
                ld      (key_found), a
                ld      (key_count), a
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
                rlc     b                       ; on to the next half row
                dec     d
                jr      nz, .row
                ld      a, (key_found)
                or      a
                ret     z
                call    symbol_held
                ld      a, (key_found)
                ret     z                       ; plain, as it is printed
                jp      to_symbol

; Whether symbol shift is held; zero flag clear if it is.
; Corrupts: A, BC
symbol_held:
                ld      bc, $7FFE
                in      a, (c)
                cpl
                and     2
                ret

; What the key in A says with symbol shift held, or nothing.
; Corrupts: AF, C, HL
to_symbol:
                ld      c, a
                ld      hl, symbol_pairs
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

; The marks in red on the keys, as far as an adventure ever needs them: the
; six that part one order from the next come first.
symbol_pairs:   db      'M', '.'
                db      'N', ','
                db      'J', '-'
                db      '1', '!'
                db      'C', '?'
                db      'Z', ':'
                db      'O', ';'
                db      'P', '"'
                db      'V', '/'
                db      'K', '+'
                db      'L', '='
                db      '7', 39                 ; an apostrophe
                db      0

key_found:      db      0

; Whether caps shift is held; zero flag clear if it is.
; Corrupts: A, BC
caps_held:
                ld      bc, $FEFE
                in      a, (c)
                cpl
                and     1
                ret

; Wait for a key to be typed and give it back in A.  What counts as typing one
; is the ROM's rules, in common/keys.asm.
; Corrupts: BC, DE, HL
read_key:
                call    next_key
                push    af                      ; the original clicked at every
                call    beep_click              ; key, and so does this
                pop     af
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

; Which engine makes a noise here.  A 48 has only its speaker; a 128, a +3
; and a Next have a sound chip as well, and where there is a chip it is the
; better instrument -- a cleaner note, and the border left alone.  The build
; says which with WITH_AY.
                IFDEF WITH_AY
                include "ay.asm"
                ELSE
                include "beep.asm"
                ENDIF

                include "../common/keys.asm"
