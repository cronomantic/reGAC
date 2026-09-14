; MIT License, Copyright (c) 2025 Cronomantic
;
; Filling an area on the PCW, the way GAC filled.
;
; It is not a flood fill.  It walks up and down the one column the fill was
; started in, laying a horizontal run across each row, and stops the moment
; the point directly above or below is blocked.  It never spreads round a
; corner.  The original is at $6374 and what it lays down is at $6364.
;
; Here a run goes down twice: once in the mask, which is the picture as the
; Spectrum would have held it and is what stops the next fill, and once on the
; screen, which carries no colour and so lays down a dither instead.
;
; That dither is one byte for the whole run.  The ink's dither and the paper's
; both repeat every two points, and the pattern GAC lays down is itself either
; solid, empty or a chequer, so whatever the pattern takes from one and leaves
; to the other repeats every two points as well.  Work it out once for the row
; and the run is a byte written along it, which is what makes a fill
; affordable.

PICTURE_TOP     equ 175                 ; the y a picture reaches
PICTURE_BOTTOM  equ 48

FILL_INK        equ 0
FILL_PAPER      equ 1
FILL_SHADE      equ 2

; The address in the mask of column zero of row E, in HL.  The thirty two
; bytes of the row follow in L, so nothing after this needs it worked out
; again.
; Corrupts: AF
mask_row:
                ld      a, e
                and     7
                rrca
                rrca
                rrca                    ; the row inside the page, times 32
                ld      l, a
                ld      a, e
                rrca
                rrca
                rrca
                and     %00011111       ; and which page of eight rows
                add     a, MASK_AT >> 8
                ld      h, a
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
                call    paint_span
                jp      mark_span

; How far the clear run through (D, E) reaches, into fill_left and fill_right.
; The address is worked out once and the mask rotated from there.
;
; Whenever the walk steps into a byte it has not looked at yet, it looks at the
; whole byte first: eight clear pixels are a byte of zero, and one comparison
; takes all eight.  Only a byte with something in it is picked apart pixel by
; pixel, which happens twice in a run, at its two ends.
; Corrupts: everything
span_extent:
                call    mask_row
                ld      (mask_base), hl
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
                ld      a, (fill_left)          ; the walk arrived at a byte
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

; Point HL at the byte of the mask holding column A of the row, with B the bit.
; Corrupts: AF
point_at:
                push    de
                ld      e, a
                srl     a
                srl     a
                srl     a                       ; which byte across
                ld      hl, (mask_base)
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

; Work out where the run sits in the mask: HL at its first byte, C how many
; whole bytes follow, and the masks for the two ends.
; Corrupts: AF, DE
span_bytes:
                ld      a, (fill_row)
                ld      e, a
                call    mask_row
                ld      (mask_base), hl
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
                ld      hl, (mask_base)
                or      l
                ld      l, a
                ld      a, c
                sub     b
                ld      c, a                    ; bytes after the first
                ret

; Put the pattern down over the run of the mask, eight pixels at a stroke
; where it can.
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

; Lay the run down on the screen, which is the dither the two colours and the
; pattern come to.  Four points of the picture to a byte, and the bytes of a
; row go up by eight, because the eight lines of a column are together.
; Corrupts: everything
paint_span:
                ld      a, (fill_row)
                ld      e, a
                ld      a, (ink_level)
                call    dither_for
                ld      b, a                    ; what the ink lays on this row
                ld      a, (fill_row)
                ld      e, a
                ld      a, (paper_level)
                call    dither_for
                ld      c, a                    ; and what the paper lays
                ld      a, (span_pattern)
                and     b
                ld      b, a                    ; the pattern's share of the ink
                ld      a, (span_pattern)
                cpl
                and     c
                or      b                       ; and the rest from the paper
                rlca
                rlca
                and     3                       ; two points tell the whole byte
                ld      hl, pair_bytes
                add     a, l
                ld      l, a
                ld      a, 0
                adc     a, h
                ld      h, a
                ld      a, (hl)
                ld      (screen_byte), a
                ; where it goes, and how many bytes of the screen it covers
                ld      a, (fill_left)
                ld      d, a
                ld      a, (fill_row)
                ld      e, a
                call    screen_address          ; HL the first byte of the run
                ld      a, (fill_left)
                and     3
                ld      de, pair_from
                add     a, e
                ld      e, a
                ld      a, (de)
                ld      c, a                    ; the mask of its first byte
                ld      a, (fill_right)
                and     3
                ld      de, pair_to
                add     a, e
                ld      e, a
                ld      a, (de)
                ld      (screen_last), a
                ld      a, (fill_right)
                rrca
                rrca
                and     %00111111
                ld      e, a
                ld      a, (fill_left)
                rrca
                rrca
                and     %00111111
                ld      d, a
                ld      a, e
                sub     d
                ld      d, a                    ; bytes after the first
                or      a
                jr      nz, .several
                ld      a, (screen_last)
                and     c
                jr      .blend
.several:
                ld      a, c
                call    .blend
                ld      bc, 8
                add     hl, bc
                dec     d
                jr      z, .last
.middle:
                ld      a, (screen_byte)
                ld      (hl), a
                ld      bc, 8
                add     hl, bc
                dec     d
                jr      nz, .middle
.last:
                ld      a, (screen_last)
.blend:
                ld      b, a
                cpl
                and     (hl)
                ld      c, a
                ld      a, (screen_byte)
                and     b
                or      c
                ld      (hl), a
                ret

; -- what the picture interpreter calls -------------------------------------

; The picture's half of the screen goes into the map, and the colours in force
; are settled into levels of light, once for the whole shape.
; Corrupts: AF, BC, HL
gfx_ready:
                ld      a, PICTURE_BANK
                call    screen_bank
                jp      settle_colours

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
                call    gfx_ready
                call    gfx_to_words
                jp      draw_line

gfx_rect:
                call    gfx_ready
                call    gfx_to_words
                jp      draw_rect

gfx_ellipse:
                call    gfx_ready
                call    gfx_to_words
                jp      draw_ellipse

gfx_plot:
                call    gfx_ready
                call    gfx_to_words
                ld      hl, (lin_x0)
                call    clamp_x
                ld      d, l
                ld      hl, (lin_y0)
                call    clamp_row
                ld      e, l
                jp      plot_point

gfx_fill:
                call    gfx_ready
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

; Wipe the picture: the mask to nothing and the screen to white paper, which
; is what it starts in.  The margins to either side are left dark.
; Corrupts: everything
gfx_clear:
                ld      a, PICTURE_BANK
                call    screen_bank
                ld      hl, MASK_AT
                ld      de, MASK_AT + 1
                ld      bc, PICTURE_ROWS * 32 - 1
                ld      (hl), 0
                ldir
                ld      c, SCREEN_ROWS
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

; The same two for the screen, where a byte is four points of the picture.
pair_from:      db      %11111111, %00111111, %00001111, %00000011
pair_to:        db      %11000000, %11110000, %11111100, %11111111

; A row's dither, four points of it, doubled into the byte it becomes.  Two
; points are enough to know it, because every dither here repeats every two.
pair_bytes:     db      $00, $33, $CC, $FF

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
screen_byte:    db      0
screen_last:    db      0
mask_base:      dw      0
