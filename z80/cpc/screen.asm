; MIT License, Copyright (c) 2025 Cronomantic
;
; The Amstrad's screen, without asking the firmware for anything.
;
; The gate array takes everything through port $7Fxx, and the top two bits of
; a byte say what it is: 00 chooses a pen, with sixteen the border, 01 gives
; the one chosen a colour, and 10 sets the mode.  The colours are the
; hardware's own numbering, which is not the firmware's, so what a picture
; names has to be looked up.
;
; The pens were chosen with 01 here for as long as this machine had them, and
; that is not choosing at all: it gives a colour to whatever pen the firmware
; had chosen last.  So none of them was ever set, and the screen came up in
; the firmware's own four -- blue, yellow, cyan and red -- whatever this file
; said.  Nothing noticed, because every test looked at pens and none at a
; colour; see doc/pendiente.md.

; What a build with pictures does with colour.  Its pictures carry their inks
; (PICTURE_INKS); an adventure off an Amstrad draws with the Amstrad's rules
; (AMSTRAD_PICTURES), and then its inks may flash; one off a Spectrum draws
; with the Spectrum's, and then a colour in the text goes through the
; picture's pens as a colour in the picture does.  A build without pictures
; -- the tests of the keyboard, the tape, the text -- has neither.
                IFDEF   PICTURE_INKS
                IFDEF   AMSTRAD_PICTURES
                DEFINE  FLASHING_INKS
                ELSE
                DEFINE  COLOUR_TEXT
                ENDIF
                ENDIF

SCREEN          equ $C000
PICTURE_LEFT    equ 32                  ; where the picture starts across
PICTURE_ROWS    equ 128                 ; and how deep it is
; Eighty bytes a line, for each character row of the screen: sixteen of the
; picture and nine of the text below it.
block_starts:   dw      0, 80, 160, 240, 320, 400, 480, 560
                dw      640, 720, 800, 880, 960, 1040, 1120, 1200
                dw      1280, 1360, 1440, 1520, 1600, 1680, 1760, 1840, 1920
GATE_ARRAY      equ $7F00
GATE_BORDER     equ %00010000           ; choosing pen sixteen, the border
GATE_COLOUR     equ %01000000           ; and giving the chosen pen a colour
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
; numbers them, which is the order an adventure names them in.  The last
; three are bright yellow, pastel yellow and bright white; the yellow and the
; white were the other way round here, and it never showed while no ink was
; ever set -- see the gate array above.  What gave it away was the emulator
; painting white where 24 was asked for.
firmware_inks:  db      $54, $44, $55, $5C, $58, $5D, $4C, $45
                db      $4D, $56, $46, $57, $5E, $40, $5F, $4E
                db      $47, $4F, $52, $42, $53, $5A, $59, $5B
                db      $4A, $43, $4B

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
                ; fall through

; The four pens and the border, from the inks of the picture on the screen:
; of each pair, the one the flashing is showing now.
; Corrupts: AF, BC, DE, HL
pens_init:
                ld      e, 0                    ; which pen
.each_pen:
                ld      a, e
                call    pen_colour
                ld      bc, GATE_ARRAY
                out     (c), e                  ; choose it
                or      GATE_COLOUR
                out     (c), a                  ; and give it its colour
                inc     e
                ld      a, e
                cp      4
                jr      nz, .each_pen
                ; fall through

; The border, which is pen sixteen and wears the colour of one of the four.
; Corrupts: AF, BC, HL
border_init:
                ld      a, (border_pen)
                call    pen_colour
                ld      bc, GATE_ARRAY
                ld      l, GATE_BORDER
                out     (c), l
                or      GATE_COLOUR
                out     (c), a
                ret

; The hardware's colour for what pen A is wearing now.
; Corrupts: AF, HL
pen_colour:
                add     a, a                    ; a pair of inks to a pen
                ld      hl, ink_phase
                add     a, (hl)                 ; and which of the two
                ld      hl, picture_inks
                add     a, l
                ld      l, a
                jr      nc, .no_carry
                inc     h
