; MIT License, Copyright (c) 2025 Cronomantic
;
; Rectangles and ellipses, built on the straight line.
;
; The ellipse follows the original exactly, table and all, so that the pictures
; come out as they were drawn.  The reference renderer does the same sum and
; the two are compared pixel for pixel.
;
; Everything here works in sixteen bit coordinates, because the original does:
; a curve that leaves the picture has to stay outside rather than come round in
; a byte.  Bringing a point back to the edge is the line's job.
;
; This is shared by the machines that count in whole pixels, which is every one
; of them but the Amstrad: its firmware works in halves of a pixel, so an
; ellipse of its own comes out a pixel wider on one side, and it keeps its own
; copy of this file.

ELLIPSE_STEPS   equ 8                   ; steps to a quarter turn

; The outline of a rectangle, as four straight lines.
; Corrupts: everything
draw_rect:
                ld      hl, (lin_x0)
                ld      (rect_x0), hl
                ld      hl, (lin_y0)
                ld      (rect_y0), hl
                ld      hl, (lin_x1)
                ld      (rect_x1), hl
                ld      hl, (lin_y1)
                ld      (rect_y1), hl
                call    .whole_box              ; the top
                ld      hl, (rect_y0)
                ld      (lin_y1), hl
                call    draw_line
                call    .whole_box              ; the bottom
                ld      hl, (rect_y1)
                ld      (lin_y0), hl
                call    draw_line
                call    .whole_box              ; the left side
                ld      hl, (rect_x0)
                ld      (lin_x1), hl
                call    draw_line
                call    .whole_box              ; and the right
                ld      hl, (rect_x1)
                ld      (lin_x0), hl
                jp      draw_line
.whole_box:
                ld      hl, (rect_x0)
                ld      (lin_x0), hl
                ld      hl, (rect_y0)
                ld      (lin_y0), hl
                ld      hl, (rect_x1)
                ld      (lin_x1), hl
                ld      hl, (rect_y1)
                ld      (lin_y1), hl
                ret

rect_x0:        dw      0
rect_y0:        dw      0
rect_x1:        dw      0
rect_y1:        dw      0

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

; How big the sixteen bit number in HL is, without its sign, in A.  A radius
; never reaches 256, so a byte holds it.
; Corrupts: AF, DE, HL
magnitude:
                bit     7, h
                jr      z, .positive
                ex      de, hl
                ld      hl, 0
                or      a
                sbc     hl, de
.positive:
                ld      a, l
                ret

; The centre, plus or minus the distance in A, as a sixteen bit point in HL.
; Which way round is in ell_sx or ell_sy, which hold one or minus one.
; Corrupts: AF, C, DE, HL
offset_x:
                ld      hl, ell_sx
                ld      c, (hl)
                ld      hl, (ell_cx)
                jr      offset
offset_y:
                ld      hl, ell_sy
                ld      c, (hl)
                ld      hl, (ell_cy)
offset:
                ld      e, a
                ld      d, 0
                bit     7, c
                jr      nz, .away
                add     hl, de
                ret
.away:
                or      a
                sbc     hl, de
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
                ld      hl, (lin_x0)
                ld      (ell_cx), hl
                ld      hl, (lin_y0)
                ld      (ell_cy), hl
                ld      hl, (lin_x1)
                ld      de, (ell_cx)
                or      a
                sbc     hl, de
                call    magnitude
                ld      (ell_rx), a
                ld      hl, (lin_y1)
                ld      de, (ell_cy)
                or      a
                sbc     hl, de
                call    magnitude
                ld      (ell_ry), a
                ld      hl, ell_ry
                ld      a, (ell_rx)
                or      (hl)
                jr      nz, .quarters
                ld      hl, (ell_cx)            ; no room in it: a point
                call    clamp_x
                ld      d, l
                ld      hl, (ell_cy)
                call    clamp_row
                ld      e, l
                jp      plot_point
.quarters:
                xor     a
                ld      (ell_quarter), a
.each_quarter:
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
                ; start at the point on the side
                ld      a, (ell_rx)
                call    offset_x
                ld      (ell_px), hl
                ld      hl, (ell_cy)
                ld      (ell_py), hl
                xor     a
                ld      (ell_step), a
.each_step:
                ld      hl, (ell_px)
                ld      (lin_x0), hl
                ld      hl, (ell_py)
                ld      (lin_y0), hl
                call    ellipse_point
                ld      hl, (ell_px)
                ld      (lin_x1), hl
                ld      hl, (ell_py)
                ld      (lin_y1), hl
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
                call    multiply
                ld      a, h                    ; the top eight bits, the divide
                call    offset_x
                ld      (ell_px), hl
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
                call    offset_y
                ld      (ell_py), hl
                ret

; A straight line, or a single point when both ends are the same place.
; Corrupts: everything
draw_segment:
                ld      hl, (lin_x0)
                ld      de, (lin_x1)
                or      a
                sbc     hl, de
                jp      nz, draw_line
                ld      hl, (lin_y0)
                ld      de, (lin_y1)
                or      a
                sbc     hl, de
                jp      nz, draw_line
                ld      hl, (lin_x0)
                call    clamp_x
                ld      d, l
                ld      hl, (lin_y0)
                call    clamp_row
                ld      e, l
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

ell_cx:         dw      0
ell_cy:         dw      0
ell_px:         dw      0
ell_py:         dw      0
ell_rx:         db      0
ell_ry:         db      0
ell_sx:         db      0
ell_sy:         db      0
ell_step:       db      0
ell_quarter:    db      0
