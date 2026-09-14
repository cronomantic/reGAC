; MIT License, Copyright (c) 2025 Cronomantic
;
; Drawing on the Amstrad PCW: the primitives the picture interpreter asks for.
;
; This machine has one bit a pixel and no colour whatever, so two things are
; different from every other target.
;
; The first is what a colour becomes.  An area is laid down as a dither chosen
; by how light the colour was, which keeps a dark wall darker than a bright
; sky; an outline is not dithered at all, because half a line is not a line,
; so it comes out solid, white or black by that same lightness.  The bright
; bit does nothing here: lightness is measured against white, and one level of
; light has nowhere to put a second.
;
; The second follows from the first.  A lit pixel can no longer be what stops
; a fill, because a black outline on this screen is an unlit pixel, so there
; is a separate one bit mask of four kilobytes which holds exactly what a
; Spectrum's bitmap would hold.  It has to: the pictures were drawn against
; the Spectrum's own rule, where the lit half of a half tone stops the next
; fill and the unlit half does not.
;
; The mask is the picture as it was written, 256 across; the screen is twice
; that, because a pixel of this one is about half as wide as it is tall.  The
; doubling is done here, at the point, and never by drawing anything twice.

MASK_AT         equ $C000               ; four kilobytes, thirty two to a row
GAC_TOP         equ 175                 ; y=175 is the first row of the screen
POINT_MASK      equ (8 / PICTURE_SCALE) - 1      ; which points share a byte

; Turn the adventure's y into a screen row.  In A, out A.
to_row:
                neg
                add     a, GAC_TOP
                ret

; The colours a picture starts in: black on white, as the screen starts.
; Corrupts: AF, BC
gfx_start_colours:
                push    hl                      ; the caller is holding the
                xor     a                       ; picture it is about to draw
                ld      (gfx_ink), a
                ld      (gfx_bright), a
                ld      (gfx_flash), a
                ld      (pcw_ink), a
                ld      a, 7
                ld      (gfx_paper), a
                ld      (pcw_paper), a
                call    settle_colours
                pop     hl
                ret

; There is no border on this machine, so the command has nowhere to go.  It is
; still a macro and not a routine, because the picture interpreter runs it
; inside its command loop: one picture of Los pájaros de Bangkok sets the
; border forty three thousand times, and even a call and a return cost that
; picture half a second on a Spectrum.
                MACRO   GFX_BORDER
                ENDM

; Settle what the colours in force come to on a screen with none: how light
; the ink and the paper are, nought to four, and whether an outline is drawn
; white or black.  Once per shape, not once per pixel.
;
; The ink and the paper are kept here as they came rather than as they came
; out, because an ink of eight means leave the colour alone and an ink of nine
; means pick whichever reads against the paper, and that second one has to be
; worked out again every time the paper changes.
; Corrupts: AF, BC, HL
settle_colours:
                ld      a, (gfx_paper)
                cp      8
                jr      nc, .paper_stands
                ld      (pcw_paper), a
.paper_stands:
                ld      a, (gfx_ink)
                cp      8
                jr      z, .ink_stands
                ld      (pcw_ink), a
.ink_stands:
                ld      a, (pcw_paper)
                call    level_of
                ld      (paper_level), a
                ld      a, (pcw_ink)
                cp      9
                jr      nz, .have_ink
                ld      a, (pcw_paper)          ; whichever reads against it
                cp      4
                ld      a, 0                    ; black on a light paper
                jr      nc, .have_ink
                ld      a, 7                    ; white on a dark one
.have_ink:
                call    level_of
                ld      (ink_level), a
                ; a line is solid: white if the ink is more than half light
                ld      b, 0
                cp      9 * 4
                jr      c, .dark
                ld      b, $FF
.dark:
                ld      a, b
                ld      (line_lit), a
                ret

; How light colour A is, as four times the level, which is how the dithers
; below are indexed.  Nought is black and sixteen is white; the bright bit is
; not looked at.
; Corrupts: AF, HL
level_of:
                and     7
                ld      hl, levels
                add     a, l
                ld      l, a
                ld      a, 0
                adc     a, h
                ld      h, a
                ld      a, (hl)
                ret

; Four times the level of each of the eight colours: black, blue, red,
; magenta, green, cyan, yellow, white, weighed the way the eye weighs them.
; Seventeen levels and not five, because with five the dark blue of a window
; came out the same black as the outline drawn around it.
levels:         db      0, 8, 20, 28, 40, 44, 56, 64