.no_carry:
                ld      a, (hl)
                ; fall through

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

; The inks of the picture on the screen, in the firmware's numbering: a pair
; to each pen, as an Amstrad picture carries them, because an ink there can
; flash between two colours.  Until a picture says otherwise they are the four
; the firmware starts the machine with, which is what the screen has always
; shown -- see the gate array above.
INKS_BYTES      equ 8
picture_inks:   db      1, 1, 24, 24, 20, 20, 6, 6
; Which of each pair is on: the second one first, because that is the one the
; original hands the firmware as the first colour -- B to SCR SET INK, with the
; first byte of the pair in C.  Read at $0538 of its interpreter.
ink_phase:      db      1
border_pen:     db      0               ; the pen whose colour the border wears
picture_head:   db      0               ; what each picture carries before its
                                        ; orders: its inks and, off a
                                        ; Spectrum, its pens; or nothing

                IFDEF   PICTURE_INKS

; The inks of picture HL, when the pictures carry any.  The original sets them
; for the picture of a room, the border from the first pair and then the
; pens, at $0538; a picture called from another steps over its own, at $1C64,
; which is why this is called from draw_picture and not for a CALL.  A picture
; off a Spectrum carries the pen each of its colours comes to after the inks,
; and they are put where spectrum.asm looks for them.
; Corrupts: AF, BC, DE
picture_inks_set:
                ld      a, (picture_head)
                or      a
                ret     z
                push    hl
                call    picture_find
                jr      c, .none
                ld      a, (picture_head)       ; they are in front of the
                add     a, 2                    ; length, which is in front of
                neg                             ; the orders
                ld      e, a
                ld      d, $FF
                add     hl, de
                ld      de, picture_inks
                ld      bc, INKS_BYTES
                ldir
                IFDEF   AMSTRAD_PICTURES
                call    flash_init
                ELSE
                call    unpack_pens             ; which come after the inks
                ld      a, (text_colour)        ; and the text's colour may
                call    text_ink                ; have a pen of its own now
                ENDIF
                ld      a, 1
                ld      (ink_phase), a
                xor     a
                ld      (border_pen), a
                call    pens_init
.none:
                pop     hl
                ret

                IFDEF   AMSTRAD_PICTURES

; Whether any pen flashes, which is any pair of two colours, and the count
; started again.  The counting is the keyboard's: see flash_look.
; Corrupts: AF, BC, HL
flash_init:
                ld      hl, picture_inks
                ld      bc, 4 * 256             ; four pairs, none flashing yet
.each:
                ld      a, (hl)
                inc     hl
                cp      (hl)
                inc     hl
                jr      z, .steady
                inc     c
.steady:
                djnz    .each
                ld      a, c
                ld      (flashing), a
                xor     a
                ld      (flash_looks), a        ; nought: start counting afresh
                ret

; The firmware changes a flashing ink every ten frames, the one and then the
; other: the original never asks for anything else, SCR SET FLASHING being
; called nowhere in it.  Only a picture off an Amstrad has inks that flash.
FLASH_FRAMES    equ 10
flashing:       db      0               ; whether any pen of this picture does
flash_looks:    db      0               ; looks at the keyboard until it does

                ENDIF
                ENDIF

; How far along its pixel line character row A starts, in HL: eighty bytes a
; row.
; Corrupts: AF, BC
row_offset:
                add     a, a
                ld      c, a
                ld      b, 0
                ld      hl, block_starts
                add     hl, bc
                ld      a, (hl)
                inc     hl
                ld      h, (hl)
                ld      l, a
                ret

; Where the cursor's character cell starts, in HL.  Its eight pixel lines are
; two kilobytes apart from there.
; Corrupts: AF, BC, DE
cursor_address:
                ld      a, (cursor_y)
                call    row_offset
                ld      bc, SCREEN
                add     hl, bc
                ld      a, (cursor_x)
                add     a, a                    ; two bytes a character
                ld      c, a
                ld      b, 0
                add     hl, bc
                ret

