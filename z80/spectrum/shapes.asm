; MIT License, Copyright (c) 2025 Cronomantic
;
; Rectangles and ellipses, built on the straight line.
;
; The ellipse is walked round in sixty four steps off a table of sines, with
; whole numbers throughout.  Nothing smoother, because the reference renderer
; in Python does exactly the same sum and the two are compared pixel for
; pixel.  Every ellipse in the eight adventures fits inside 36 pixels, where
; the steps are shorter than the pixels anyway.

ELLIPSE_STEPS   equ 64

; The outline of a rectangle, as four straight lines.
; Corrupts: everything
draw_rect:
                ld      a, (gfx_x0)
                ld      (rect_x0), a
                ld      a, (gfx_y0)
                ld      (rect_y0), a
                ld      a, (gfx_x1)
                ld      (rect_x1), a
                ld      a, (gfx_y1)
                ld      (rect_y1), a
                call    .whole_box              ; the top
                ld      a, (rect_y0)
                ld      (gfx_y1), a
                call    draw_line
                call    .whole_box              ; the bottom
                ld      a, (rect_y1)
                ld      (gfx_y0), a
                call    draw_line
                call    .whole_box              ; the left side
                ld      a, (rect_x0)
                ld      (gfx_x1), a
                call    draw_line
                call    .whole_box              ; and the right
                ld      a, (rect_x1)
                ld      (gfx_x0), a
                jp      draw_line
.whole_box:
                ld      a, (rect_x0)
                ld      (gfx_x0), a
                ld      a, (rect_y0)
                ld      (gfx_y0), a
                ld      a, (rect_x1)
                ld      (gfx_x1), a
                ld      a, (rect_y1)
                ld      (gfx_y1), a
                ret

rect_x0:        db      0
rect_y0:        db      0
rect_x1:        db      0
rect_y1:        db      0

; B times C, unsigned, into HL.
; Corrupts: AF, BC, DE
multiply:
                ld      hl, 0
                ld      d, 0
                ld      e, c
                ld      a, b
                or      a
                ret     z
                ld      b, 8
.step:
                rra
                jr      nc, .no_add
                add     hl, de
.no_add:
                sla     e
                rl      d
                djnz    .step
                ret

; Radius B times the sine in C, divided by 128 and cut towards zero, signed,
; back in A.  Nine bits of the product, which is what the divide comes to.
; Corrupts: everything
sine_scaled:
                ld      a, c
                or      a
                jp      p, .positive
                neg
                ld      c, a
                call    multiply
                add     hl, hl
                ld      a, h
                neg
                ret
.positive:
                call    multiply
                add     hl, hl
                ld      a, h
                ret

; An ellipse inside the box in gfx_x0..gfx_y1.
; Corrupts: everything
draw_ellipse:
                call    order_box
                ; the middle and the two radii
                ld      a, (gfx_x0)
                ld      b, a
                ld      a, (gfx_x1)
                add     a, b
                rra                             ; carry carries bit eight
                ld      (ell_cx), a
                ld      a, (gfx_x0)
                ld      b, a
                ld      a, (gfx_x1)
                sub     b
                srl     a
                ld      (ell_rx), a
                ld      a, (gfx_y0)
                ld      b, a
                ld      a, (gfx_y1)
                add     a, b
                rra
                ld      (ell_cy), a
                ld      a, (gfx_y0)
                ld      b, a
                ld      a, (gfx_y1)
                sub     b
                srl     a
                ld      (ell_ry), a
                ; a box with no room in it is just a point
                ld      a, (ell_rx)
                ld      b, a
                ld      a, (ell_ry)
                or      b
                jr      nz, .walk_round
                ld      a, (ell_cx)
                ld      d, a
                ld      a, (ell_cy)
                ld      e, a
                jp      plot_point
.walk_round:
                xor     a
                ld      (ell_step), a
                call    ellipse_point
                ld      a, (ell_px)
                ld      (ell_first_x), a
                ld      a, (ell_py)
                ld      (ell_first_y), a
                ld      b, ELLIPSE_STEPS - 1
.each:
                push    bc
                ld      a, (ell_px)
                ld      (gfx_x0), a
                ld      a, (ell_py)
                ld      (gfx_y0), a
                ld      hl, ell_step
                inc     (hl)
                call    ellipse_point
                ld      a, (ell_px)
                ld      (gfx_x1), a
                ld      a, (ell_py)
                ld      (gfx_y1), a
                call    draw_segment
                pop     bc
                djnz    .each
                ; and close it back to where it began
                ld      a, (ell_px)
                ld      (gfx_x0), a
                ld      a, (ell_py)
                ld      (gfx_y0), a
                ld      a, (ell_first_x)
                ld      (gfx_x1), a
                ld      a, (ell_first_y)
                ld      (gfx_y1), a
                ; fall through

; A straight line, or a single point when both ends are the same place.
draw_segment:
                ld      a, (gfx_x0)
                ld      b, a
                ld      a, (gfx_x1)
                cp      b
                jp      nz, draw_line
                ld      a, (gfx_y0)
                ld      b, a
                ld      a, (gfx_y1)
                cp      b
                jp      nz, draw_line
                ld      a, (gfx_x0)
                ld      d, a
                ld      a, (gfx_y0)
                ld      e, a
                jp      plot_point

; Put the box the right way round, smaller corner first.
order_box:
                ld      a, (gfx_x0)
                ld      b, a
                ld      a, (gfx_x1)
                cp      b
                jr      nc, .x_done
                ld      (gfx_x0), a
                ld      a, b
                ld      (gfx_x1), a
.x_done:
                ld      a, (gfx_y0)
                ld      b, a
                ld      a, (gfx_y1)
                cp      b
                ret     nc
                ld      (gfx_y0), a
                ld      a, b
                ld      (gfx_y1), a
                ret

; Where step ell_step falls on the ellipse, into ell_px and ell_py.
; Corrupts: everything
ellipse_point:
                ld      a, (ell_step)
                add     a, ELLIPSE_STEPS / 4    ; across uses a quarter turn on
                call    sine_at
                ld      c, a
                ld      a, (ell_rx)
                ld      b, a
                call    sine_scaled
                ld      hl, ell_cx
                add     a, (hl)
                ld      (ell_px), a
                ld      a, (ell_step)
                call    sine_at
                ld      c, a
                ld      a, (ell_ry)
                ld      b, a
                call    sine_scaled
                ld      hl, ell_cy
                add     a, (hl)
                ld      (ell_py), a
                ret

; The sine for step A.
; Corrupts: DE, HL
sine_at:
                and     ELLIPSE_STEPS - 1
                ld      e, a
                ld      d, 0
                ld      hl, sine_table
                add     hl, de
                ld      a, (hl)
                ret

ell_cx:         db      0
ell_cy:         db      0
ell_rx:         db      0
ell_ry:         db      0
ell_px:         db      0
ell_py:         db      0
ell_first_x:    db      0
ell_first_y:    db      0
ell_step:       db      0

; round(128 * sin(2 * pi * step / 64)), held to 127 so it fits a byte with a
; sign.  The reference holds exactly these numbers.
sine_table:
                db      0, 13, 25, 37, 49, 60, 71, 81
                db      91, 99, 106, 113, 118, 122, 126, 127
                db      127, 127, 126, 122, 118, 113, 106, 99
                db      91, 81, 71, 60, 49, 37, 25, 13
                db      0, -13, -25, -37, -49, -60, -71, -81
                db      -91, -99, -106, -113, -118, -122, -126, -127
                db      -127, -127, -126, -122, -118, -113, -106, -99
                db      -91, -81, -71, -60, -49, -37, -25, -13
