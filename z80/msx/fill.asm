; MIT License, Copyright (c) 2025 Cronomantic
;
; Filling an area on an MSX1, which is the Spectrum's fill.
;
; The walk is the same, the pattern is the same and the rule is the same, and
; because the copy it draws into is kept row by row -- screen.asm says why --
; a run is walked and laid down with the same one byte steps.
;
; The one thing that is this machine's own: the colour goes down once a row
; rather than once every eight, because here a colour belongs to eight pixels
; of one line and not to a cell of eight by eight.

PICTURE_TOP     equ 175                 ; the y a picture reaches
PICTURE_BOTTOM  equ 48
FILL_INK        equ 0
FILL_PAPER      equ 1
FILL_SHADE      equ 2

; The address of column zero of row E, in HL.  The thirty two bytes of the row
; follow in L, so nothing after this needs the address working out again.
; Corrupts: AF
row_address:
                ld      a, e
                rrca
                rrca
                rrca
                and     %00011111               ; which page of eight rows
                add     a, SHADOW >> 8
                ld      h, a
                ld      a, e
                and     7
                rrca
                rrca
                rrca                            ; the row in it, times thirty two
                ld      l, a
                ret

; Whether a fill is stopped at (D across, E up), in the coordinates of the
; commands.  Zero flag clear if it is.
; Corrupts: AF, BC, HL
blocked:
                push    de
                ld      a, e
                call    to_row
                ld      e, a
                call    is_boundary
                pop     de
                ret

; Fill from (D across, E up).
; Corrupts: everything
flood_fill:
                ld      a, d
                ld      (fill_x), a             ; laying a run treads on D
                call    blocked
                ret     nz
                ld      a, e
                ld      (fill_seed_y), a
                ld      (fill_y), a
.upwards:
                ld      a, (fill_y)
                cp      PICTURE_TOP + 1
                jr      nc, .downwards
                ld      e, a
                ld      a, (fill_x)
                ld      d, a
                call    blocked
                jr      nz, .downwards
                call    fill_run
                ld      hl, fill_y
                inc     (hl)
                jr      .upwards
.downwards:
                ld      a, (fill_seed_y)
                dec     a
                ld      (fill_y), a
.each_below:
                ld      a, (fill_y)
                cp      PICTURE_BOTTOM
                ret     c
                ld      e, a
                ld      a, (fill_x)
                ld      d, a
                call    blocked
                ret     nz
                call    fill_run
                ld      hl, fill_y
                dec     (hl)
                jr      .each_below

; Lay the pattern across the run of clear pixels through (D across, fill_y up).
; Corrupts: everything
fill_run:
                ld      a, (fill_x)
                ld      d, a
                ; the byte for this row: the low half, turned about on odd rows
                ld      a, (fill_y)
                and     1
                ld      a, (fill_low)
                jr      z, .have_pattern
                ld      hl, fill_high
                xor     (hl)
.have_pattern:
                ld      (span_pattern), a
                ld      a, (fill_y)
                call    to_row
                ld      (fill_row), a
                ld      e, a
                call    span_extent
                call    colour_span
                jp      mark_span

; How far the clear run through (D, E) reaches, into fill_left and fill_right.
;
; Whenever the walk steps into a byte it has not looked at yet, it looks at the
; whole byte first: eight clear pixels are a byte of zero, and one comparison
; takes all eight.  Only a byte with something in it is picked apart pixel by
; pixel, which happens twice in a run, at its two ends.
; Corrupts: everything
span_extent:
                call    row_address
                ld      (row_base), hl
                ld      a, d
                ld      (fill_left), a
                ld      (fill_right), a
                call    point_at
.leftwards:
                ld      a, (fill_left)
                or      a
                jr      z, .left_done
                rlc     b                       ; one pixel to the left
                jr      nc, .pixel_left
                dec     l                       ; over into the byte before
                ld      a, (hl)
                or      a
                jr      nz, .pixel_left         ; something in it: one at a time
                ld      a, (fill_left)          ; the walk arrived at a cell
                sub     8                       ; boundary, so this byte is all
                ld      (fill_left), a          ; of the next eight pixels
                ld      b, %10000000            ; and we stand at its first
                jr      .leftwards