; Move the text window up by one character row.
;
; The window begins where text_top says, which TEXT sets to nought, and on this
; machine that still costs only one LDIR a pixel line: each of the eight holds
; the twenty five character rows end to end, so moving rows from any one down
; to the last is one run however many there are.  The Spectrum's thirds have
; no such luck.  What the three numbers are is worked out once for all eight.
; Corrupts: everything
scroll_window:
                ld      a, (text_top)
                call    row_offset
                ld      (scroll_to), hl         ; where the window begins
                ld      a, (text_top)
                inc     a
                call    row_offset
                ld      (scroll_from), hl       ; and the row under that
                ld      a, TEXT_LAST - 1
                ld      hl, text_top
                sub     (hl)
                call    row_offset
                ld      (scroll_count), hl      ; every row but the first
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
                ex      de, hl                  ; the pixel line's start
                ld      hl, (scroll_from)
                add     hl, de                  ; where the copy comes from
                push    hl
                ld      hl, (scroll_to)
                add     hl, de
                ex      de, hl                  ; and where it goes
                pop     hl
                ld      bc, (scroll_count)
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

; TEXT: the text has the whole screen from now on.  Nothing is cleared and
; the cursor does not move -- what changes is only how far the scrolling
; reaches, which is what the original does.  See doc/pendiente.md.
;
; This machine went without it for a long time, for want of room: the
; interpreter ended thirty eight bytes below a boundary that cost every
; adventure a page to cross.  The boundary went, and printing a message a word
; at a time gave back the two hundred bytes of its buffer.
; Corrupts: AF
text_window_all:
                xor     a
                ld      (text_top), a
                ret

; And back under the picture, which on the original is what drawing a picture
; does rather than anything PICT says.  A cursor left above the new top comes
; down to it.
; Corrupts: AF, HL
text_window_below:
                ld      a, TEXT_TOP
                ld      (text_top), a
                ld      hl, cursor_y
                cp      (hl)
                ret     c
                ret     z
                ld      (hl), a
                xor     a
                ld      (cursor_x), a
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

; The ink the text is printed in, from a change of ink in a message or from
; the adventure's own.  The original prints in pen one on pen nought and never
; changes either, so that is what a message starts in.
;
; In an adventure off an Amstrad a number is the pen itself, which is what a
; colour meant on that machine.  In one off a Spectrum it is one of the sixteen
; colours, and it goes to the pen that colour comes to in the picture on the
; screen, as a colour in the picture does; so it is kept, and settled again
; when a picture brings its own pens.  See doc/pendiente.md.
;
; A pen's low bit is the high half of the byte and its high bit the low half,
; which is what pen_bytes says.  This had them the other way round, and what
; saved it was that the default was written as two: the text came out in pen
; one, which is the original's, and an ink of one or two in a message came
; out in the other.
; Corrupts: AF, HL
                IFDEF   COLOUR_TEXT
TEXT_INK_DEFAULT equ 7                  ; white, as on the Spectrum
                ELSE
TEXT_INK_DEFAULT equ 1
                ENDIF

text_ink:
                IFDEF   COLOUR_TEXT
                and     $0F
                ld      (text_colour), a
                ld      hl, colour_pen
                call    table_byte
                ENDIF
                and     3
                ld      h, a
                ld      a, 0
                bit     0, h
                jr      z, .no_high
                ld      a, $F0
.no_high:
                ld      (pen_high), a
                ld      a, 0
                bit     1, h
                jr      z, .no_low
                ld      a, $0F
.no_low:
                ld      (pen_low), a
                ret

pen_high:       db      $F0             ; pen one, which is the original's
pen_low:        db      0
                IFDEF   COLOUR_TEXT
text_colour:    db      TEXT_INK_DEFAULT        ; the colour the text asked for
                ENDIF

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
                ld      hl, text_top
                cp      (hl)
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
text_top:       db      TEXT_TOP                ; the first row the text may use
scroll_from:    dw      0
scroll_to:      dw      0
scroll_count:   dw      0

