; MIT License, Copyright (c) 2025 Cronomantic
;
; Drawing on the Spectrum: the primitives the picture interpreter asks for.
;
; Coordinates arrive as the adventure wrote them, x across and y up from the
; bottom of the screen, and are turned into screen rows here.  Colour is held
; per cell of eight by eight, which is the machine's own limitation and none
; of the picture interpreter's business.

PICTURE_ROWS    equ 128                 ; the top sixteen character rows
GAC_TOP         equ 175                 ; y=175 is the first row of the screen
ATTRIBUTES      equ $5800

; Turn the adventure's y into a screen row.  In A, out A.
to_row:
                neg
                add     a, GAC_TOP
                ret

; The colours a picture starts in: black on white, as the screen starts.
; Corrupts: AF
gfx_start_colours:
                xor     a
                ld      (gfx_ink), a
                ld      (gfx_bright), a
                ld      (gfx_flash), a
                ld      a, 7
                ld      (gfx_paper), a
                ret

; The border, which on a Spectrum is three bits of a port.
; Corrupts: AF
gfx_border:
                and     7
                out     ($FE), a
                ret

; Turn a command's y into a screen row, keeping sixteen bits with their sign.
; A picture may name a y above the top or below the bottom of the picture, and
; those have to stay outside rather than come round in a byte.  In A, out HL.
; Corrupts: AF, C
row_of:
                ld      c, a
                ld      a, GAC_TOP
                sub     c
                ld      l, a
                sbc     a, a                    ; all ones when it went below
                ld      h, a
                ret

; Bring an x that left the picture to its edge: below nought comes to nought
; and past the last column comes to the last column.  In HL, out L.
; Corrupts: AF
clamp_x:
                ld      a, h
                or      a
                ret     z                       ; nought to 255 already
                ld      l, 0
                bit     7, h
                ret     nz
                ld      l, 255
                ret

; The same for a row: above the top comes to the top and below the bottom to
; the last row.  In HL, out L.
; Corrupts: AF
clamp_row:
                ld      a, h
                or      a
                jr      nz, .outside
                ld      a, l
                cp      PICTURE_ROWS
                ret     c
                ld      l, PICTURE_ROWS - 1
                ret
.outside:
                ld      l, 0
                bit     7, h
                ret     nz
                ld      l, PICTURE_ROWS - 1
                ret

; The byte holding pixel (D across, E down) in HL, its bit as a mask in B.
; Corrupts: AF
pixel_address:
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
                ld      a, d
                rrca
                rrca
                rrca
                and     %00011111       ; which byte across
                or      l
                ld      l, a
                ; the bit within the byte, looked up rather than shifted for
                ; each pixel: this routine is called for every one of them
                ld      a, d
                and     7
                push    hl
                ld      hl, bit_masks
                add     a, l
                ld      l, a
                jr      nc, .no_carry
                inc     h
.no_carry:
                ld      b, (hl)
                pop     hl
                ret

bit_masks:      db      %10000000, %01000000, %00100000, %00010000
                db      %00001000, %00000100, %00000010, %00000001

; The attribute of the cell holding pixel (D, E), in HL.
; Corrupts: AF, BC
attribute_address:
                ld      a, e
                rrca
                rrca
                rrca
                and     %00011111
                ld      l, a
                ld      h, 0
                add     hl, hl
                add     hl, hl
                add     hl, hl
                add     hl, hl
                add     hl, hl          ; thirty two bytes a row
                ld      a, d
                rrca
                rrca
                rrca
                and     %00011111
                add     a, l
                ld      l, a
                jr      nc, .no_carry
                inc     h
.no_carry:
                ld      bc, ATTRIBUTES
                add     hl, bc
                ret

; The attribute byte the colours in force come to, when it does not depend on
; what is already in the cell.  Carry clear and the byte in A when they do not;
; carry set when one of them is an eight, meaning leave what is there, or the
; ink is nine, meaning choose against the paper.  A fill that colours a long
; run wants this once instead of working it out for every cell.
; Corrupts: AF, B
attr_const:
                ld      a, (gfx_ink)
                cp      8
                jr      nc, .varies
                ld      b, a
                ld      a, (gfx_paper)
                cp      8
                jr      nc, .varies
                rlca
                rlca
                rlca
                or      b
                ld      b, a
                ld      a, (gfx_bright)
                cp      8
                jr      nc, .varies
                and     1
                rrca
                rrca                            ; into bit six
                or      b
                ld      b, a
                ld      a, (gfx_flash)
                cp      8
                jr      nc, .varies
                and     1
                rrca                            ; into bit seven
                or      b
                ret                             ; carry is clear after OR
.varies:
                scf
                ret

; Give the cell holding pixel (D, E) the colours in force.  A colour of eight
; means leave what is there, and an ink of nine means pick black or white,
; whichever will be read against the paper.
; Corrupts: everything but DE
colour_cell:
                push    de
                call    attribute_address
                ld      c, (hl)                 ; what is there now
                ld      a, (gfx_paper)
                cp      8
                jr      c, .have_paper
                ld      a, c
                rrca
                rrca
                rrca
.have_paper:
                and     7
                ld      d, a                    ; the paper
                ld      a, (gfx_ink)
                cp      8
                jr      c, .have_ink
                cp      9
                jr      z, .contrast
                ld      a, c                    ; leave the ink alone
                jr      .have_ink
.contrast:
                ld      a, 7                    ; white on a dark paper
                ld      b, a
                ld      a, d
                cp      4
                ld      a, b
                jr      c, .have_ink
                xor     a                       ; black on a light one