.pixel_left:
                ld      a, (hl)
                and     b
                jr      nz, .left_done
                ld      a, (fill_left)
                dec     a
                ld      (fill_left), a
                jr      .leftwards
.left_done:
                ld      a, d
                ld      (fill_right), a
                call    point_at
.rightwards:
                ld      a, (fill_right)
                inc     a
                jr      z, .right_done          ; the edge of the screen
                rrc     b                       ; one pixel to the right
                jr      nc, .pixel_right
                inc     l                       ; over into the next byte
                ld      a, (hl)
                or      a
                jr      nz, .pixel_right
                ld      a, (fill_right)
                add     a, 8
                ld      (fill_right), a
                ld      b, %00000001            ; standing at its last pixel
                jr      .rightwards
.pixel_right:
                ld      a, (hl)
                and     b
                ret     nz
                ld      a, (fill_right)
                inc     a
                ld      (fill_right), a
                jr      .rightwards
.right_done:
                ret

; Point HL at the byte holding column A of the row, with B the bit mask.
; Corrupts: AF
point_at:
                push    de
                ld      e, a
                srl     a
                srl     a
                srl     a                       ; which byte across
                ld      hl, (row_base)
                or      l
                ld      l, a
                ld      a, e
                and     7
                ld      de, bit_masks
                add     a, e
                ld      e, a
                ld      a, (de)
                ld      b, a
                pop     de
                ret

; Work out where the run sits in bytes: HL at its first byte, C how many whole
; bytes follow, and the masks for the two ends.
; Corrupts: AF, DE
span_bytes:
                ld      a, (fill_row)
                ld      e, a
                call    row_address
                ld      (row_base), hl
                ld      a, (fill_left)
                and     7
                ld      de, mask_from
                add     a, e
                ld      e, a
                ld      a, (de)
                ld      (span_first), a
                ld      a, (fill_right)
                and     7
                ld      de, mask_to
                add     a, e
                ld      e, a
                ld      a, (de)
                ld      (span_last), a
                ld      a, (fill_right)
                srl     a
                srl     a
                srl     a
                ld      c, a
                ld      a, (fill_left)
                srl     a
                srl     a
                srl     a
                ld      b, a
                ld      hl, (row_base)
                or      l
                ld      l, a
                ld      a, c
                sub     b
                ld      c, a                    ; cells after the first
                ret

; Put the pattern down over the run, eight pixels at a stroke where it can.
; Corrupts: everything
mark_span:
                call    span_bytes
                ld      a, c
                or      a
                jr      nz, .several
                ld      a, (span_first)
                ld      b, a
                ld      a, (span_last)
                and     b
                jp      blend_byte
.several:
                ld      a, (span_first)
                call    blend_byte
                inc     l
                dec     c
                jr      z, .last
.middle:
                ld      a, (span_pattern)
                ld      (hl), a                 ; a whole byte, eight pixels
                inc     l
                dec     c
                jr      nz, .middle
.last:
                ld      a, (span_last)
                jp      blend_byte

; Put the pattern where the mask says, leaving the rest of the byte alone.
; Corrupts: AF, B, D
blend_byte:
                ld      b, a
                cpl
                and     (hl)
                ld      d, a                    ; C carries the byte count
                ld      a, (span_pattern)
                and     b
                or      d
                ld      (hl), a
                ret

; Give every cell the run passes through the colours in force.  Here that is
; once a row and not once every eight rows, because a colour belongs to eight
; pixels of one line.
;
; Almost always the same byte goes into every cell of the run, because the
; colours in force do not depend on what is already there.  Then the whole run
; is one address worked out once and a byte written along it.
; Corrupts: everything
colour_span:
                ld      a, (fill_row)
                ld      e, a
                ld      a, (fill_left)
                ld      d, a
                ld      a, (colour_varies)      ; settled once for the shape
                or      a
                jr      nz, .cell_by_cell
                ld      a, (colour_now)
                or      a                       ; and the carry off with it
                push    af
                call    pixel_address           ; the first cell of the run
                call    to_colour
                pop     af
                ld      c, a                    ; the byte all of them get
                ld      a, (fill_right)
                srl     a
                srl     a
                srl     a
                ld      b, a                    ; the last cell across
                ld      a, d
                srl     a
                srl     a
                srl     a                       ; the first
