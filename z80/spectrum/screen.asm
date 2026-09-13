; MIT License, Copyright (c) 2025 Cronomantic
;
; The screen on the Spectrum.
;
; The picture takes the top sixteen character rows and the text the eight
; below, and only those eight ever scroll, which is how the original behaved.
; See doc/graficos.md.
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

; Move the text window up by one character row.
; Corrupts: AF, BC, DE, HL
scroll_window:
                ld      b, 8                    ; one pass a pixel line
                ld      hl, SCREEN_THIRD + 32
                ld      de, SCREEN_THIRD
.line:
                push    bc
                push    hl
                push    de
                ld      bc, (TEXT_ROWS - 1) * 32
                ldir
                ; the row that came free is where the copy ended, DE
                ld      h, d
                ld      l, e
                inc     de
                ld      (hl), 0
                ld      bc, 31
                ldir
                pop     de
                pop     hl
                inc     d
                inc     h                       ; on to the next pixel line
                pop     bc
                djnz    .line
                ; the colours move with it
                ld      hl, ATTR_BASE + 32
                ld      de, ATTR_BASE
                ld      bc, (TEXT_ROWS - 1) * 32
                ldir
                ld      hl, ATTR_BASE + (TEXT_ROWS - 1) * 32
                ld      de, ATTR_BASE + (TEXT_ROWS - 1) * 32 + 1
                ld      bc, 31
                ld      (hl), TEXT_ATTR
                ldir
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
                inc     h
                djnz    .row
                ret

font_glyphs:    dw      0
font_first:     db      0
font_count:     db      0
cursor_x:       db      0
cursor_y:       db      TEXT_TOP
