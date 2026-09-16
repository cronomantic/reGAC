; MIT License, Copyright (c) 2025 Cronomantic
;
; The screen on the Spectrum.
;
; The picture takes the top sixteen character rows and the text the eight
; below, and only those eight ever scroll, which is how the original behaved.
; See doc/graficos.md.
;
; Only usually, that is.  TEXT gives the text the whole screen, and then the
; picture scrolls away with everything else: text_top says where the window
; begins and it is a byte, not a constant, so the scrolling walks the rows
; one at a time instead of trusting that the window sits inside one third of
; the display.  What TEXT and PICT do was measured on the original -- see
; doc/pendiente.md.
;
; The printing is ours, not the ROM's.  Codes are places in the adventure's own
; character set, not ASCII, so an accented letter is a glyph like any other,
; and the same routine serves every machine once its screen layer is written.

TEXT_TOP    equ 16                      ; first character row the text may use
TEXT_ROWS   equ 24 - TEXT_TOP
SCREEN_COLS equ 32
TEXT_ATTR   equ 7                       ; white on black
SCREEN_THIRD equ $5000                  ; the third the text window lives in
ATTR_BASE   equ $5800 + TEXT_TOP * 32

; Read the font out of the database and clear the text window.
; Corrupts: AF, BC, DE, HL
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
                ; fall through

; Clear the text window and put the cursor at its top left.
; Corrupts: AF, BC, DE, HL
cls_window:
                ld      hl, SCREEN_THIRD
                ld      de, SCREEN_THIRD + 1
                ld      bc, 2048 - 1
                ld      (hl), 0
                ldir
                ld      hl, ATTR_BASE
                ld      de, ATTR_BASE + 1
                ld      bc, TEXT_ROWS * 32 - 1
                ld      (hl), TEXT_ATTR
                ldir
                xor     a
                ld      (cursor_x), a
                ld      a, TEXT_TOP
                ld      (cursor_y), a
                ret

; Screen address of the cursor, in HL.
; Corrupts: AF, DE
cursor_address:
                ld      a, (cursor_y)
                ld      l, a
                and     %00011000               ; already the third, times eight
                add     a, $40
                ld      h, a
                ld      a, l
                and     %00000111
                rrca
                rrca
                rrca                            ; row within the third, x32
                ld      l, a
                ld      a, (cursor_x)
                or      l
                ld      l, a
                ret

; The address of pixel line C of character row B, in HL.
; Corrupts: AF
text_row_address:
                ld      a, b
                and     %00011000               ; the third, already times eight
                or      c
                or      $40
                ld      h, a
                ld      a, b
                and     %00000111
                rrca
                rrca
                rrca                            ; the row within the third, x32
                ld      l, a
                ret

; The address of the colours of character row B, in HL.
; Corrupts: AF
text_row_colours:
                ld      l, b
                ld      h, 0
                add     hl, hl
                add     hl, hl
                add     hl, hl
                add     hl, hl
                add     hl, hl                  ; thirty two to a row
                ld      a, h
                or      $58
                ld      h, a
                ret

; Move the text window up by one character row.  The window is whatever
; text_top says, so the rows are moved one by one: with TEXT it is the whole
; screen and the old trick of one LDIR inside a single third does not hold.
; Corrupts: everything
scroll_window:
                ld      a, (text_top)
                ld      (scroll_row), a
.each_row:
                ld      a, (scroll_row)
                cp      23
                jr      nc, .the_last_one
                xor     a
                ld      (scroll_line), a
.each_line:
                ld      a, (scroll_row)
                inc     a
                ld      b, a
                ld      a, (scroll_line)
                ld      c, a
                call    text_row_address             ; where it comes from
                push    hl
                ld      a, (scroll_row)
                ld      b, a
                ld      a, (scroll_line)
                ld      c, a
                call    text_row_address             ; where it goes
                ex      de, hl
                pop     hl
                ld      bc, 32
                ldir
                ld      hl, scroll_line
                inc     (hl)
                ld      a, (hl)
                cp      8
                jr      c, .each_line
                ; and the colours of that row move with it
                ld      a, (scroll_row)
                inc     a
                ld      b, a
                call    text_row_colours
                push    hl
                ld      a, (scroll_row)
                ld      b, a
                call    text_row_colours
                ex      de, hl
                pop     hl
                ld      bc, 32
                ldir
                ld      hl, scroll_row
                inc     (hl)
                jr      .each_row
