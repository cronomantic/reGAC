; MIT License, Copyright (c) 2025 Cronomantic
;
; The Amstrad's screen, without asking the firmware for anything.
;
; The gate array takes everything through port $7Fxx: a byte with the top two
; bits 01 chooses which pen is being set and 010 what colour to give it, and
; 100 sets the mode.  The colours are the hardware's own numbering, which is
; not the firmware's, so what a picture names has to be looked up.

SCREEN          equ $C000
PICTURE_LEFT    equ 32                  ; where the picture starts across
PICTURE_ROWS    equ 128                 ; and how deep it is
; Eighty bytes a line, for each character row of the screen: sixteen of the
; picture and nine of the text below it.
block_starts:   dw      0, 80, 160, 240, 320, 400, 480, 560
                dw      640, 720, 800, 880, 960, 1040, 1120, 1200
                dw      1280, 1360, 1440, 1520, 1600, 1680, 1760, 1840, 1920
GATE_ARRAY      equ $7F00
MODE_1          equ %10001101           ; mode 1, both ROMs out of the way

; Mode 1 is forty characters across and twenty five down, of which the picture
; takes the top sixteen and the text the nine below.  A character is eight
; pixels wide, which is two bytes here, and a character row starts eighty
; bytes along from the one above it with its eight pixel lines two kilobytes
; apart.
TEXT_TOP        equ 16
TEXT_LAST       equ 25
TEXT_ROWS       equ TEXT_LAST - TEXT_TOP
SCREEN_COLS     equ 40
LINE_BYTES      equ 80

; The twenty seven colours the hardware knows, in the order the firmware
; numbers them, which is the order an adventure names them in.
firmware_inks:  db      $54, $44, $55, $5C, $58, $5D, $4C, $45
                db      $4D, $56, $46, $57, $5E, $40, $5F, $4E
                db      $47, $4F, $52, $42, $53, $5A, $59, $5B
                db      $4B, $43, $4A

; Read the font out of the database, put the machine in mode 1 with the
; picture's four pens, and clear the text window.
; Corrupts: everything
screen_init:
                ld      a, SECTION_FONT
                call    db_section
                ld      a, (hl)
                ld      (font_first), a
                inc     hl
                ld      a, (hl)
                ld      (font_count), a
                inc     hl
                ld      (font_glyphs), hl
                call    mode_init
                call    wipe_all                ; whatever was on it before
                ; fall through

; Clear the text window and put the cursor at its top left.
; Corrupts: everything
cls_window:
                ld      d, 0                    ; one pass a pixel line
.each_line:
                ld      a, d
                add     a, a
                add     a, a
                add     a, a                    ; which block, times 2048
                or      SCREEN >> 8
                ld      h, a
                ld      l, 0
                ld      bc, TEXT_TOP * LINE_BYTES
                add     hl, bc
                ld      bc, TEXT_ROWS * LINE_BYTES
.across:
                ld      (hl), 0
                inc     hl
                dec     bc
                ld      a, b
                or      c
                jr      nz, .across
                inc     d
                ld      a, d
                cp      8
                jr      nz, .each_line
                xor     a
                ld      (cursor_x), a
                ld      a, TEXT_TOP
                ld      (cursor_y), a
                ret

; Wipe the whole screen, which is sixteen kilobytes of it.
; Corrupts: everything
wipe_all:
                ld      hl, SCREEN
                ld      de, SCREEN + 1
                ld      bc, $4000 - 1
                ld      (hl), 0
                ldir
                ret

; Put the machine in mode 1 with the picture's four pens.
; Corrupts: everything
mode_init:
                ld      bc, GATE_ARRAY
                ld      a, MODE_1
                out     (c), a
                ; the four pens, and the border with them
                ld      hl, picture_inks
                ld      d, 0
.each_pen:
                ld      a, d
                or      %01000000               ; choose this pen
                ld      bc, GATE_ARRAY
                out     (c), a
                ld      a, (hl)
                call    hardware_ink
                or      %01000000               ; give it a colour
                ld      bc, GATE_ARRAY
                out     (c), a
                inc     hl
                inc     d
                ld      a, d
                cp      4
                jr      nz, .each_pen
                ; the border, which is pen sixteen
                ld      bc, GATE_ARRAY
                ld      a, %01010000
                out     (c), a
                ld      a, (picture_inks)
                call    hardware_ink
                or      %01000000
                ld      bc, GATE_ARRAY
                out     (c), a
                ret

; The hardware's colour for the firmware's number in A.
; Corrupts: AF, HL
hardware_ink:
                cp      27
                jr      c, .known
                xor     a
.known:
                ld      hl, firmware_inks
                add     a, l
                ld      l, a
                jr      nc, .no_carry
                inc     h
.no_carry:
                ld      a, (hl)
                ret

; The four pens a picture wants, in the firmware's numbering.  An adventure
; off an Amstrad carries its own; until the format holds them these are the
; four the machine starts with.
picture_inks:   db      0, 24, 20, 6

; Where the cursor's character cell starts, in HL.  Its eight pixel lines are
; two kilobytes apart from there.
; Corrupts: AF, BC, DE
cursor_address:
                ld      a, (cursor_y)
                add     a, a
                ld      c, a
                ld      b, 0
                ld      hl, block_starts
                add     hl, bc
                ld      c, (hl)
                inc     hl
                ld      b, (hl)
                ld      hl, SCREEN
                add     hl, bc
                ld      a, (cursor_x)
                add     a, a                    ; two bytes a character
                ld      c, a
                ld      b, 0
                add     hl, bc
                ret

