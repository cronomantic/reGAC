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
REG_TRANSPARENT equ $14                 ; the colour layer 2 does not show
REG_LINE_HIGH   equ $1E                 ; the line the video is drawing
REG_LINE_LOW    equ $1F
MMU6            equ $56                 ; the two registers that map $C000
MMU7            equ $57

TURBO_28        equ 3                   ; twenty eight megahertz
L2_FIRST_PAGE   equ 16                  ; the 8K pages layer 2 is in: bank 8
L2_PALETTE      equ %00010000           ; layer 2's first palette, to write
ULA_PALETTE     equ %00000000           ; and the ULA's, which the border is
; The colour layer 2 treats as not there.  The machine starts it at $E3, which
; is exactly what the Spectrum's bright magenta comes to in nine bits -- and
; the Amstrad's too -- so every point of that colour showed whatever was
; under layer 2 instead: two pictures of Los pajaros de Bangkok lost them.  No
; colour this machine is given comes to $01.  See doc/pendiente.md.
NOTHING_IS_CLEAR equ $01

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

                IFDEF   AMSTRAD_PICTURES
; An adventure off an Amstrad prints as the Amstrad's GAC does, in pen one on
; pen nought, which are whatever inks the picture on the screen gave them; and
; a picture starts on pen nought.
TEXT_INK        equ 1
TEXT_PAPER      equ 0
START_PAPER     equ 0
                ELSE
TEXT_INK        equ 7                   ; white on black, as on the Spectrum
TEXT_PAPER      equ 0
START_PAPER     equ 7                   ; what a picture starts on
                ENDIF
TEXT_INK_DEFAULT equ TEXT_INK           ; what a message starts in

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
                ld      a, NOTHING_IS_CLEAR
                nextreg REG_TRANSPARENT, a
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

                IFDEF   PICTURE_INKS

; -- the inks of a picture off an Amstrad ------------------------------------

; A picture off an Amstrad carries its four inks, a pair to each pen because
; an ink there can flash between two colours, and the original puts them up
; for the picture of a room: the border from the first pair and then each pen,
; at $0538 of its interpreter.  Here they go into the first four entries of
; layer 2's palette, which is what a pen is on this screen, and the border is
; the ULA's.  See z80/cpc/screen.asm, which does the same on the Amstrad.
INKS_BYTES      equ 8
picture_inks:   db      1, 1, 24, 24, 20, 20, 6, 6
ink_phase:      db      1               ; the second of a pair shows first
border_pen:     db      0
picture_head:   db      0               ; what each picture carries in front
                                        ; of its orders

; The inks of picture HL.  A picture called from another steps over its own,
; which is why this is called from draw_picture and not for a CALL.
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
                IFDEF   FLASHING_INKS
                call    flash_init
                ENDIF
                ld      a, 1
                ld      (ink_phase), a
                xor     a
                ld      (border_pen), a
                call    pens_init
.none:
                pop     hl
                ret

; The four pens and the border, from the picture's inks: of each pair, the
; one the flashing is showing now.
; Corrupts: AF, BC, DE, HL
pens_init:
                ld      a, L2_PALETTE
                nextreg REG_PALETTE_SEL, a
                xor     a
                nextreg REG_PALETTE_IX, a       ; from entry nought, counting up
                ld      e, 0
.each_pen:
                ld      a, e
                call    pen_colour
                nextreg REG_PALETTE_9, a
                ld      a, (hl)
                nextreg REG_PALETTE_9, a
                inc     e
                ld      a, e
                cp      4
                jr      nz, .each_pen
                ; fall through

; The border, which on this machine is the ULA's: it is drawn in the colour
; of the ULA palette's paper entry for the colour on the port, so the port is
; given nought and that entry the pen's ink.
; Corrupts: AF, HL
border_init:
                ld      a, ULA_PALETTE
                nextreg REG_PALETTE_SEL, a
                ld      a, ULA_BORDER_ENTRY
                nextreg REG_PALETTE_IX, a
                ld      a, (border_pen)
                call    pen_colour
                nextreg REG_PALETTE_9, a
                ld      a, (hl)
                nextreg REG_PALETTE_9, a
                xor     a
                ld      (gfx_border), a         ; the speaker shares the port
                out     ($FE), a
                ret

; The first of the two bytes of the colour pen A is wearing now, in A, and HL
; at the second.
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
                ld      a, (hl)                 ; the firmware's number
                cp      27
                jr      c, .known
                xor     a
.known:
                add     a, a                    ; two bytes to a colour
                ld      hl, next_inks
                add     a, l
                ld      l, a
                jr      nc, .no_carry2
                inc     h
.no_carry2:
                ld      a, (hl)
                inc     hl
                ret

; The ULA palette entry the border is drawn in when the port says nought.
ULA_BORDER_ENTRY equ 16

