; MIT License, Copyright (c) 2025 Cronomantic
;
; Rectangles and ellipses, built on the straight line.
;
; The ellipse follows the original exactly, table and all, so that the pictures
; come out as they were drawn.  The reference renderer does the same sum and
; the two are compared pixel for pixel.

ELLIPSE_STEPS   equ 8                   ; steps to a quarter turn

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

; An ellipse, the way GAC drew one.
;
; The two pairs in the command are not a box round it: the first is the centre
; and the second gives the radii, as the distance from one to the other.  Read
; out of the original at $88FE.
;
; It is walked in eight steps a quarter off the table below, and each quarter
; is drawn on its own starting from the point at the side, which is why the
; curve comes out as thirty two straight pieces.
; Corrupts: everything
draw_ellipse:
                ld      a, (gfx_x0)
                ld      (ell_cx), a
                ld      a, (gfx_y0)
                ld      (ell_cy), a
                ld      hl, gfx_x0
                ld      a, (gfx_x1)
                sub     (hl)
                jr      nc, .have_rx
                neg
.have_rx:
                ld      (ell_rx), a
                ld      hl, gfx_y0
                ld      a, (gfx_y1)
                sub     (hl)
                jr      nc, .have_ry
                neg
.have_ry:
                ld      (ell_ry), a
                ld      hl, ell_ry
                ld      a, (ell_rx)
                or      (hl)
                jr      nz, .quarters
                ld      a, (ell_cx)             ; no room in it: a point
                ld      d, a
                ld      a, (ell_cy)
                ld      e, a
                jp      plot_point
.quarters:
                xor     a
                ld      (ell_quarter), a
.each_quarter:
                ; start at the point on the side
                ld      a, (ell_quarter)
                add     a, a
                ld      e, a
                ld      d, 0
                ld      hl, quarter_signs
                add     hl, de
                ld      a, (hl)
                ld      (ell_sx), a
                inc     hl
                ld      a, (hl)
                ld      (ell_sy), a
                ld      a, (ell_rx)
                call    give_sign_x
                ld      hl, ell_cx
                add     a, (hl)
                ld      (ell_px), a
                ld      a, (ell_cy)
                ld      (ell_py), a
                xor     a
                ld      (ell_step), a
.each_step:
                ld      a, (ell_px)
                ld      (gfx_x0), a
                ld      a, (ell_py)
                ld      (gfx_y0), a
                call    ellipse_point
                ld      a, (ell_px)
                ld      (gfx_x1), a
                ld      a, (ell_py)
                ld      (gfx_y1), a
                call    draw_segment
                ld      hl, ell_step
                inc     (hl)
                ld      a, (hl)
                cp      ELLIPSE_STEPS
                jr      nz, .each_step
                ld      hl, ell_quarter
                inc     (hl)
                ld      a, (hl)
                cp      4
                jr      nz, .each_quarter
                ret

; Where the current step of the current quarter falls, into ell_px and ell_py.
; Corrupts: everything
ellipse_point:
                ld      a, (ell_step)
                ld      e, a
                ld      d, 0
                ld      hl, ellipse_table
                add     hl, de
                ld      c, (hl)                 ; the cosine
                ld      a, (ell_rx)
                ld      b, a
                push    de
                call    multiply
                pop     de
                ld      a, h                    ; the top eight bits, the divide
                call    give_sign_x
                ld      hl, ell_cx
                add     a, (hl)
                ld      (ell_px), a
                ld      a, (ell_step)
                add     a, ELLIPSE_STEPS
                ld      e, a
                ld      d, 0
                ld      hl, ellipse_table
                add     hl, de
                ld      c, (hl)                 ; the sine
                ld      a, (ell_ry)
                ld      b, a
                call    multiply
                ld      a, h
                call    give_sign_y
                ld      hl, ell_cy
                add     a, (hl)
                ld      (ell_py), a
                ret

; Turn A about if this quarter goes the other way.
give_sign_x:
                ld      hl, ell_sx
                bit     7, (hl)
                ret     z
                neg
                ret
give_sign_y:
                ld      hl, ell_sy
                bit     7, (hl)
                ret     z
                neg
                ret

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

quarter_signs:  db      1, 1
                db      1, -1
                db      -1, 1
                db      -1, -1

; The table GAC carries at $A1ED inside the adventure: eight cosines then
; eight sines, a quarter turn divided in eight, scaled by 256 and held to 255
; so that each fits a byte.
ellipse_table:  db      251, 237, 213, 181, 142, 98, 50, 0
                db      50, 98, 142, 181, 213, 237, 251, 255

ell_cx:         db      0
ell_cy:         db      0
ell_rx:         db      0
ell_ry:         db      0
ell_px:         db      0
ell_py:         db      0
ell_sx:         db      0
ell_sy:         db      0
ell_step:       db      0
ell_quarter:    db      0