; What a level lays down along a row, eight points of the picture to the byte.
; Four entries to a level, one for each row of a four by four dither, and four
; points across is as wide as that dither can be and still cost nothing: eight
; points are two turns of it, so a whole run is still one byte written along.
dither_bytes:   db      $00, $00, $00, $00      ; nothing lit
                db      $88, $00, $00, $00
                db      $88, $00, $22, $00
                db      $AA, $00, $22, $00
                db      $AA, $00, $AA, $00      ; a quarter
                db      $AA, $44, $AA, $00
                db      $AA, $44, $AA, $11
                db      $AA, $55, $AA, $11
                db      $AA, $55, $AA, $55      ; half, the chequer
                db      $EE, $55, $AA, $55
                db      $EE, $55, $BB, $55
                db      $FF, $55, $BB, $55
                db      $FF, $55, $FF, $55      ; three quarters
                db      $FF, $DD, $FF, $55
                db      $FF, $DD, $FF, $77
                db      $FF, $FF, $FF, $77
                db      $FF, $FF, $FF, $FF      ; all of it

; The dither for level A (already four times it) on screen row E, in A.
; Corrupts: AF, HL
dither_for:
                ld      hl, dither_bytes
                add     a, l
                ld      l, a
                ld      a, 0
                adc     a, h
                ld      h, a
                ld      a, e
                and     3
                add     a, l
                ld      l, a
                ld      a, 0
                adc     a, h
                ld      h, a
                ld      a, (hl)
                ret

; Turn a command's y into a screen row, keeping sixteen bits with their sign.
; A picture may name a y above the top or below the bottom, and those have to
; stay outside rather than come round in a byte.  In A, out HL.
; Corrupts: AF, C
row_of:
                ld      c, a
                ld      a, GAC_TOP
                sub     c
                ld      l, a
                sbc     a, a                    ; all ones when it went below
                ld      h, a
                ret

; Bring an x that left the picture to its edge.  In HL, out L.
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

; The same for a row.  In HL, out L.
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

; The byte of the mask holding point (D across, E down) in HL, its bit in B.
; The mask is a plain bitmap, thirty two bytes a row, on a four kilobyte
; boundary, so the row never carries into H.
; Corrupts: AF
mask_address:
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

; The bits of the screen belonging to one point of the picture.  Drawn double,
; a point is two pixels across and the pair never straddles a byte because it
; starts on an even one; drawn single it is one pixel like anywhere else.
                IF PICTURE_SCALE = 2
point_masks:    db      %11000000, %00110000, %00001100, %00000011
                ELSE
point_masks     equ     bit_masks
                ENDIF

; The byte of the screen holding point (D across, E down) in HL, with the bits
; of the point in C.  Four points to the byte drawn double and eight drawn
; single, and the eight lines of a byte column are the eight bytes in a row.
; Corrupts: AF, B
screen_address:
                ld      a, e
                and     %01111000
                rrca
                rrca                    ; twice the row, for a table of words
                ld      hl, picture_rows
                add     a, l
                ld      l, a
                ld      a, 0
                adc     a, h
                ld      h, a
                ld      a, (hl)
                inc     hl
                ld      h, (hl)
                ld      l, a                    ; the first byte of the row
                IF PICTURE_SCALE = 2
                ld      a, d
                and     %11111100
                ld      c, a
                ld      b, 0
                sla     c
                rl      b                       ; eight bytes to four points
                ELSE
                ld      a, d
                and     %11111000
                ld      c, a
                ld      b, 0                    ; and eight bytes to eight
                ENDIF
                add     hl, bc
                ld      a, e
                and     7                       ; and the line inside the row
                add     a, l
                ld      l, a
                ld      a, 0
                adc     a, h
                ld      h, a
                ld      a, d
                and     POINT_MASK
                push    hl
                ld      hl, point_masks
                add     a, l
                ld      l, a
                jr      nc, .no_carry
                inc     h
.no_carry:
                ld      c, (hl)
                pop     hl
                ret

; Put down a pixel of the outline at (D, E), which also stops fills.
; Corrupts: everything but DE
plot_point:
                ld      a, e
                cp      PICTURE_ROWS
                ret     nc                      ; off the picture, leave it
                push    de
                call    mask_address
                ld      a, (hl)
                or      b
                ld      (hl), a
                pop     de
                call    screen_address
                ld      a, (line_lit)
                and     c                       ; the two bits, lit or not
                ld      b, a
                ld      a, c
                cpl
                and     (hl)
                or      b
                ld      (hl), a
                ret

; Whether a fill has to stop at (D, E).  Zero flag clear if it does.  Off the
; picture always stops it.
; Corrupts: AF, BC, HL
is_boundary:
                ld      a, e
                cp      PICTURE_ROWS
                jr      nc, .stops              ; off the top or bottom
                call    mask_address
                ld      a, (hl)
                and     b
                ret
.stops:
                ld      a, 1
                ret

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
; diagonal.
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

pcw_ink:        db      0                       ; the colours as they came
pcw_paper:      db      7
ink_level:      db      0                       ; and as this screen has them
paper_level:    db      16 * 4
line_lit:       db      0                       ; $FF when an outline is white