.each_byte:
                ld      (hl), c
                cp      b
                ret     z
                inc     a
                inc     l
                jr      .each_byte
.cell_by_cell:
                ld      a, (fill_right)
                srl     a
                srl     a
                srl     a
                ld      c, a                    ; the last cell across
.each_cell:
                push    bc
                push    de
                call    colour_cell
                pop     de
                pop     bc
                ld      a, d
                srl     a
                srl     a
                srl     a
                cp      c
                ret     z
                ld      a, d
                and     %11111000
                add     a, 8
                ld      d, a
                jr      .each_cell

; -- what the picture interpreter calls -------------------------------------

; The y in the commands counts up from the bottom of the screen; the screen
; counts rows down from the top.  Everything that draws an outline works in
; sixteen bit rows, so that a point above the top stays above it; the fill is
; the one thing that keeps working in the commands' own coordinates, because
; that is where its pattern and its limits are reckoned.
gfx_to_words:
                ld      a, (gfx_x0)
                ld      l, a
                ld      h, 0
                ld      (lin_x0), hl
                ld      a, (gfx_y0)
                call    row_of
                ld      (lin_y0), hl
                ld      a, (gfx_x1)
                ld      l, a
                ld      h, 0
                ld      (lin_x1), hl
                ld      a, (gfx_y1)
                call    row_of
                ld      (lin_y1), hl
                ret

gfx_line:
                call    settle_colours
                call    gfx_to_words
                jp      draw_line

gfx_rect:
                call    settle_colours
                call    gfx_to_words
                jp      draw_rect

gfx_ellipse:
                call    settle_colours
                call    gfx_to_words
                jp      draw_ellipse

gfx_plot:
                call    settle_colours
                call    gfx_to_words
                ld      hl, (lin_x0)
                call    clamp_x
                ld      d, l
                ld      hl, (lin_y0)
                call    clamp_row
                ld      e, l
                jp      plot_point

gfx_fill:
                call    settle_colours
                ld      a, (gfx_x0)
                ld      d, a
                ld      a, (gfx_y0)
                ld      e, a
                jp      flood_fill

; Choose what a fill lays down.  A says which of the three.
; Corrupts: AF, DE, HL
set_fill_pattern:
                add     a, a
                ld      e, a
                ld      d, 0
                ld      hl, fill_patterns
                add     hl, de
                ld      a, (hl)
                ld      (fill_low), a
                inc     hl
                ld      a, (hl)
                ld      (fill_high), a
                ret

; Wipe the picture and give it back the colours it starts in.  Both copies,
; because what the video chip is shown is what these hold.
; Corrupts: everything
gfx_clear:
                ld      hl, SHADOW
                ld      de, SHADOW + 1
                ld      bc, PICTURE_BYTES - 1
                ld      (hl), 0
                ldir
                ld      hl, SHADOW_COLOURS
                ld      de, SHADOW_COLOURS + 1
                ld      bc, PICTURE_BYTES - 1
                ld      a, (msx_colours)        ; black on white, as it starts
                rlca
                rlca
                rlca
                rlca
                push    hl
                ld      hl, msx_colours + 7
                or      (hl)
                pop     hl
                ld      (hl), a
                ldir
                ret

; Solid, wiped, half tone: the three pairs the original holds at $6364.
fill_patterns:  db      $FF, $00
                db      $00, $00
                db      $AA, $FF

; Every bit from this one rightwards, and every bit up to this one.
mask_from:      db      %11111111, %01111111, %00111111, %00011111
                db      %00001111, %00000111, %00000011, %00000001
mask_to:        db      %10000000, %11000000, %11100000, %11110000
                db      %11111000, %11111100, %11111110, %11111111

fill_x:         db      0
fill_seed_y:    db      0
fill_y:         db      0
fill_row:       db      0
fill_left:      db      0
fill_right:     db      0
fill_low:       db      0
fill_high:      db      0
span_pattern:   db      0
span_first:     db      0
span_last:      db      0
row_base:       dw      0
