; MIT License, Copyright (c) 2025 Cronomantic
;
; Drawing a picture off an Amstrad on a Spectrum Next, with the Amstrad's
; rules.
;
; An adventure is drawn with the rules of the GAC it was written with, on any
; machine that has room for them, and this one needs nothing it has not got:
; layer 2 is a byte a pixel, so the pen of every point is written into the
; picture and read back out of it, and a fill that stops where the pen changes
; has the pens to look at.  No mask, then -- a build carries this, the
; Amstrad's shapes and amstrad_fill.asm instead of draw.asm, the Spectrum's
; shapes and fill.asm, never both.
;
; A pixel's byte is its pen, nought to three, and the first four entries of
; layer 2's palette are the picture's inks: see picture_inks_set in
; screen.asm.  What is the Amstrad's is the same as on the Amstrad and was
; read off it, in z80/cpc/draw.asm: an outline is drawn in the ink's low two
; bits, and a line lights the same points whichever end it starts from.

; The pen an outline is drawn in, settled when the ink is set.
ink_pen:        db      1

; Put down a pixel of the outline at (D across, E up the commands' way).  A
; picture may reach past the top or the bottom, and those pixels are simply
; not put down.
; Corrupts: everything but DE
plot_point:
                ld      a, e
                call    to_row
                cp      PICTURE_ROWS
                ret     nc
                push    de
                ld      e, a
                call    plot_here
                pop     de
                ret

; Put down a pixel at (D across, E down in screen rows), which is what the
; line works in.
; Corrupts: everything but DE
plot_row:
                ld      a, e
                cp      PICTURE_ROWS
                ret     nc
plot_here:
                call    colour_address
                ld      a, (ink_pen)
                ld      (hl), a
                ret

; Which pen is at (D across, E down in screen rows), in A.  Off the picture
; comes back as 255, which is no pen at all and stops a fill.
; Corrupts: AF, HL
pen_at:
                ld      a, e
                cp      PICTURE_ROWS
                jr      nc, .outside
                call    colour_address
                ld      a, (hl)
                ret
.outside:
                ld      a, 255
                ret

; A straight line between the two points in lin_x0 and lin_x1, which are
; sixteen bit and may lie outside the picture.  Each end is brought to the
; edge first, and then they are put in order along the longer side: on the
; Amstrad a line from A to B lights the same points as one from B to A.
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
                call    order_ends
                jp      line_between

; Put the two ends in order along the longer side, as the firmware does.
; Corrupts: everything
order_ends:
                ld      a, (gfx_x1)
                ld      b, a
                ld      a, (gfx_x0)
                sub     b
                jr      nc, .have_dx
                neg
.have_dx:
                ld      c, a                    ; how far across
                ld      a, (gfx_y1)
                ld      b, a
                ld      a, (gfx_y0)
                sub     b
                jr      nc, .have_dy
                neg
.have_dy:
                cp      c
                jr      z, .by_x
                jr      c, .by_x
                ; the longer side is down the screen, which is up the
                ; commands, so the end with the larger row goes first
                ld      a, (gfx_y0)
                ld      b, a
                ld      a, (gfx_y1)
                cp      b
                ret     c
                ret     z
                jr      .swap
.by_x:
                ld      a, (gfx_x0)
                ld      b, a
                ld      a, (gfx_x1)
                cp      b
                ret     nc
.swap:
                ld      a, (gfx_x0)
                ld      b, a
                ld      a, (gfx_x1)
                ld      (gfx_x0), a
                ld      a, b
                ld      (gfx_x1), a
                ld      a, (gfx_y0)
                ld      b, a
                ld      a, (gfx_y1)
                ld      (gfx_y0), a
                ld      a, b
                ld      (gfx_y1), a
                ret

; The line between two points that are known to be inside, in screen rows.
; The error starts at half the longer side, counts up by the shorter one, and
; when it reaches the longer side it comes off again and that step goes
; diagonal.
; Corrupts: everything
line_between:
                ld      a, (gfx_x0)
                ld      d, a
                ld      a, (gfx_y0)
                ld      e, a
                ld      a, (gfx_x1)
                sub     d
                ld      b, 1
                jr      nc, .have_dx
                neg
                ld      b, -1
.have_dx:
                ld      (line_dx), a
                ld      a, b
                ld      (line_sx), a
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
                ld      a, (line_dx)
                ld      c, a
                ld      a, (line_dy)
                cp      c
                jr      z, .across
                jr      c, .across
                jp      .down
.across:
                call    plot_row
                ld      a, (line_dx)
                srl     a
                ld      (line_err), a
                ld      a, (line_dx)
                or      a
                ret     z
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
                ld      e, a
                ld      a, c
.across_straight:
                ld      (line_err), a
                ld      hl, line_sx
                ld      a, d
                add     a, (hl)
                ld      d, a
                call    plot_row
                pop     bc
                djnz    .across_step
                ret
.down:
                call    plot_row
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
                call    plot_row
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

; The colours a picture starts in.  Pen one, and nothing in the picture data
; says so: the frame every room of the Amstrad adventures draws carries no
; colour order at all and comes out in pen one on the machine.
;
; The picture interpreter calls this with the number of the picture it is
; about to draw in HL, so HL comes back untouched.
; Corrupts: AF
gfx_start_colours:
                ld      a, 1
                ld      (gfx_ink), a
                ld      (gfx_pen1), a
                ld      (gfx_pen2), a
                xor     a
                ld      (gfx_paper), a
                ld      (gfx_bright), a
                ld      (gfx_flash), a
                ld      a, 1
                ; fall through

; The pen of the ink in A, which is its low two bits.
; Corrupts: AF
settle_ink:
                and     3
                ld      (ink_pen), a
                ret

; The colours in force have changed.  An ink of eight or more is the format's
; way of saying leave the colour alone, so only a real one settles anything.
                MACRO   GFX_COLOURS
                ld      a, (gfx_ink)
                cp      8
                call    c, settle_ink
                ENDM

; The border wears the colour of a pen, as an ink is -- the low two bits --
; which is what AmstradDevice does.  The macro the picture interpreter expands
; is the call, and the routine keeps every register but AF.
; Corrupts: AF
                MACRO   GFX_BORDER
                call    set_border
                ENDM

set_border:
                push    hl
                push    bc
                and     3
                ld      (border_pen), a
                call    border_init
                pop     bc
                pop     hl
                ret

; Wipe the picture to pen nought.
; Corrupts: everything
gfx_clear:
                ld      c, 0
                ld      a, PIECE_TOP
                call    clear_piece
                ld      c, 0
                ld      a, PIECE_BOTTOM
                jp      clear_piece
