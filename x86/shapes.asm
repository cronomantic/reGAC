; MIT License, Copyright (c) 2025 Cronomantic
;
; Rectangles and ellipses, built on the straight line: z80/common/shapes.asm,
; step for step, because the ellipse follows the original exactly, table and
; all, and the reference renderer does the same sum.  A build off an Amstrad,
; assembled with AMSTRAD_PICTURES, is z80/cpc/shapes.asm instead, which is the
; same ellipse come down to a pixel from halves of one: see round_out.
;
; Everything here works in sixteen bit coordinates, as the original does: a
; curve that leaves the picture has to stay outside rather than come round.
; Bringing a point back to the edge is the line's job.

ELLIPSE_STEPS   equ 8                   ; steps to a quarter turn

; The outline of a rectangle, as four straight lines.
; Corrupts: everything but DS
draw_rect:
                mov     ax, [lin_x0]
                mov     [rect_x0], ax
                mov     ax, [lin_y0]
                mov     [rect_y0], ax
                mov     ax, [lin_x1]
                mov     [rect_x1], ax
                mov     ax, [lin_y1]
                mov     [rect_y1], ax
                call    .whole_box              ; the top
                mov     ax, [rect_y0]
                mov     [lin_y1], ax
                call    draw_line
                call    .whole_box              ; the bottom
                mov     ax, [rect_y1]
                mov     [lin_y0], ax
                call    draw_line
                call    .whole_box              ; the left side
                mov     ax, [rect_x0]
                mov     [lin_x1], ax
                call    draw_line
                call    .whole_box              ; and the right
                mov     ax, [rect_x1]
                mov     [lin_x0], ax
                jmp     draw_line
.whole_box:
                mov     ax, [rect_x0]
                mov     [lin_x0], ax
                mov     ax, [rect_y0]
                mov     [lin_y0], ax
                mov     ax, [rect_x1]
                mov     [lin_x1], ax
                mov     ax, [rect_y1]
                mov     [lin_y1], ax
                ret

section .data
rect_x0:        dw      0
rect_y0:        dw      0
rect_x1:        dw      0
rect_y1:        dw      0
section .text

; How big the sixteen bit number in AX is, without its sign, in AL.  A radius
; never reaches 256, so a byte holds it.
; Corrupts: AX
magnitude:
                test    ah, 80h
                jz      .positive
                neg     ax
.positive:
                ret

; The centre, plus or minus the distance in AL, as a sixteen bit point in AX.
; Which way round is in ell_sx or ell_sy, which hold one or minus one.
; Corrupts: AX, BX
offset_x:
                mov     bl, [ell_sx]
                mov     bh, al
                mov     ax, [ell_cx]
                jmp     offset
offset_y:
                mov     bl, [ell_sy]
                mov     bh, al
                mov     ax, [ell_cy]
offset:
                push    cx
                mov     cl, bh
                xor     ch, ch
                test    bl, 80h
                jnz     .away
                add     ax, cx
                pop     cx
                ret
.away:
                sub     ax, cx
                pop     cx
                ret

; An ellipse, the way GAC drew one.
;
; The two pairs in the command are not a box round it: the first is the centre
; and the second gives the radii, as the distance from one to the other.  Read
; out of the original at $88FE.  It is walked in eight steps a quarter off the
; table below, each quarter drawn on its own from the point at the side, which
; is why the curve comes out as thirty two straight pieces.
; Corrupts: everything but DS
draw_ellipse:
                mov     ax, [lin_x0]
                mov     [ell_cx], ax
                mov     ax, [lin_y0]
                mov     [ell_cy], ax
                mov     ax, [lin_x1]
                sub     ax, [ell_cx]
                call    magnitude
                mov     [ell_rx], al
                mov     ax, [lin_y1]
                sub     ax, [ell_cy]
                call    magnitude
                mov     [ell_ry], al
                or      al, [ell_rx]
                jnz     .quarters
                mov     ax, [ell_cx]            ; no room in it: a point
                call    clamp_x
                mov     dl, al
                mov     ax, [ell_cy]
                call    clamp_row
                mov     dh, al
                jmp     plot_point
.quarters:
                mov     byte [ell_quarter], 0
.each_quarter:
                mov     bl, [ell_quarter]
                xor     bh, bh
                shl     bx, 1
                mov     al, [quarter_signs + bx]
                mov     [ell_sx], al
                mov     al, [quarter_signs + bx + 1]
                mov     [ell_sy], al
                ; start at the point on the side
                mov     al, [ell_rx]
                call    offset_x
                mov     [ell_px], ax
                mov     ax, [ell_cy]
                mov     [ell_py], ax
                mov     byte [ell_step], 0
