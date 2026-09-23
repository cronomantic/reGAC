; MIT License, Copyright (c) 2025 Cronomantic
;
; Filling an area of a picture off an Amstrad on a Spectrum Next, with the
; Amstrad's rules -- read off that machine, and written up in
; z80/cpc/fill.asm and doc/graficos.md.
;
; The walk is the same as everywhere else: up and down the one column the fill
; was started in, laying a horizontal run across each row, stopping the moment
; the point directly above or below is blocked.  A point blocks when its pen is
; no longer the pen under the seed; and what a fill lays down is a chequer of
; the two pens the colour order names, the one or the other as the column and
; the y of the commands add up even or odd.
;
; Here a pixel is a byte and a row of the picture is 256 of them in one page
; of the window, so a run is walked and laid by stepping L.

PICTURE_TOP     equ 175                 ; the y a picture reaches
PICTURE_BOTTOM  equ 48

FILL_INK        equ 0
FILL_PAPER      equ 1
FILL_SHADE      equ 2

; Whether a fill is stopped at (D across, E up the commands' way).  Zero flag
; set while it is still the pen the fill started on.
; Corrupts: AF, BC, HL
blocked:
                push    de
                ld      a, e
                call    to_row
                ld      e, a
                call    pen_at
                ld      hl, fill_seed
                cp      (hl)
                pop     de
                ret

; Fill from (D across, E up).
; Corrupts: everything
flood_fill:
                ld      a, d
                ld      (fill_x), a
                push    de
                ld      a, e
                call    to_row
                ld      e, a
                call    pen_at
                ld      (fill_seed), a
                pop     de
                cp      255
                ret     z                       ; the seed is off the picture
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

; Lay the two pens across the run through (fill_x, fill_y).
; Corrupts: everything
fill_run:
                ld      a, (fill_y)
                call    to_row
                ld      e, a
                ld      a, (fill_x)
                ld      d, a
                call    colour_address          ; HL at the seed, L its x
                ld      a, (fill_seed)
                ld      b, a
                ; how far to the left, stepping L down while the pen holds
                ld      c, l
.leftwards:
                ld      a, l
                or      a
                jr      z, .left_done           ; the edge of the picture
                dec     l
                ld      a, (hl)
                cp      b
                jr      z, .leftwards
                inc     l                       ; the one before was the last
.left_done:
                ld      a, l
                ld      (fill_left), a
                ; and to the right, from the seed again
                ld      l, c
.rightwards:
                ld      a, l
                inc     a
                jr      z, .right_done          ; the edge of the picture
                inc     l
                ld      a, (hl)
                cp      b
                jr      z, .rightwards
                dec     l
.right_done:
                ld      a, l
                ld      (fill_right), a
                ; The two pens, the first where the column and the y add up
                ; even: which one a point gets turns on the y of the commands,
                ; as the original picks between its two pattern bytes with bit
                ; nought of that y, and not on the screen row.
                ld      a, (gfx_pen1)
                and     3
                ld      d, a
                ld      a, (gfx_pen2)
                and     3
                ld      e, a
                ld      a, (fill_left)
                ld      l, a
                ld      c, a
                ld      a, (fill_y)
                add     a, c
                rra                             ; odd: the run starts on the
                jr      nc, .lined_up           ; second pen
                ld      a, d
                ld      d, e
                ld      e, a
.lined_up:
                ld      a, (fill_right)
                sub     l
                inc     a
                ld      b, a                    ; the run's length, nought
.lay:                                           ; for the whole 256
                ld      (hl), d
                inc     l
                ld      a, d
                ld      d, e
                ld      e, a
                djnz    .lay
                ret

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
                call    gfx_to_words
                jp      draw_line

gfx_rect:
                call    gfx_to_words
                jp      draw_rect

gfx_ellipse:
                call    gfx_to_words
                jp      draw_ellipse

gfx_plot:
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

; Which of the three fills this is.  The Amstrad has only one: what it lays
; down is whatever the colour order last named, so the three come to the same
; thing here and the pens are left alone.
set_fill_pattern:
                ret

fill_x:         db      0
fill_seed_y:    db      0
fill_y:         db      0
fill_left:      db      0
fill_right:     db      0
fill_seed:      db      0
