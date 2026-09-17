; MIT License, Copyright (c) 2025 Cronomantic
;
; Reading the keyboard on an Amstrad, without the firmware.
;
; The keys hang off the sound chip, not off a port of their own: the 8255 is
; told to put the chip in "choose a register" mode, register fourteen is
; selected, the row wanted is written to the 8255's port C and the eight keys
; of that row are then read back through port A.  A bit is low while its key
; is held, as everywhere else.
;
; There are ten rows of eight.  Letters come back in upper case because the
; vocabulary is stored that way, and the marks that part one order from the
; next have keys of their own here, which on a Spectrum they do not.

PPI_A           equ $F4                 ; the chip's data, one row at a time
PPI_C           equ $F6                 ; and what it is being asked for
PPI_CONTROL     equ $F7

KEY_ENTER       equ 13
KEY_DELETE      equ 8
INPUT_MAX       equ 64                  ; as much of a line as is kept

; A fiftieth of a second is eighty thousand clock cycles here, and one look at
; the whole keyboard is about 6680 -- ten rows through the 8255 -- so this
; many looks fill a frame.
; It was measured, and not guessed as it was at first: a wait like HOLD's with
; nothing pressed, against the processor's own cycle counter.  The guesses were
; out by up to three and a half times, which made a HOLD that long.  A look
; with a key held costs a little more, so a key repeats a little late.
LOOKS_A_FRAME   equ 12
LOOKS_HELD      equ 11                  ; a look with a key held, about 6960

; Read the eight keys of row A, into A.  A bit low means held.
;
; The whole dance every time: the chip is told which register the keyboard
; comes back on, the row is written to port C and the answer read through port
; A, which has to be turned round for the read and back again afterwards.
; Doing less than this once left it reading somebody else register.
;
; In a build with music the interrupts go off while this lasts.  The music is
; written to the same chip through the same 8255, so an interrupt half way
; through this dance would leave the chip pointed at somebody else's register
; and the row would come back wrong.  It is thirty microseconds; the music
; does not notice.
; Corrupts: AF, BC
read_row:
                IFDEF WITH_MUSIC
                di
                ENDIF
                ld      (row_wanted), a
                ld      bc, $F782
                out     (c), c                  ; port A outwards
                ld      bc, $F40E
                out     (c), c                  ; register fourteen
                ld      bc, $F6C0
                out     (c), c                  ; tell the chip to take it
                ld      bc, $F600
                out     (c), c                  ; and let go
                ld      bc, $F792
                out     (c), c                  ; port A inwards
                ld      a, (row_wanted)
                or      $40                     ; reading, and the row
                ld      b, $F6
                ld      c, a
                out     (c), c
                ld      b, $F4
                in      a, (c)                  ; its eight keys
                push    af
                ld      bc, $F782
                out     (c), c                  ; port A outwards again
                pop     af
                IFDEF WITH_MUSIC
                ei
                ENDIF
                ret

row_wanted:     db      0

; Get the chip ready to be asked about the keyboard: register fourteen is the
; one the rows come back on.
; Corrupts: AF, BC
keyboard_init:
                ld      bc, PPI_CONTROL * 256 + %10000010
                out     (c), c
                ld      bc, PPI_A * 256 + 14    ; the register to choose
                out     (c), c
                ld      bc, PPI_C * 256 + %11000000
                out     (c), c                  ; choosing it
                ld      bc, PPI_C * 256 + %00000000
                out     (c), c                  ; and done choosing
                ret

; Look once at the whole keyboard.  The character comes back in A, and zero
; with the zero flag set when nothing useful is held.
;
; The two shifts are passed over rather than reported, or holding one would
; look like nothing being typed at all; what they do is decided afterwards.
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
                cpl
                and     $FF                     ; now one means held
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
                cp      10
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

; Whether either shift is held; zero flag clear if one is.
; Corrupts: AF, BC
shift_held:
                ld      a, 2
                call    read_row
                cpl
                and     %00100000               ; row two, the shift key
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

; The ten rows of eight, as they are printed on the keys.  A nought is a key
; with nothing to say for itself here: a shift, a cursor, a function key.
key_table:
                db      0, 0, 0, 0, 0, 0, KEY_ENTER, '.'
                db      0, 0, 0, 0, 0, 0, 0, 0
                db      0, '[', KEY_ENTER, ']', 0, 0, '\', 0
                db      '^', '-', '@', 'P', ';', ':', '/', '.'
                db      '0', '9', 'O', 'I', 'L', 'K', 'M', ','
                db      '8', '7', 'U', 'Y', 'H', 'J', 'N', ' '
                db      '6', '5', 'R', 'T', 'G', 'F', 'B', 'V'
                db      '4', '3', 'E', 'W', 'S', 'D', 'C', 'X'
                db      '1', '2', 0, 'Q', 0, 'A', 0, 'Z'
                db      0, 0, 0, 0, 0, 0, 0, KEY_DELETE

; What a key says with shift held, as far as an adventure ever needs: the two
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
