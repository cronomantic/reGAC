; MIT License, Copyright (c) 2025 Cronomantic
;
; The screen on an MSX1, which is not in the processor's memory at all.
;
; It lives in the video chip's own sixteen kilobytes, behind two ports: one to
; say which address, one to pass the bytes.  Reading it back costs two writes
; and a read, where a Spectrum costs seven clock cycles, and our fill reads the
; screen constantly -- it walks left and right asking what is set.
;
; So the picture is drawn into a copy in our own memory and sent across when it
; is finished.  Everything above that is then the Spectrum's, unchanged: screen
; 2 is one bit per pixel and a fill stops where a pixel is set, exactly as
; there.  What is not the Spectrum's is the colour, which belongs to eight
; pixels of one line rather than to a cell of eight by eight.
;
; The copy is kept **row by row**, thirty two bytes to a line, and not in the
; shape the chip wants -- which is the eight lines of a cell together, at
;
;       (y & $F8) * 32 + (x & $F8) + (y & 7)
;
; That was tried the other way round first, and it cost: in the chip's shape
; the byte next to this one along a row is eight further on, so the fill's
; search for the ends of a run steps with three instructions where the
; Spectrum's steps with one, twice for every cell of every row.  Measured on a
; screenful, that search took 0.32s against the Spectrum's 0.18s while writing
; the pixels and the colours cost the same on both.
;
; Laid out row by row, all of that is the Spectrum's code unchanged, and the
; shuffling into the chip's shape happens once, in the sending, which walks
; the whole copy anyway: eight bytes of a cell are eight steps of thirty two.
;
; The text goes straight to the chip: printing never reads what is there.

VDP_DATA        equ $98                 ; the bytes
VDP_ADDR        equ $99                 ; where they go, and the registers

VRAM_PATTERNS   equ $0000               ; the three tables, in the chip
VRAM_NAMES      equ $1800
VRAM_COLOURS    equ $2000
VRAM_COLOUR_ROW equ (VRAM_COLOURS - VRAM_PATTERNS) >> 8         ; rows apart
ROW_BYTES       equ 256                 ; one character row of either table

SCREEN_COLS     equ 32
TEXT_TOP        equ 16                  ; the first row the text may use
TEXT_ROWS       equ 24 - TEXT_TOP
PICTURE_ROWS    equ TEXT_TOP * 8        ; the picture, in pixel lines
PICTURE_BYTES   equ TEXT_TOP * ROW_BYTES

; And the copy we draw into: four kilobytes of patterns and four of colours,
; row by row, on a four kilobyte boundary so that the eight rows of a page are
; the high byte of an address and nothing else.
SHADOW          equ $C000
SHADOW_COLOURS  equ SHADOW + $1000

; Colours, as this machine numbers them.  A picture asks in the Spectrum's
; sixteen and gets the nearest of the fifteen here; the table that does the
; matching is in draw.asm and comes from the reference renderer, so that both
; ends of the comparison agree.
MSX_BLACK       equ 1
MSX_WHITE       equ 14
TEXT_COLOUR     equ (MSX_WHITE << 4) | MSX_BLACK

; The eight registers screen 2 wants.
screen_setup:   db      $02             ; graphics two
                db      $C0             ; sixteen K, display on, no interrupt
                db      VRAM_NAMES / $400
                db      $FF             ; the colour table, and all of it
                db      $03             ; the patterns
                db      $36             ; sprites, which are never used
                db      $07
                db      MSX_BLACK       ; the border

; Put the machine in screen 2 and lay its tables out.  The BIOS could do this,
; but the BIOS is not there once the interpreter takes all sixty four
; kilobytes for itself, so it is done here.
; Corrupts: AF, BC, DE, HL
screen_init:
                ld      hl, screen_setup
                ld      c, $80                  ; register nought
.each_register:
                ld      a, (hl)
                out     (VDP_ADDR), a
                ld      a, c
                out     (VDP_ADDR), a
                inc     hl
                inc     c
                ld      a, c
                cp      $88
                jr      nz, .each_register
                ; The name table says which pattern each cell shows: its own,
                ; counting round every 256.  That is what turns a table of
                ; characters into a bitmap.
                ld      hl, VRAM_NAMES
                call    vram_write
                ld      b, 3                    ; three blocks of 256
.each_block:
                ld      c, 0
.each_name:
                ld      a, c
                out     (VDP_DATA), a
                inc     c
                jr      nz, .each_name
                djnz    .each_block
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
                jr      cls_window

; Point the chip at address HL, to be written to.
; Corrupts: AF
vram_write:
                ld      a, l
                out     (VDP_ADDR), a
                ld      a, h
                or      $40                     ; writing, not reading
                out     (VDP_ADDR), a
                ret

; And to be read from.
; Corrupts: AF
vram_read:
                ld      a, l
                out     (VDP_ADDR), a
                ld      a, h
                out     (VDP_ADDR), a
                ret

; DE bytes of C from where the chip is pointed.
; Corrupts: AF, DE
vram_same:
                ld      a, c
                out     (VDP_DATA), a
                dec     de
                ld      a, d
                or      e
                jr      nz, vram_same
                ret

; Send the picture across: four kilobytes of patterns and four of colours.
; Once a room, not once a shape, which is what the picture interpreter's own
; hook is for.
; Corrupts: AF, BC, DE, HL
gfx_show:
                ld      hl, VRAM_PATTERNS
                call    vram_write
                ld      hl, SHADOW
                call    .a_table
                ld      hl, VRAM_COLOURS
                call    vram_write
                ld      hl, SHADOW_COLOURS
                ; fall through