.each_step:
                mov     ax, [ell_px]
                mov     [lin_x0], ax
                mov     ax, [ell_py]
                mov     [lin_y0], ax
                call    ellipse_point
                mov     ax, [ell_px]
                mov     [lin_x1], ax
                mov     ax, [ell_py]
                mov     [lin_y1], ax
                call    draw_segment
                inc     byte [ell_step]
                cmp     byte [ell_step], ELLIPSE_STEPS
                jne     .each_step
                inc     byte [ell_quarter]
                cmp     byte [ell_quarter], 4
                jne     .each_quarter
                ret

; Where the current step of the current quarter falls, into ell_px and ell_py:
; the radius times the table's entry, and the top eight bits of that.
; Corrupts: AX, BX
ellipse_point:
                mov     bl, [ell_step]
                xor     bh, bh
                mov     al, [ellipse_table + bx]        ; the cosine
                mul     byte [ell_rx]
%ifdef AMSTRAD_PICTURES
                ; across, where the far side is the one the step comes off
                test    byte [ell_sx], 80h
                jz      .plain_x
                call    round_out
.plain_x:
%endif
                mov     al, ah
                call    offset_x
                mov     [ell_px], ax
                mov     bl, [ell_step]
                xor     bh, bh
                mov     al, [ellipse_table + ELLIPSE_STEPS + bx]    ; the sine
                mul     byte [ell_ry]
%ifdef AMSTRAD_PICTURES
                ; and down the screen, which is up the commands, so the side
                ; the step comes off is the other one
                test    byte [ell_sy], 80h
                jnz     .plain_y
                call    round_out
.plain_y:
%endif
                mov     al, ah
                call    offset_y
                mov     [ell_py], ax
                ret

%ifdef AMSTRAD_PICTURES
; On the side a step is taken from, the half that the divide throws away
; counts: the Amstrad keeps its coordinates in halves of a pixel, and the
; position the step lands on rounds down, which there is one further out.
; See z80/cpc/shapes.asm, where it was measured.  AX is the radius times the
; table's entry; AH comes back one more if a half is left over in AL.
round_out:
                test    al, 80h
                jz      .none
                inc     ah
.none:
                ret
%endif

; A straight line, or a single point when both ends are the same place.
; Corrupts: everything but DS
draw_segment:
                mov     ax, [lin_x0]
                cmp     ax, [lin_x1]
                jne     draw_line
                mov     ax, [lin_y0]
                cmp     ax, [lin_y1]
                jne     draw_line
                mov     ax, [lin_x0]
                call    clamp_x
                mov     dl, al
                mov     ax, [lin_y0]
                call    clamp_row
                mov     dh, al
                jmp     plot_point

; -- what the picture interpreter calls -------------------------------------

; The y in the commands counts up from the bottom; the screen counts rows down
; from the top.  Everything that draws an outline works in sixteen bit rows,
; so that a point above the top stays above it; the fill keeps working in the
; commands' own coordinates, because that is where its pattern and its limits
; are reckoned.
; Corrupts: AX
gfx_to_words:
                mov     al, [gfx_x0]
                xor     ah, ah
                mov     [lin_x0], ax
                mov     al, [gfx_y0]
                call    row_of
                mov     [lin_y0], ax
                mov     al, [gfx_x1]
                xor     ah, ah
                mov     [lin_x1], ax
                mov     al, [gfx_y1]
                call    row_of
                mov     [lin_y1], ax
                ret

gfx_line:
                call    gfx_to_words
                jmp     draw_line

gfx_rect:
                call    gfx_to_words
                jmp     draw_rect

gfx_ellipse:
                call    gfx_to_words
                jmp     draw_ellipse

gfx_plot:
                call    gfx_to_words
                mov     ax, [lin_x0]
                call    clamp_x
                mov     dl, al
                mov     ax, [lin_y0]
                call    clamp_row
                mov     dh, al
                jmp     plot_point

gfx_fill:
                mov     dl, [gfx_x0]
                mov     dh, [gfx_y0]
                jmp     flood_fill

section .data
quarter_signs:  db      1, 1
                db      1, -1
                db      -1, 1
                db      -1, -1

; The table GAC carries at $A1ED inside the adventure: eight cosines then
; eight sines, a quarter turn divided in eight, scaled by 256 and held to 255.
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
section .text
