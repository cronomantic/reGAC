; MIT License, Copyright (c) 2025 Cronomantic
;
; Reading the keyboard on a PCW, which is reading sixteen bytes of memory.
;
; Nothing is asked of any port.  The keyboard's own controller keeps the state
; of every key in the last sixteen bytes of the first sixty four kilobytes of
; RAM, which with our map is $FFF0 to $FFFF, and writes them there whether the
; processor is looking or not.  A bit is *high* while its key is held, which is
; the other way round from every other machine here.
;
; Where each key sits was measured in the emulator, key by key, and what came
; out is the Amstrad CPC's own matrix: every letter, every digit, the space,
; the comma, the full stop, enter and the shift land on exactly the bit the
; CPC has them on.  The six marks of row three could not be pressed from the
; host keyboard, so they are the CPC's, which is the best evidence there is
; and agrees with everything that could be checked.
;
; Letters come back in upper case because the vocabulary is stored that way.

KEYS_AT         equ $FFF0               ; where the controller leaves them
                ; and it will leave them there whatever else we had in mind,
                ; so the table the video reads has to end before this
                ASSERT  ROLLER_AT + 512 <= KEYS_AT
KEY_ROWS        equ 16
SHIFT_ROW       equ 2                   ; and the bit of it the shift is on
SHIFT_BIT       equ %00100000

KEY_ENTER       equ 13
KEY_DELETE      equ 8
INPUT_MAX       equ 64                  ; as much of a line as is kept

; A fiftieth of a second is eighty thousand clock cycles here, and one look at
; the whole keyboard is about 5750, so this many looks fill a frame.
; It was measured, and not guessed as it was at first: a wait like HOLD's with
; nothing pressed, against the processor's own cycle counter.  The guesses were
; out by up to three and a half times, which made a HOLD that long.  A look
; with a key held costs a little more, so a key repeats a little late.
LOOKS_A_FRAME   equ 14
LOOKS_HELD      equ 13                  ; a look with a key held, about 5940

; There is nothing to set up: the controller was already writing there before
; we started.  It is here so that every machine's runtime can say the same.
keyboard_init:
                ret

; Read the eight keys of row A, into A.  A bit high means held.
; Corrupts: AF, HL
read_row:
                ld      hl, KEYS_AT
                add     a, l
                ld      l, a
                ld      a, 0
                adc     a, h
                ld      h, a
                ld      a, (hl)
                ret

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
                ld      de, KEYS_AT
                ld      b, KEY_ROWS
.row:
                ld      a, (de)
                inc     de
                ld      c, 8
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
                dec     c
                jr      nz, .key
                djnz    .row
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

; Whether either shift is held; zero flag clear if one is.
; Corrupts: AF
shift_held:
                ld      a, (KEYS_AT + SHIFT_ROW)
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
                jp      next_key

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

; The sixteen rows of eight, in the order the bits come out of each byte.  A
; nought is a key with nothing to say for itself here: a shift, a cursor, a
; function key, or one of the many this machine has and the adventure does not
; need.  The two keys that rub out are the two the machine has for it.
key_table:
                db      0, 0, 0, 0, 0, 0, 0, 0
                db      0, 0, 0, 0, 0, 0, 0, 0
                db      KEY_DELETE, 0, KEY_ENTER, 0, 0, 0, 0, 0
                db      '^', '-', '@', 'P', ';', ':', '/', '.'
                db      '0', '9', 'O', 'I', 'L', 'K', 'M', ','
                db      '8', '7', 'U', 'Y', 'H', 'J', 'N', ' '
                db      '6', '5', 'R', 'T', 'G', 'F', 'B', 'V'
                db      '4', '3', 'E', 'W', 'S', 'D', 'C', 'X'
                db      '1', '2', 0, 'Q', 0, 'A', 0, 'Z'
                db      0, 0, 0, 0, 0, 0, 0, KEY_DELETE
                db      0, 0, 0, 0, 0, 0, 0, 0
                db      0, 0, 0, 0, 0, 0, 0, 0
                db      0, 0, 0, 0, 0, 0, 0, 0
                db      0, 0, 0, 0, 0, 0, 0, 0
                db      0, 0, 0, 0, 0, 0, 0, 0
                db      0, 0, 0, 0, 0, 0, 0, 0

; What a key says with shift held, as far as an adventure ever needs: the
; marks that part one order from the next and have no key of their own.
shifted_pairs:  db      '1', '!'
                db      '/', '?'
                db      '2', '"'
                db      ';', '+'
                db      ':', '*'
                db      0

key_found:      db      0
line_ptr:       dw      0
line_length:    db      0
input_buffer:   ds      INPUT_MAX

                include "../common/keys.asm"