.the_last_one:
                ; the row that came free at the bottom
                xor     a
                ld      (scroll_line), a
.each_blank:
                ld      b, 23
                ld      a, (scroll_line)
                ld      c, a
                call    text_row_address
                ld      d, h
                ld      e, l
                inc     de
                ld      (hl), 0
                ld      bc, 31
                ldir
                ld      hl, scroll_line
                inc     (hl)
                ld      a, (hl)
                cp      8
                jr      c, .each_blank
                ld      b, 23
                call    text_row_colours
                ld      d, h
                ld      e, l
                inc     de
                ld      (hl), TEXT_ATTR
                ld      bc, 31
                ldir
                ret

; TEXT: the text has the whole screen from now on.  Nothing is cleared and
; the cursor does not move -- what changes is only how far the scrolling
; reaches, which is what the original does.
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
; Corrupts: AF, BC, DE, HL
new_line:
                xor     a
                ld      (cursor_x), a
                ld      a, (cursor_y)
                inc     a
                cp      24
                jr      c, .fits
                call    scroll_window
                ld      a, 23
.fits:
                ld      (cursor_y), a
                ret

; The attribute of the cursor's cell, in HL.
; Corrupts: AF, DE
attr_address:
                ld      a, (cursor_y)
                ld      l, a
                ld      h, 0
                add     hl, hl
                add     hl, hl
                add     hl, hl
                add     hl, hl
                add     hl, hl                  ; thirty two to a row
                ld      a, (cursor_x)
                add     a, l
                ld      l, a
                jr      nc, .no_carry
                inc     h
.no_carry:
                ld      de, $5800
                add     hl, de
                ret

; The ink the text is printed in, from a change of ink in a message: A is one
; of the Spectrum's sixteen, eight and above being the same colour bright, and
; what is kept is the whole attribute byte -- the paper stays black, which is
; what the text window is cleared to.
; Corrupts: AF, BC
text_ink:
                and     15
                ld      c, a
                and     7
                ld      b, a
                ld      a, c
                and     8
                jr      z, .plain
                ld      a, %01000000            ; bright, in an attribute
.plain:
                or      b
                ld      (text_attr), a
                ret

text_attr:      db      TEXT_ATTR

; Draw the glyph for code A at the cursor and step right.
; Corrupts: AF, BC, DE, HL
print_char:
                push    af
                ld      hl, font_first
                sub     (hl)                    ; where it is in the font
                ld      l, a
                ld      h, 0
                add     hl, hl
                add     hl, hl
                add     hl, hl                  ; eight bytes a glyph
                ld      de, (font_glyphs)
                add     hl, de
                push    hl
                call    cursor_address
                ex      de, hl                  ; DE = screen
                pop     hl                      ; HL = glyph
                ld      b, 8
.row:
                ld      a, (hl)
                ld      (de), a
                inc     hl
                inc     d                       ; next pixel line
                djnz    .row
                call    attr_address            ; and the colour of the cell
                ld      a, (text_attr)
                ld      (hl), a
                pop     af
                ; step right, wrapping to the next line at the edge
                ld      a, (cursor_x)
                inc     a
                cp      SCREEN_COLS
                jr      c, .same_line
                jp      new_line
.same_line:
                ld      (cursor_x), a
                ret

; Step back one place and rub out what was there.
; Corrupts: AF, BC, DE, HL
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
                inc     h
                djnz    .row
                ret

font_glyphs:    dw      0
font_first:     db      0
font_count:     db      0
cursor_x:       db      0
cursor_y:       db      TEXT_TOP
text_top:       db      TEXT_TOP                ; the first row the text may use
scroll_row:     db      0
scroll_line:    db      0

; What the border was last set to.  It is kept because the port it goes out on
; cannot be read back and the speaker is another bit of it: beep.asm has to
; put the border out again with every flip.  draw.asm writes it.
gfx_border:     db      0
