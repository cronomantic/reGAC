; MIT License, Copyright (c) 2025 Cronomantic
;
; Rectangles and ellipses on the Amstrad, built on the straight line.
;
; The ellipse is the same shape as the Spectrum's, off the same table, but it
; is not worked out the same way.  This machine keeps its coordinates in
; halves of a pixel, because the firmware's screen is 640 by 400 whatever the
; mode is, so a step comes out in halves and only then comes down to a pixel.
; What comes down is a position rather than a distance, so it always goes
; down: away from the centre on the side the step is taken from, towards it on
; the other.  That one pixel is the whole difference, and it was measured on a
; real machine by bending its own table of sines.

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

; How big the sixteen bit number in HL is, without its sign, in A.
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

; How far one step of the ellipse falls from the centre, in A.
;
; The radius is in B and the table value in C, and ell_away says whether this
; is the side the step is taken from: there the half that the divide throws
; away counts, because the position it lands on rounds down and that is one
; further out.
; Corrupts: everything
scaled_step:
                call    multiply                ; HL = radius times the sine
                ld      a, (ell_away)
                or      a
                ld      a, h
                ret     z                       ; the plain half of it
                bit     7, l
                ret     z
                inc     a                       ; a half is left over
                ret

; The centre in HL plus or minus the distance in A, as a sixteen bit point.
; The sign is in C: bit seven set means take it away.
; Corrupts: AF, DE, HL
offset_from:
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

; An ellipse, the way GAC drew one: the first pair is the centre and the
; second gives the radii, walked in eight steps a quarter off the table.
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
                jp      plot_row
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
                ; the point at the side, which is the radius exactly
                ld      a, (ell_sx)
                ld      c, a
                ld      hl, (ell_cx)
                ld      a, (ell_rx)
                call    offset_from
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
                ; across, where the far side is the one the step comes off
                ld      a, (ell_step)
                ld      e, a
                ld      d, 0
                ld      hl, ellipse_table
                add     hl, de
                ld      c, (hl)
                ld      a, (ell_rx)
                ld      b, a
                ld      a, (ell_sx)
                and     $80
                ld      (ell_away), a           ; taking it away rounds out
                call    scaled_step
                ld      b, a                    ; how far it falls
                ld      a, (ell_sx)
                ld      c, a
                ld      hl, (ell_cx)
                ld      a, b
                call    offset_from
                ld      (ell_px), hl
                ; and down the screen, which is up the commands, so the side
                ; the step comes off is the other one
                ld      a, (ell_step)
                add     a, ELLIPSE_STEPS
                ld      e, a
                ld      d, 0
                ld      hl, ellipse_table
                add     hl, de
                ld      c, (hl)
                ld      a, (ell_ry)
                ld      b, a
                ld      a, (ell_sy)
                and     $80
                xor     $80
                ld      (ell_away), a
                call    scaled_step
                ld      b, a
                ld      a, (ell_sy)
                ld      c, a
                ld      hl, (ell_cy)
                ld      a, b
                call    offset_from
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
                jp      plot_row

quarter_signs:  db      1, 1
                db      1, -1
                db      -1, 1
                db      -1, -1

; The table GAC carries inside the adventure: eight cosines then eight sines,
; a quarter turn divided in eight, scaled by 256 and held to 255.
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
ell_away:       db      0