.have_ink:
                and     7
                ld      e, a                    ; the ink
                ld      a, d
                rlca
                rlca
                rlca
                or      e
                ld      e, a                    ; ink and paper together
                ld      a, (gfx_bright)
                cp      8
                jr      c, .have_bright
                ld      a, c
                rrca
                rrca
                rrca
                rrca
                rrca
                rrca
.have_bright:
                and     1
                rrca
                rrca                            ; into bit six
                or      e
                ld      e, a
                ld      a, (gfx_flash)
                cp      8
                jr      c, .have_flash
                ld      a, c
                rlca
.have_flash:
                and     1
                rrca                            ; into bit seven
                or      e
                ld      (hl), a
                pop     de
                ret

; Put down a pixel of the outline at (D, E), which also stops fills.
; Corrupts: everything but DE
plot_point:
                ld      a, e
                cp      PICTURE_ROWS
                ret     nc                      ; off the picture, leave it
                push    de
                call    pixel_address
                ld      a, (hl)
                or      b
                ld      (hl), a
                pop     de
                jp      colour_cell

; Whether a fill has to stop at (D, E).  Zero flag clear if it does.
; Off the picture always stops it.
; Corrupts: AF, BC, HL
is_boundary:
                ld      a, e
                cp      PICTURE_ROWS
                jr      nc, .stops              ; off the top or bottom
                call    pixel_address
                ld      a, (hl)
                and     b
                ret
.stops:
                ld      a, 1
                ret

; Paint a pixel a fill has reached, in the way fill_mode says.
; Corrupts: everything but DE
; A straight line between the two points in lin_x0 and lin_x1, which are
; sixteen bit and may lie outside the picture.
;
; Each end is brought to the edge before anything else, which is what GAC does
; at $643C, and only then are the two deltas worked out in a byte.  Without
; that a curve which leaves the top of the picture comes back as a line down
; the whole screen, because in a byte a row of minus one is a row of 255.
; Corrupts: everything
draw_line:
                ld      hl, (lin_x0)
                call    clamp_x
                ld      a, l
                ld      (gfx_x0), a
                ld      hl, (lin_y0)
                call    clamp_row
                ld      a, l
                ld      (gfx_y0), a
                ld      hl, (lin_x1)
                call    clamp_x
                ld      a, l
                ld      (gfx_x1), a
                ld      hl, (lin_y1)
                call    clamp_row
                ld      a, l
                ld      (gfx_y1), a
                ; fall through

; The line between two points that are known to be inside, in screen rows.
; Drawn the way the Spectrum ROM draws a line, because that is what GAC
; called: it does PLOT at $22E5 and DRAW at $24BA and never wrote its own.
; The error starts at half the longer side, counts up by the shorter one, and
; when it reaches the longer side it comes off again and that step goes
; diagonal.  Counting the other way round is just as valid a Bresenham but
; puts the diagonal steps one place along, which shows on short slanted lines.
; Corrupts: everything
line_between:
                ld      a, (gfx_x0)
                ld      d, a
                ld      a, (gfx_y0)
                ld      e, a
                ; how far, and which way, across
                ld      a, (gfx_x1)
                sub     d
                ld      b, 1                    ; rightwards
                jr      nc, .have_dx
                neg
                ld      b, -1
.have_dx:
                ld      (line_dx), a
                ld      a, b
                ld      (line_sx), a
                ; and down
                ld      a, (gfx_y1)
                sub     e
                ld      b, 1
                jr      nc, .have_dy
                neg
                ld      b, -1
.have_dy:
                ld      (line_dy), a
                ld      a, b
                ld      (line_sy), a
                ; which side is longer?
                ld      a, (line_dx)
                ld      c, a
                ld      a, (line_dy)
                cp      c
                jr      z, .across
                jr      c, .across
                jp      .down

.across:
                ; the starting point, then a step across every time and a step
                ; down when the error comes round
                push    de
                call    plot_point
                pop     de
                ld      a, (line_dx)
                srl     a
                ld      (line_err), a
                ld      a, (line_dx)
                or      a
                ret     z                       ; both ends the same place
                ld      b, a
.across_step:
                push    bc
                ld      a, (line_err)
                ld      hl, line_dy
                add     a, (hl)
                ld      hl, line_dx
                cp      (hl)
                jr      c, .across_straight
                sub     (hl)
                ld      c, a
                ld      hl, line_sy
                ld      a, e
                add     a, (hl)
                ld      e, a                    ; the step goes diagonal
                ld      a, c
.across_straight:
                ld      (line_err), a
                ld      hl, line_sx
                ld      a, d
                add     a, (hl)
                ld      d, a
                push    de
                call    plot_point
                pop     de
                pop     bc
                djnz    .across_step
                ret

.down:
                push    de
                call    plot_point
                pop     de
                ld      a, (line_dy)
                srl     a
                ld      (line_err), a
                ld      a, (line_dy)
                or      a
                ret     z
                ld      b, a
.down_step:
                push    bc
                ld      a, (line_err)
                ld      hl, line_dx
                add     a, (hl)
                ld      hl, line_dy
                cp      (hl)
                jr      c, .down_straight
                sub     (hl)
                ld      c, a
                ld      hl, line_sx
                ld      a, d
                add     a, (hl)
                ld      d, a
                ld      a, c
.down_straight:
                ld      (line_err), a
                ld      hl, line_sy
                ld      a, e
                add     a, (hl)
                ld      e, a
                push    de
                call    plot_point
                pop     de
                pop     bc
                djnz    .down_step
                ret

lin_x0:         dw      0                       ; a line's two ends, before
lin_y0:         dw      0                       ; they are brought inside
lin_x1:         dw      0
lin_y1:         dw      0

line_dx:        db      0
line_dy:        db      0
line_sx:        db      0
line_sy:        db      0
line_err:       db      0

