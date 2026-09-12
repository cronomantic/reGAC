; MIT License, Copyright (c) 2025 Cronomantic
;
; Filling an area, the way GAC filled, read out of the original interpreter.
;
; It is not a flood fill, which is the thing that took longest to work out.
; It walks up and down the one column the fill was started in, laying a
; horizontal run across each row, and stops the moment the point directly
; above or below is blocked.  It never spreads round a corner.  That is why a
; picture carries dozens of fill commands where a flood would need one, and
; why filling solid does not bury the drawing.  The original is at $6374.
;
; What it lays down is two bytes: the low one on even rows and the high one
; exclusive ored into it on odd ones, counting in the y of the commands.
; Solid is $00FF, wiping is $0000 and the half tone is $FFAA, which comes to
; $AA and $55 by turns.  From $6364.
;
; A run is laid down a byte at a time where it can be, because eight clear
; pixels are one byte of zero, and bit by bit at the two ends.

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
                and     %11000000
                rrca
                rrca
                rrca                    ; which third
                ld      h, a
                ld      a, e
                and     %00000111       ; which line within the character
                or      h
                or      $40
                ld      h, a
                ld      a, e
                and     %00111000       ; which row within the third
                rlca
                rlca
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
; The address is worked out once and the mask rotated from there.
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
                jr      nc, .same_byte_left
                dec     l                       ; over into the byte before
.same_byte_left:
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
                jr      nc, .same_byte_right
                inc     l                       ; over into the next byte
.same_byte_right:
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
                ld      c, a                    ; bytes after the first
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

; Give every cell the run passes through the colours in force.  A colour
; belongs to a cell of eight by eight, so this steps by bytes.
; Corrupts: everything
colour_span:
                ld      a, (fill_row)
                ld      e, a
                ld      a, (fill_left)
                ld      d, a
                ld      a, (fill_right)
                srl     a
                srl     a
                srl     a
                ld      c, a                    ; the last byte across
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
; counts rows down from the top.  The fill is the one thing that keeps working
; in the commands' own coordinates, because that is where its pattern and its
; limits are reckoned.
gfx_to_rows:
                ld      a, (gfx_y0)
                call    to_row
                ld      (gfx_y0), a
                ld      a, (gfx_y1)
                call    to_row
                ld      (gfx_y1), a
                ret

gfx_line:
                call    gfx_to_rows
                jp      draw_line

gfx_rect:
                call    gfx_to_rows
                jp      draw_rect

gfx_ellipse:
                call    gfx_to_rows
                jp      draw_ellipse

gfx_plot:
                call    gfx_to_rows
                ld      a, (gfx_x0)
                ld      d, a
                ld      a, (gfx_y0)
                ld      e, a
                jp      plot_point

gfx_fill:
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

; Wipe the picture area and give it back the colours it starts with.
; Corrupts: everything
gfx_clear:
                ld      hl, $4000
                ld      de, $4001
                ld      bc, PICTURE_ROWS * 32 - 1
                ld      (hl), 0
                ldir
                ld      hl, ATTRIBUTES
                ld      de, ATTRIBUTES + 1
                ld      bc, (PICTURE_ROWS / 8) * 32 - 1
                ld      (hl), $38               ; black on white, as it starts
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
