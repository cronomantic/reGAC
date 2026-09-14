; MIT License, Copyright (c) 2025 Cronomantic
;
; Filling an area on the Amstrad.
;
; The walk is the same as everywhere else: up and down the one column the fill
; was started in, laying a horizontal run across each row, stopping the moment
; the point directly above or below is blocked.  Two things are this machine's
; own, and both were read off it.
;
; A point blocks when its pen is no longer the pen under the seed, rather than
; when a pixel happens to be set.  That is why a fill here can run over a
; colour and stop at another, which on a one bit screen has no meaning.
;
; And what it lays down is a chequer of two pens, the ones the colour order
; names.  With the two the same it comes out solid; with two different ones it
; is how four pens are made to look like more.  Which of the two a point gets
; turns on the y of the commands, not on the screen row.

PICTURE_TOP     equ 175                 ; the y a picture reaches
PICTURE_BOTTOM  equ 48

FILL_INK        equ 0
FILL_PAPER      equ 1
FILL_SHADE      equ 2

; Whether a fill is stopped at (D across, E up the commands' way).
; Zero flag set while it is still the pen the fill started on.
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

; Put pen A down at (D across, E down in screen rows).
; Corrupts: everything but DE
put_pen:
                push    de
                push    af
                call    pixel_address
                push    hl
                call    pixel_mask
                ld      c, a
                pop     hl
                pop     af
                push    hl
                call    pen_byte
                and     c
                ld      b, a
                ld      a, c
                cpl
                pop     hl
                and     (hl)
                or      b
                ld      (hl), a
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
                ld      (fill_row), a
                ; how far it reaches to the left
                ld      a, (fill_x)
                ld      (fill_left), a
.leftwards:
                ld      a, (fill_left)
                or      a
                jr      z, .left_done
                dec     a
                ld      d, a
                ld      a, (fill_row)
                ld      e, a
                call    pen_at
                ld      hl, fill_seed
                cp      (hl)
                jr      nz, .left_done
                ld      hl, fill_left
                dec     (hl)
                jr      .leftwards
.left_done:
                ld      a, (fill_x)
                ld      (fill_right), a
.rightwards:
                ld      a, (fill_right)
                inc     a
                jr      z, .right_done          ; the edge of the picture
                ld      d, a
                ld      a, (fill_row)
                ld      e, a
                call    pen_at
                ld      hl, fill_seed
                cp      (hl)
                jr      nz, .right_done
                ld      hl, fill_right
                inc     (hl)
                jr      .rightwards
.right_done:
                ; and then lay it
                ld      a, (fill_left)
                ld      (fill_at), a
.each_point:
                ld      a, (fill_at)
                ld      d, a
                ld      hl, fill_y
                add     a, (hl)                 ; which of the two pens
                and     1
                ld      hl, gfx_pen1
                jr      z, .have_pen
                ld      hl, gfx_pen2
.have_pen:
                ld      a, (fill_row)
                ld      e, a
                ld      a, (hl)
                call    put_pen
                ld      a, (fill_at)
                ld      hl, fill_right
                cp      (hl)
                ret     z
                ld      hl, fill_at
                inc     (hl)
                jr      .each_point

; -- what the picture interpreter calls -------------------------------------

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

; The picture is finished.  This machine draws straight at its screen, so
; there is nothing to send anywhere.
gfx_show:
                ret

fill_x:         db      0
fill_seed_y:    db      0
fill_y:         db      0
fill_row:       db      0
fill_left:      db      0
fill_right:     db      0
fill_at:        db      0
fill_seed:      db      0