; Move the text window up by one character row.
; Corrupts: everything
scroll_window:
                ld      d, 0
.each_block:
                push    de
                ld      a, d
                add     a, a
                add     a, a
                add     a, a
                or      SCREEN >> 8
                ld      h, a
                ld      l, 0
                push    hl
                ld      bc, (TEXT_TOP + 1) * LINE_BYTES
                add     hl, bc                  ; where the copy comes from
                pop     de
                push    hl
                ld      hl, TEXT_TOP * LINE_BYTES
                add     hl, de
                ex      de, hl                  ; and where it goes
                pop     hl
                ld      bc, (TEXT_ROWS - 1) * LINE_BYTES
                ldir
                ; the row that came free is where the copy ended
                ld      h, d
                ld      l, e
                ld      b, LINE_BYTES
.clear:
                ld      (hl), 0
                inc     hl
                djnz    .clear
                pop     de
                inc     d
                ld      a, d
                cp      8
                jr      nz, .each_block
                ret

; TEXT and PICT, of which this machine does only half.
;
; With TEXT no picture is drawn, which the interpreter sees to by itself.
; Giving the text the whole screen is not here, and the reason is measured:
; the database is laid on a boundary of 256 bytes behind the interpreter, and
; the interpreter ends thirty eight bytes below one.  Crossing it costs every
; adventure a page, and MegaCorp II has a hundred and sixty two bytes to
; spare.  The window costs some sixty.  See doc/pendiente.md.
; Corrupts: nothing
text_window_all:
                ret

text_window_below:
                ret

; Start a new line, scrolling if the window is full.
; Corrupts: everything
new_line:
                xor     a
                ld      (cursor_x), a
                ld      a, (cursor_y)
                inc     a
                cp      TEXT_LAST
                jr      c, .fits
                call    scroll_window
                ld      a, TEXT_LAST - 1
.fits:
                ld      (cursor_y), a
                ret

; Draw the glyph for code A at the cursor and step right.
;
; A glyph is eight pixels across, which here is two bytes: the top half of the
; font byte becomes the first and the bottom half the second, every pixel one
; bit of pen one.
; Corrupts: everything
; Four pixels, one to a bit in the top half of A, given the pen the text is
; in.  A pen is two bits of a pixel and the two live in different halves of
; the byte -- the high one where these pixels already are, the low one four
; places down -- so a pen is two masks and this is an AND with each.
; Corrupts: AF, C
in_pen:
                ld      c, a
                ld      a, (pen_high)
                and     c
                push    af
                ld      a, c
                rrca
                rrca
                rrca
                rrca
                ld      c, a
                ld      a, (pen_low)
                and     c
                ld      c, a
                pop     af
                or      c
                ret

; The ink the text is printed in, from a change of ink in a message.  This
; machine has four pens and a picture chooses their colours, so what a number
; means here is the pen itself, which is what the adventures written for this
; machine meant by a colour in the first place.
; Corrupts: AF
text_ink:
                and     3
                ld      c, a
                ld      a, 0
                bit     1, c
                jr      z, .no_high
                ld      a, $F0
.no_high:
                ld      (pen_high), a
                ld      a, 0
                bit     0, c
                jr      z, .no_low
                ld      a, $0F
.no_low:
                ld      (pen_low), a
                ret

pen_high:       db      $F0             ; pen two, which is what it printed in
pen_low:        db      0               ; before there was any choice

print_char:
                push    af
                ld      hl, font_first
                sub     (hl)
                ld      l, a
                ld      h, 0
                add     hl, hl
                add     hl, hl
                add     hl, hl                  ; eight bytes a glyph
                ld      de, (font_glyphs)
                add     hl, de
                push    hl
                call    cursor_address
                ex      de, hl                  ; DE = the screen
                pop     hl                      ; HL = the glyph
                ld      b, 8
.row:
                ld      a, (hl)
                and     $F0                     ; the left four pixels
                call    in_pen
                ld      (de), a
                inc     de
                ld      a, (hl)
                add     a, a
                add     a, a
                add     a, a
                add     a, a                    ; and the right four
                call    in_pen
                ld      (de), a
                dec     de
                inc     hl
                push    hl
                ld      hl, 2048                ; the next pixel line down
                add     hl, de
                ex      de, hl
                pop     hl
                djnz    .row
                pop     af
                ld      a, (cursor_x)
                inc     a
                cp      SCREEN_COLS
                jr      c, .same_line
                jp      new_line
.same_line:
                ld      (cursor_x), a
                ret

; Step back one place and rub out what was there.
; Corrupts: everything
backspace:
                ld      a, (cursor_x)
                or      a
                jr      nz, .same_line
                ld      a, (cursor_y)
                cp      TEXT_TOP
                ret     z                       ; nothing left to rub out
                dec     a
                ld      (cursor_y), a
                ld      a, SCREEN_COLS - 1
                jr      .place
.same_line:
                dec     a
.place:
                ld      (cursor_x), a
                call    cursor_address
                ld      b, 8
.row:
                ld      (hl), 0
                inc     hl
                ld      (hl), 0
                dec     hl
                push    bc
                ld      bc, 2048
                add     hl, bc
                pop     bc
                djnz    .row
                ret

font_glyphs:    dw      0
font_first:     db      0
font_count:     db      0
cursor_x:       db      0
cursor_y:       db      TEXT_TOP