; The Amstrad's twenty seven colours, in the firmware's order, in the nine
; bits of this machine: each of the Amstrad's three levels to the nearest of
; the eight here, so nought, four and seven.  RRRGGGBB, then the last bit of
; the blue.  None of them is NOTHING_IS_CLEAR.
next_inks:
                db      $00, 0          ;  0  black
                db      $02, 0          ;  1  blue
                db      $03, 1          ;  2  bright blue
                db      $80, 0          ;  3  red
                db      $82, 0          ;  4  magenta
                db      $83, 1          ;  5  mauve
                db      $E0, 0          ;  6  bright red
                db      $E2, 0          ;  7  purple
                db      $E3, 1          ;  8  bright magenta
                db      $10, 0          ;  9  green
                db      $12, 0          ; 10  cyan
                db      $13, 1          ; 11  sky blue
                db      $90, 0          ; 12  yellow
                db      $92, 0          ; 13  white
                db      $93, 1          ; 14  pastel blue
                db      $F0, 0          ; 15  orange
                db      $F2, 0          ; 16  pink
                db      $F3, 1          ; 17  pastel magenta
                db      $1C, 0          ; 18  bright green
                db      $1E, 0          ; 19  sea green
                db      $1F, 1          ; 20  bright cyan
                db      $9C, 0          ; 21  lime
                db      $9E, 0          ; 22  pastel green
                db      $9F, 1          ; 23  pastel cyan
                db      $FC, 0          ; 24  bright yellow
                db      $FE, 0          ; 25  pastel yellow
                db      $FF, 1          ; 26  bright white

                IFDEF   FLASHING_INKS

; Whether any pen flashes, which is any pair of two colours, and the count
; started again.
; Corrupts: AF, BC, HL
flash_init:
                ld      hl, picture_inks
                ld      bc, 4 * 256
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
                ld      hl, 0
                ld      (flash_looks), hl       ; nought: start counting afresh
                ret

; The firmware changes a flashing ink every ten frames, the one and then the
; other; the original never asks for anything else.  This interpreter runs
; with the interrupts off, so there is no frame to count: what there is is the
; keyboard, looked at LOOKS_A_FRAME times a frame -- measured -- and every wait
; for a key is that.  So the pens change there and only there.
FLASH_FRAMES    equ 10
flashing:       db      0
flash_looks:    dw      0

; One look's worth of flashing.  Nothing at all unless a pen flashes.
; Corrupts: AF, BC, DE, HL
flash_look:
                ld      a, (flashing)
                or      a
                ret     z
                ld      hl, (flash_looks)
                ld      a, h
                or      l
                jr      nz, .counting
                ld      hl, FLASH_FRAMES * LOOKS_A_FRAME
.counting:
                dec     hl
                ld      (flash_looks), hl
                ld      a, h
                or      l
                ret     nz
                ; In the frame flyback, as the firmware does, so that no frame
                ; comes out half in the one colour and half in the other: the
                ; video is past the 192 lines of the picture from line 192 to
                ; the end of the frame.
.wait:
                ld      bc, NEXT_REG_SELECT
                ld      a, REG_LINE_HIGH
                out     (c), a
                inc     b
                in      a, (c)
                or      a
                jr      nz, .wait
                dec     b
                ld      a, REG_LINE_LOW
                out     (c), a
                inc     b
                in      a, (c)
                cp      192
                jr      c, .wait
                ld      a, (ink_phase)
                xor     1
                ld      (ink_phase), a
                jp      pens_init

                ENDIF
                ENDIF

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
; free.  Under a picture all of it is in one piece, so it is one long copy.
; Corrupts: everything
scroll_window:
                ld      a, (text_whole)
                or      a
                jr      nz, scroll_screen
                ld      a, PIECE_TEXT
                call    map_piece
                ld      hl, WINDOW + 8 * ROW_BYTES
                ld      de, WINDOW
                ld      bc, (TEXT_ROWS - 1) * 8 * ROW_BYTES
                ldir
                ld      hl, WINDOW + (TEXT_ROWS - 1) * 8 * ROW_BYTES
wipe_row:
                ld      d, h
                ld      e, l
                inc     de
                ld      (hl), TEXT_PAPER
                ld      bc, 8 * ROW_BYTES - 1
                ldir
                ret

; With TEXT the whole screen goes up, picture and all, and the screen is three
; pieces of which only one is ever seen.  So it is walked an 8K page at a time
; instead, with the page after it seen behind it: each copy takes the page's
; lines from eight further down, and those eight are the start of the next
; page, which is only written on the next turn round.  The last turn reads
; eight lines of a page that is not layer 2's, which does no harm, and they
; are the row that is wiped.
; Corrupts: everything
scroll_screen:
                ld      a, L2_FIRST_PAGE
                ld      b, 6                    ; the six pages of layer 2
.page:
                nextreg MMU6, a
                inc     a
                nextreg MMU7, a
                push    af
                push    bc
                ld      hl, WINDOW + 8 * ROW_BYTES
                ld      de, WINDOW
                ld      bc, $2000
                ldir
                pop     bc
                pop     af
                djnz    .page
                ld      a, $FF
                ld      (piece_now), a          ; none of the three is there now
                ld      hl, WINDOW + $2000 - 8 * ROW_BYTES
                jr      wipe_row

; TEXT: the text has the whole screen from now on.  Nothing is cleared and
; the cursor does not move -- what changes is only how far the scrolling
; reaches, which is what the original does.  The cursor is always in the rows
; under the picture, so giving the window back has nothing to put right.
; Corrupts: AF
text_window_all:
                ld      a, 1
                ld      (text_whole), a
                ret

; And back under the picture, which on the original is what drawing a picture
; does rather than anything PICT says.
; Corrupts: AF
text_window_below:
                xor     a
                ld      (text_whole), a
                ret

text_whole:     db      0                       ; TEXT has the whole screen

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
                IFDEF   AMSTRAD_PICTURES
                and     3                       ; a pen, as on the Amstrad
                ELSE
                and     15
                ENDIF
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
