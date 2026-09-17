; MIT License, Copyright (c) 2025 Cronomantic
;
; The screen on a Spectrum Next: layer 2, which is a byte a pixel and no clash
; at all.
;
; Layer 2 is forty eight kilobytes of ordinary memory that the video reads, and
; the memory management unit can show any eight of it wherever we like, so
; there is nothing here like the video chip of an MSX: what is drawn is drawn
; straight into the picture, with no copy in between and nothing to send
; across afterwards.  gfx_show has nothing to do.
;
; What there is instead is a window.  Sixty four kilobytes will not hold the
; database, the interpreter and all forty eight of layer 2 at once, so layer 2
; is seen sixteen kilobytes at a time at $C000 -- the top half of the picture,
; the bottom half, or the eight rows of text -- and a piece is mapped by
; writing two registers.  Which piece is wanted follows from the row, so
; nothing above this has to know.
;
;       lines   0-63    the top half of the picture
;       lines  64-127   the bottom half
;       lines 128-191   the text window
;
; A line is 256 bytes, so inside a piece a pixel is at $C000 + (y & 63) * 256 +
; x: the row is the high byte and the column the low one, which is as cheap as
; the Spectrum and cheaper than anything else here.
;
; The sixteen colours are the Spectrum's own, because the palette is ours to
; set: entry n is the Spectrum's colour n, so a pixel is the number a picture
; asked for and nothing has to be matched to anything.

L2_PORT         equ $123B               ; bit 1 shows layer 2
NEXT_REG_SELECT equ $243B               ; and the machine's own registers
NEXT_REG_VALUE  equ $253B

REG_TURBO       equ $07                 ; how fast the processor runs
REG_L2_BANK     equ $12                 ; which 16K bank layer 2 starts at
REG_PALETTE_SEL equ $43                 ; which palette is being written
REG_PALETTE_IX  equ $40                 ; and where in it
REG_PALETTE_9   equ $44                 ; nine bits of colour, in two writes
MMU6            equ $56                 ; the two registers that map $C000
MMU7            equ $57

TURBO_28        equ 3                   ; twenty eight megahertz
L2_FIRST_PAGE   equ 16                  ; the 8K pages layer 2 is in: bank 8
L2_PALETTE      equ %00010000           ; layer 2's first palette, to write

WINDOW          equ $C000               ; where a piece of layer 2 is seen
PIECE_LINES     equ 64
PIECE_BYTES     equ PIECE_LINES * 256
PIECE_TOP       equ 0                   ; the three of them
PIECE_BOTTOM    equ 1
PIECE_TEXT      equ 2

ROW_BYTES       equ 256
PICTURE_ROWS    equ 128                 ; what a picture is given
TEXT_ROWS       equ 8                   ; and the rows under it
SCREEN_COLS     equ 32

TEXT_INK        equ 7                   ; white on black, as on the Spectrum
TEXT_PAPER      equ 0
START_PAPER     equ 7                   ; what a picture starts on

; Put the machine in layer 2 and lay the screen out.  The colours go in first,
; because everything shown afterwards is one of them.
; Corrupts: AF, BC, DE, HL
screen_init:
                ; Which sixteen kilobyte bank layer 2 starts at is a register
                ; like any other, and what is in it depends on who loaded us:
                ; a .nex with a loading screen in it does not leave the same
                ; value as a bare one.  So it is said rather than assumed --
                ; the pages this file maps and the ones the video reads have to
                ; be the same pages, and a picture drawn into the wrong ones is
                ; invisible and looks like a picture that was never drawn.
                ld      a, L2_FIRST_PAGE / 2
                nextreg REG_L2_BANK, a
                ld      bc, L2_PORT
                ld      a, %00000010            ; layer 2 shown
                out     (c), a
                call    set_palette
                call    cls_picture
                call    cls_window
                ; the font, out of the database, as on every machine
                ld      a, SECTION_FONT
                call    db_section
                ld      a, (hl)
                ld      (font_first), a
                inc     hl
                ld      a, (hl)
                ld      (font_count), a
                inc     hl
                ld      (font_glyphs), hl
                ret

; The sixteen colours of a Spectrum into the first sixteen entries of layer
; two's palette, three bits a channel.  The table is the one the reference
; renderer holds, worked out from the same numbers; tests/test_graphics_next.py
; compares the two so that they cannot drift apart.
; Corrupts: AF, B, HL
set_palette:
                ld      a, L2_PALETTE
                nextreg REG_PALETTE_SEL, a
                xor     a
                nextreg REG_PALETTE_IX, a       ; from the first, counting up
                ld      hl, palette
                ld      b, 16 * 2
.each:
                ld      a, (hl)
                nextreg REG_PALETTE_9, a
                inc     hl
                djnz    .each
                ret

; Three bits of red, three of green, three of blue, in the two writes the
; machine wants: RRRGGGBB and then the last bit of the blue.
palette:
                db      $00, 0          ;  0  black
                db      $03, 0          ;  1  blue
                db      $C0, 0          ;  2  red
                db      $C3, 0          ;  3  magenta
                db      $18, 1          ;  4  green
                db      $1B, 0          ;  5  cyan
                db      $D8, 1          ;  6  yellow
                db      $DB, 0          ;  7  white
                db      $00, 0          ;  8  and the bright eight
                db      $03, 1          ;  9
                db      $E0, 0          ; 10
                db      $E3, 1          ; 11
                db      $1C, 1          ; 12
                db      $1F, 1          ; 13
                db      $FC, 1          ; 14
                db      $FF, 1          ; 15

