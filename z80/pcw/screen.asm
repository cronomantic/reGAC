; MIT License, Copyright (c) 2025 Cronomantic
;
; The screen on the Amstrad PCW, which is not a screen but a table.
;
; The video does not read a block of memory: it reads 256 entries of a roller
; RAM, one for each scan line, and each says where that line's bytes are.  So
; the layout is ours to choose, and this chooses the plainest one there is:
; thirty two rows of eight lines, one after another, the top sixteen for the
; picture and the bottom sixteen for the text.
;
; Inside a row the shape is the machine's, not ours.  The video reads every
; eighth byte, so the eight lines of a byte column are the eight bytes in a
; row, and a row of ninety columns is 720 bytes.  That makes an address as
; cheap as the Spectrum's:
;
;       row base + 8 * (x / 8) + (y & 7)
;
; The picture is drawn twice as wide as it is written, because a pixel here is
; about half as wide as it is tall, so its 256 points take 512 pixels: sixty
; four of the ninety columns, centred, which leaves thirteen columns of margin
; on each side and the same sixty four for the text underneath.
;
; The two halves live in different banks, and only one of them is in the map at
; a time.  Nothing on this machine forces that -- there is memory enough for
; both -- but it leaves a whole sixteen kilobyte slot free for the database,
; and the video reads the banks whether the processor can see them or not.

SCREEN_AT       equ $8000               ; the slot both halves are seen through
SCREEN_SLOT     equ $F2                 ; and the port that says which is there
BANK_MARK       equ $80                 ; a bank number is given with this on
PICTURE_BANK    equ 2
TEXT_BANK       equ 4

ROW_BYTES       equ 720                 ; one row of eight lines
SCREEN_COLS     equ 64                  ; the columns a picture or a line uses
MARGIN          equ 13                  ; and the ones to the left of them
SCREEN_ROWS     equ 16                  ; rows to each half
PICTURE_ROWS    equ SCREEN_ROWS * 8     ; the picture in pixel lines
SCREEN_BYTES    equ SCREEN_ROWS * ROW_BYTES

; Where a row starts, as the video counts: sixteen bytes to a block, three bits
; of line inside it, and the bank on top.  The eight lines of a row are eight
; entries in a row, and the next row is 720 bytes on, which is 360 entries.
ROLLER_AT       equ $FC00               ; clear of the keyboard, which the
                                        ; controller writes at the very top
ROLLER_PORT     equ $F5                 ; bank = value >> 5, offset = 512 * low
ROLLER_VALUE    equ (3 << 5) | ((ROLLER_AT & $3FFF) / 512)
ROLLER_STEP     equ ROW_BYTES / 2       ; from one row's entry to the next
SCROLL_PORT     equ $F6                 ; which entry it starts painting at
DISPLAY_PORT    equ $F7
DISPLAY_ON      equ %01000000           ; and bit seven would turn it inside out

TEXT_ROWS       equ SCREEN_ROWS
PAPER_BYTE      equ $FF                 ; white, because every lit pixel is

; Set the screen up: the table the video reads, both halves wiped, and the
; picture's half in the map.  The font comes out of the database as it does on
; every machine.
; Corrupts: AF, BC, DE, HL
screen_init:
                ld      hl, ROLLER_AT
                ld      de, PICTURE_BANK << 13
                call    .a_half
                ld      de, TEXT_BANK << 13
                call    .a_half
                ld      a, ROLLER_VALUE
                out     (ROLLER_PORT), a
                xor     a
                out     (SCROLL_PORT), a
                ld      a, DISPLAY_ON
                out     (DISPLAY_PORT), a
                ; both halves start dark, margins and all, and only the parts
                ; that carry something are made white afterwards
                ld      a, TEXT_BANK
                call    screen_bank
                call    .wipe
                ld      a, PICTURE_BANK
                call    screen_bank
                call    .wipe
                ; the font, and the cursor at the top of the text
                ld      a, SECTION_FONT
                call    db_section
                ld      a, (hl)
                ld      (font_first), a
                inc     hl
                ld      a, (hl)
                ld      (font_count), a
                inc     hl
                ld      (font_glyphs), hl
                jr      cls_window

.a_half:
                ld      c, SCREEN_ROWS
.each_row:
                ld      b, 8                    ; the eight lines of the row