; One table across, gathering as it goes: the chip wants the eight lines of a
; cell one after another, and in our copy those are eight rows apart.
.a_table:
                ld      de, SCREEN_COLS         ; from one line to the next
                ld      c, TEXT_TOP             ; sixteen rows of the picture
.each_row:
                push    hl
                ld      b, SCREEN_COLS          ; and thirty two cells in each
.each_cell:
                push    hl
                push    bc
                ld      b, 8                    ; the eight lines of the cell
.each_line:
                ld      a, (hl)
                out     (VDP_DATA), a
                add     hl, de
                djnz    .each_line
                pop     bc
                pop     hl
                inc     hl                      ; on to the next cell along
                djnz    .each_cell
                pop     hl
                inc     h                       ; and on to the next row, which
                                                ; is eight lines of thirty two
                dec     c
                jr      nz, .each_row
                ret

; Where row A of either of the chip's tables starts: a row is 256 bytes, so it
; is the high byte and nothing else.  (The fill has a row_address of its own,
; for the copy in our memory, which is not the same thing.)
; Corrupts: AF
vram_row:
                ld      h, a
                ld      l, 0
                ret

; Clear the text window, which is the last eight rows of both tables.
; Corrupts: AF, BC, DE, HL
cls_window:
                ld      a, TEXT_TOP
                call    vram_row
                call    vram_write
                ld      de, TEXT_ROWS * ROW_BYTES
                ld      c, 0
                call    vram_same
                ld      a, TEXT_TOP + VRAM_COLOUR_ROW
                call    vram_row
                call    vram_write
                ld      de, TEXT_ROWS * ROW_BYTES
                ld      c, TEXT_COLOUR
                call    vram_same
                xor     a
                ld      (cursor_x), a
                ld      a, TEXT_TOP
                ld      (cursor_y), a
                ret

; Where the cursor is, in the chip's memory.
; Corrupts: AF
cursor_address:
                ld      a, (cursor_y)
                ld      h, a
                ld      a, (cursor_x)
                add     a, a
                add     a, a
                add     a, a                    ; eight bytes to a cell
                ld      l, a
                ret

; Move the text window up by one row.  There is no copy of the text to move
; about, so it comes back out of the chip a row at a time -- which is 256
; bytes, because of how these tables are laid out.
; Corrupts: everything
scroll_window:
                ld      b, TEXT_ROWS - 1
                ld      c, TEXT_TOP                     ; the row it lands on
.each_row:
                push    bc
                ld      d, 0                            ; the patterns
                call    copy_row
                pop     bc
                push    bc
                ld      d, VRAM_COLOUR_ROW              ; and the colours
                call    copy_row
                pop     bc
                inc     c
                djnz    .each_row
                ; the row that came free is wiped
                ld      a, TEXT_TOP + TEXT_ROWS - 1
                call    vram_row
                call    vram_write
                ld      de, ROW_BYTES
                ld      c, 0
                call    vram_same
                ld      a, TEXT_TOP + TEXT_ROWS - 1 + VRAM_COLOUR_ROW
                call    vram_row
                call    vram_write
                ld      de, ROW_BYTES
                ld      c, TEXT_COLOUR
                jp      vram_same

; The row above C down onto C, in the table D rows up.
; Corrupts: everything
copy_row:
                ld      a, c
                inc     a
                add     a, d
                call    vram_row
                push    de
                push    bc
                call    vram_read
                ld      hl, line_buffer
                ld      b, 0                            ; 256 of them
.take:
                in      a, (VDP_DATA)
                ld      (hl), a
                inc     hl
                djnz    .take
                pop     bc
                pop     de
                ld      a, c
                add     a, d
                call    vram_row
                call    vram_write
                ld      hl, line_buffer
                ld      b, 0
.give:
                ld      a, (hl)
                out     (VDP_DATA), a
                inc     hl
                djnz    .give
                ret

; Start a new line, scrolling if the window is full.
; Corrupts: everything
new_line:
                xor     a
                ld      (cursor_x), a
                ld      a, (cursor_y)
                inc     a
                cp      TEXT_TOP + TEXT_ROWS
                jr      c, .fits
                call    scroll_window
                ld      a, TEXT_TOP + TEXT_ROWS - 1
.fits:
                ld      (cursor_y), a
                ret

; Draw the glyph for code A at the cursor and step right: eight bytes of
; pattern and eight of colour, which is what a line of colour costs here.
; Corrupts: everything
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
                call    cursor_address
                push    hl
                call    vram_write
                ld      b, 8
.line:
                ld      a, (de)
                out     (VDP_DATA), a
                inc     de
                djnz    .line
                pop     hl
                ld      a, h
                add     a, VRAM_COLOUR_ROW
                ld      h, a
                call    vram_write
                ld      b, 8
.colour:
                ld      a, TEXT_COLOUR
                out     (VDP_DATA), a
                djnz    .colour
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
                call    vram_write
                ld      b, 8
                xor     a
.line:
                out     (VDP_DATA), a
                djnz    .line
                ret

font_glyphs:    dw      0
font_first:     db      0
font_count:     db      0
cursor_x:       db      0
cursor_y:       db      TEXT_TOP
line_buffer:    ds      ROW_BYTES