; Show piece A of layer 2 in the sixteen kilobytes at $C000.  Nothing is
; written if it is there already, which is what makes it cheap enough to ask
; before every pixel.
; Corrupts: AF
map_piece:
                push    hl
                ld      hl, piece_now
                cp      (hl)
                jr      z, .there
                ld      (hl), a
                add     a, a
                add     a, L2_FIRST_PAGE        ; two 8K pages to a piece
                nextreg MMU6, a
                inc     a
                nextreg MMU7, a
.there:
                pop     hl
                ret

piece_now:      db      $FF                     ; none of them, to begin with

; The picture is drawn where it is shown, so there is nothing to send across.
gfx_show:
                ret

; Wipe both halves of the picture to the paper it starts on.
; Corrupts: AF, BC, DE, HL
cls_picture:
                ld      c, START_PAPER
                ld      a, PIECE_TOP
                call    clear_piece
                ld      c, START_PAPER          ; the copy took the register
                ld      a, PIECE_BOTTOM
                ; fall through

; Fill piece A with the colour in C.
; Corrupts: AF, BC, DE, HL
clear_piece:
                push    bc
                call    map_piece
                pop     bc
                ld      hl, WINDOW
                ld      de, WINDOW + 1
                ld      (hl), c
                ld      bc, PIECE_BYTES - 1
                ldir
                ret

; Clear the text window and put the cursor at the top of it.
; Corrupts: AF, BC, DE, HL
cls_window:
                ld      c, TEXT_PAPER
                ld      a, PIECE_TEXT
                call    clear_piece
                xor     a
                ld      (cursor_x), a
                ld      (cursor_y), a
                ret

; Where the cursor is, inside the text piece: eight lines of 256 bytes to a
; row of characters, eight bytes across to a column.
; Corrupts: AF
cursor_address:
                ld      a, (cursor_y)
                add     a, a
                add     a, a
                add     a, a                    ; eight lines to a row
                add     a, WINDOW >> 8
                ld      h, a
                ld      a, (cursor_x)
                add     a, a
                add     a, a
                add     a, a                    ; eight bytes to a column
                ld      l, a
                ret

; Move the text window up by one row of characters and wipe the row that came
; free.  All of it is in one piece, so it is one long copy.
; Corrupts: everything
scroll_window:
                ld      a, PIECE_TEXT
                call    map_piece
                ld      hl, WINDOW + 8 * ROW_BYTES
                ld      de, WINDOW
                ld      bc, (TEXT_ROWS - 1) * 8 * ROW_BYTES
                ldir
                ld      hl, WINDOW + (TEXT_ROWS - 1) * 8 * ROW_BYTES
                ld      de, WINDOW + (TEXT_ROWS - 1) * 8 * ROW_BYTES + 1
                ld      (hl), TEXT_PAPER
                ld      bc, 8 * ROW_BYTES - 1
                ldir
                ret

; TEXT and PICT, of which this machine does only half.
;
; The half it does is the one that matters most: with TEXT no picture is
; drawn, which the interpreter sees to by itself.  The other half -- giving
; the text the whole screen -- is not here, for want of room where the code
; is: the interpreter has to end before the fill's mask at $A000, which is
; wiped with every picture, and there are a couple of hundred bytes left under
; it.  That was once taken for bytes past $A000 never reaching the machine;
; they reach it, and the first picture wipes them.  There are some three
; kilobytes free above the interrupt routine, from about $B200, which the
; build does not use yet.  See doc/pendiente.md.
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
                cp      TEXT_ROWS
                jr      c, .fits
                call    scroll_window
                ld      a, TEXT_ROWS - 1
.fits:
                ld      (cursor_y), a
                ret

; Draw the glyph for code A at the cursor and step right.  A glyph is eight
; bytes of bits and what goes on the screen is sixty four bytes of colour, one
; a pixel, which is what a screen without clash costs.
; Corrupts: everything
; The ink the text is printed in, from a change of ink in a message.  Here a
; pixel is a byte of palette and the palette is the Spectrum's sixteen in
; order, so the colour asked for is the colour written.
; Corrupts: AF
text_ink:
                and     15
                ld      (text_colour), a
                ret

text_colour:    db      TEXT_INK

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
                ex      de, hl                  ; DE = the glyph
                ld      a, PIECE_TEXT
                call    map_piece
                call    cursor_address
                ld      c, 8                    ; its eight lines
.line:
                ld      a, (de)
                inc     de
                ld      b, 8                    ; and the eight pixels of each
.pixel:
                rlca
                push    af
                ld      a, TEXT_PAPER
                jr      nc, .lay_it
                ld      a, (text_colour)
.lay_it:
                ld      (hl), a
                inc     l
                pop     af
                djnz    .pixel
                ld      a, l
                sub     8                       ; back to where the column is
                ld      l, a
                inc     h                       ; and on to the next line down
                dec     c
                jr      nz, .line
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
; Corrupts: everything
backspace:
                ld      a, (cursor_x)
                or      a
                jr      nz, .same_line
                ld      a, (cursor_y)
                or      a
                ret     z                       ; nothing left to rub out
                dec     a
                ld      (cursor_y), a
                ld      a, SCREEN_COLS - 1
                jr      .place
.same_line:
                dec     a
.place:
                ld      (cursor_x), a
                ld      a, PIECE_TEXT
                call    map_piece
                call    cursor_address
                ld      c, 8
.line:
                ld      b, 8
.pixel:
                ld      (hl), TEXT_PAPER
                inc     l
                djnz    .pixel
                ld      a, l
                sub     8
                ld      l, a
                inc     h
                dec     c
                jr      nz, .line
                ret

font_glyphs:    dw      0
font_first:     db      0
font_count:     db      0
cursor_x:       db      0
cursor_y:       db      0

; What the border was last set to, which is the Spectrum's arrangement: the
; port cannot be read back and the speaker is another bit of it, so beep.asm
; puts the border out again with every flip.
gfx_border:     db      0