.each_line:
                ld      (hl), e
                inc     hl
                ld      (hl), d
                inc     hl
                inc     de
                djnz    .each_line
                ld      a, e                    ; and on to the next row, which
                add     a, (ROLLER_STEP - 8) & $FF      ; is eight entries
                ld      e, a                    ; further on than we stand
                ld      a, d
                adc     a, (ROLLER_STEP - 8) >> 8
                ld      d, a
                dec     c
                jr      nz, .each_row
                ret

.wipe:
                ld      hl, SCREEN_AT
                ld      de, SCREEN_AT + 1
                ld      bc, SCREEN_BYTES - 1
                ld      (hl), 0
                ldir
                ret

; Put bank A in the slot the screen is seen through.
; Corrupts: AF
screen_bank:
                or      BANK_MARK
                out     (SCREEN_SLOT), a
                ret

; Where row A of a half starts, in HL: the first byte of the first column the
; text and the picture use, which is the same for both halves.
; Corrupts: AF, DE
row_base:
                add     a, a
                ld      e, a
                ld      d, 0
                ld      hl, screen_rows
                add     hl, de
                ld      a, (hl)
                inc     hl
                ld      h, (hl)
                ld      l, a
                ret

screen_rows:
row_at = SCREEN_AT + MARGIN * 8
                DUP     SCREEN_ROWS
                dw      row_at
row_at = row_at + ROW_BYTES
                EDUP

; Clear the text window, which is white paper, and put the cursor at its top
; left.  The margins stay dark: the paper is the width of the picture.
; Corrupts: AF, BC, DE, HL
cls_window:
                ld      a, TEXT_BANK
                call    screen_bank
                ld      c, TEXT_ROWS
                xor     a
.each_row:
                push    af
                push    bc
                call    row_base
                ld      d, h
                ld      e, l
                inc     de
                ld      (hl), PAPER_BYTE
                ld      bc, SCREEN_COLS * 8 - 1
                ldir
                pop     bc
                pop     af
                inc     a
                dec     c
                jr      nz, .each_row
                xor     a
                ld      (cursor_x), a
                ld      (cursor_y), a
                ret

; Where the cursor is, in HL.
; Corrupts: AF, DE
cursor_address:
                ld      a, (cursor_y)
                call    row_base
                ld      a, (cursor_x)           ; sixty four columns of eight
                ld      e, a                    ; bytes do not fit in one byte
                ld      d, 0
                ex      de, hl
                add     hl, hl
                add     hl, hl
                add     hl, hl
                add     hl, de
                ret

; Move the text window up by one row.  A row is 720 bytes and the eight lines
; of it are interleaved, so the whole row moves in one go and nothing has to
; be done a line at a time.
; Corrupts: AF, BC, DE, HL
scroll_window:
                ld      a, TEXT_BANK
                call    screen_bank
                ld      c, TEXT_ROWS - 1
                xor     a
                call    row_base                ; where the first row lands
.each_row:
                push    bc
                ld      d, h
                ld      e, l
                ld      bc, ROW_BYTES
                add     hl, bc                  ; and the row above it, which
                push    hl                      ; is simply 720 bytes on
                ld      bc, SCREEN_COLS * 8
                ldir
                pop     hl
                pop     bc
                dec     c
                jr      nz, .each_row
                ; the row that came free is the last one, and HL is at it
                ld      d, h
                ld      e, l
                inc     de
                ld      (hl), PAPER_BYTE
                ld      bc, SCREEN_COLS * 8 - 1
                ldir
                ret

; Start a new line, scrolling if the window is full.
; Corrupts: AF, BC, DE, HL
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

; Draw the glyph for code A at the cursor and step right.  The eight lines of
; a column are eight bytes in a row, so a glyph goes down in one loop; it goes
; down inside out, because the text is black on white paper.
; Corrupts: AF, BC, DE, HL
print_char:
                push    af
                ld      a, TEXT_BANK
                call    screen_bank
                pop     af
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
.line:
                ld      a, (hl)
                cpl
                ld      (de), a
                inc     hl
                inc     de
                djnz    .line
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
                ld      a, TEXT_BANK
                call    screen_bank
                call    cursor_address
                ld      b, 8
.line:
                ld      (hl), PAPER_BYTE
                inc     hl
                djnz    .line
                ret

font_glyphs:    dw      0
font_first:     db      0
font_count:     db      0
cursor_x:       db      0
cursor_y:       db      0
