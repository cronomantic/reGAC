; MIT License, Copyright (c) 2025 Cronomantic
;
; Drawing on a Spectrum Next, into layer 2: a byte a pixel, sixteen colours
; that are the Spectrum's own, and no clash anywhere.
;
; Two things follow from that and they are the whole of what is different
; here.  The first is that a colour belongs to one pixel, so an outline lays
; its colour down as it goes and a fill lays two along a row, one for the
; pattern's lit points and one for the rest; there is no cell to share.
;
; The second is that the picture no longer says where a fill must stop.  On a
; Spectrum a set pixel is both a black mark and a wall, and the artists drew
; against that; with a colour a pixel there is nothing to read back, so a mask
; of one bit a pixel is kept beside the picture and that is what a fill walks.
; It holds exactly what a Spectrum's screen would hold, which is why the
; pictures come out the same, and it is laid out row by row, thirty two bytes
; to a row, so the fill that walks it is the Spectrum's own.

; The mask, four kilobytes on a four kilobyte boundary: a row is the high byte
; of the address and nothing else, which is what lets a run be walked with inc
; l and dec l.
MASK            equ $A000
MASK_BYTES      equ PICTURE_ROWS * 32

; The colours a picture starts in: black on white, as the screen starts.
;
; The picture interpreter calls this with the number of the picture it is
; about to draw in HL, so HL comes back untouched.  It cost the PCW an
; afternoon once.
; Corrupts: AF
gfx_start_colours:
                push    de
                push    hl
                xor     a
                ld      (gfx_ink), a
                ld      (gfx_bright), a
                ld      (gfx_flash), a
                ld      (ink_now), a
                ld      (bright_now), a
                ld      a, START_PAPER
                ld      (gfx_paper), a
                ld      (paper_now), a
                call    settle_colours
                pop     hl
                pop     de
                ret

; The border is the one thing here that is still the old machine's: layer 2
; does not cover it and the ULA still draws it, so it is written the way it
; always was.
                MACRO   GFX_BORDER
                call    set_border
                ENDM

set_border:
                and     7
                ld      (gfx_border), a ; the speaker shares this port
                out     ($FE), a
                ret

; The colours in force have changed, and on this machine they are settled here
; rather than once per shape: an ink of nine means whichever of black and
; white reads against the paper, and the reference settles that the moment the
; command arrives -- which matters, because a picture of Megacorp changes the
; paper afterwards and expects the ink it already had.
                MACRO   GFX_COLOURS
                push    hl                      ; the command interpreter is
                push    de                      ; part way through a picture and
                push    bc                      ; wants all three of these back
                call    settle_colours
                pop     bc
                pop     de
                pop     hl
                ENDM

; Settle the two colours in force into the two bytes a pixel is written with.
;
; The ink and the paper are kept as they came rather than as they came out,
; because a colour of eight means leave the one in force alone and has to be
; told apart from a real colour later.  Bright is a colour of its own here:
; there is no attribute to carry it, so it is simply the top bit of the
; sixteen.
; Corrupts: AF, HL
settle_colours:
                ld      a, (gfx_bright)
                cp      8
                jr      nc, .bright_stands
                ld      (bright_now), a
.bright_stands:
                ld      a, (gfx_paper)
                cp      8
                jr      nc, .paper_stands
                ld      (paper_now), a
.paper_stands:
                ld      a, (gfx_ink)
                cp      8
                jr      c, .ink_given
                cp      9
                jr      nz, .ink_stands
                ld      a, (paper_now)          ; whichever reads against it
                cp      4
                ld      a, 0                    ; black on a light paper
                jr      nc, .ink_given
                ld      a, 7                    ; white on a dark one
.ink_given:
                ld      (ink_now), a
.ink_stands:
                ; and the two bytes, which are the colour and eight more of it
                ; when it is bright
                ld      hl, bright_now
                ld      a, (hl)
                or      a
                ld      a, 0
                jr      z, .no_lift
                ld      a, 8
.no_lift:
                ld      hl, ink_now
                add     a, (hl)
                ld      (line_colour), a
                sub     (hl)
                ld      hl, paper_now
                add     a, (hl)
                ld      (fill_colour), a
                ret

ink_now:        db      0                       ; the last real ones
paper_now:      db      START_PAPER
bright_now:     db      0
line_colour:    db      0                       ; and what they come to
fill_colour:    db      START_PAPER

; The byte of the mask holding pixel (D across, E down) in HL, its bit as a
; mask in B.
;
; The mask is kept row by row, thirty two bytes to a row, so the row is the
; high byte and the whole of it fits in the low one -- which is what lets the
; fill walk a run with inc l and dec l, as the Spectrum's does.
; Corrupts: AF
pixel_address:
                ld      a, e
                rrca
                rrca
                rrca
                and     %00011111               ; which page of eight rows
                add     a, MASK >> 8
                ld      h, a
                ld      a, e
                and     7
                rrca
                rrca
                rrca                            ; the row in it, times thirty two
                ld      l, a
                ld      a, d
                rrca
                rrca
                rrca
                and     %00011111               ; and which byte across
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

; Put down a pixel of the outline at (D, E), which also stops fills: the
; colour into the picture and the bit into the mask.
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
                push    de
                call    colour_address
                ld      a, (line_colour)
                ld      (hl), a
                pop     de
                ret

; Whether a fill has to stop at (D, E).  Zero flag clear if it does.  Off the
; picture always stops it.
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
; called: the error starts at half the longer side, counts up by the shorter
; one, and when it reaches the longer side it comes off again and that step
; goes diagonal.
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
