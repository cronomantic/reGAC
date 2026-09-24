; MIT License, Copyright (c) 2025 Cronomantic
;
; Drawing a picture off a Spectrum on an Amstrad, with the Spectrum's rules.
;
; An adventure is drawn with the rules of the GAC it was written with, on any
; machine; this file is those rules on this screen, and draw.asm, shapes.asm
; and fill.asm are the Amstrad's own, which a build takes instead for an
; adventure written on an Amstrad.  A build carries one or the other, never
; both.  See doc/pendiente.md.
;
; It is the Next's way, which is the Spectrum's.  A set pixel on a Spectrum is
; both a mark and a wall, and with colour a pixel there is nothing to read
; back; so a mask of one bit a pixel is kept beside the picture, laid out as a
; Spectrum's screen would be for these rows, and that is what a fill walks.
;
; What is this machine's is the colour.  It has four pens and the picture has
; sixteen colours, so every picture carries four inks chosen for it and the
; pen each of the sixteen comes to -- worked out when the database is built,
; against the reference, and put in place by picture_inks_set in screen.asm.
; A pixel is then written in the pen its colour comes to.

; The mask: four kilobytes, a row the high byte of the address and the whole
; row in the low one, which is what lets a run be walked with inc l and dec l.
; Where it lives is each build's business, as MASK.
MASK_BYTES      equ PICTURE_ROWS * 32
START_PAPER     equ 7                   ; the screen starts white, as it does

; The pen each of the sixteen colours of the original comes to, for the
; picture on the screen.  Before the first picture, black and the dark blue
; are the paper and everything else the letter, in the firmware's four.
colour_pen:     db      0, 0, 1, 1, 1, 1, 1, 1
                db      0, 1, 1, 1, 1, 1, 1, 1

; Put the pens this picture's colours come to in colour_pen, out of the four
; bytes at HL: two bits a colour, four to a byte, the first in the lowest.
; Corrupts: AF, BC, DE, HL
unpack_pens:
                ld      de, colour_pen
                ld      c, 4
.each_byte:
                ld      a, (hl)
                inc     hl
                ld      b, 4
.each_colour:
                push    af
                and     3
                ld      (de), a
                inc     de
                pop     af
                rrca
                rrca
                djnz    .each_colour
                dec     c
                jr      nz, .each_byte
                ret

; The byte with the pen colour A comes to all the way across.
; Corrupts: AF, HL
colour_byte:
                ld      hl, colour_pen
                call    table_byte
                jp      pen_byte

; The colours a picture starts in: black on white, as the screen starts, and
; the picture laid down white.  gfx_clear wiped it to pen nought, because it
; is called when there is no picture too; this is called once a picture's
; inks are in, which is when white has a pen.
;
; The picture interpreter calls this with the number of the picture it is
; about to draw in HL, so HL comes back untouched.
; Corrupts: AF
gfx_start_colours:
                push    bc
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
                ld      a, (fill_pen_byte)
                or      a
                call    nz, paint_picture
                pop     hl
                pop     de
                pop     bc
                ret

; Lay the byte in A over the whole of the picture.
; Corrupts: AF, BC, DE, HL
paint_picture:
                ld      c, a
                ld      e, 0
.each_row:
                ld      d, 0
                push    bc
                push    de
                call    pixel_address
                pop     de
                pop     bc
                ld      b, 64
.across:
                ld      (hl), c
                inc     hl
                djnz    .across
                inc     e
                ld      a, e
                cp      PICTURE_ROWS
                jr      nz, .each_row
                ret

; The border, in the pen the colour comes to, which is what the reference
; does: a Spectrum border is one of the eight, and here it is a pen like any
; other.  The macro the picture interpreter expands is the call, and the
; routine keeps every register but AF, which is what that promises.
; Corrupts: AF
                MACRO   GFX_BORDER
                call    set_border
                ENDM

set_border:
                push    hl
                push    bc
                and     7
                ld      hl, colour_pen
                call    table_byte
                ld      (border_pen), a
                call    border_init
                pop     bc
                pop     hl
                ret

; The colours in force have changed, and they are settled here rather than
; once per shape: an ink of nine means whichever of black and white reads
; against the paper, and the reference settles that the moment the command
; arrives.
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
; told apart from a real colour later.  Bright is a colour of its own: the
; sixteen are the eight and the eight bright, and each has its pen.
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
                ld      a, (bright_now)
                or      a
                jr      z, .no_lift
                ld      a, 8
.no_lift:
                ld      hl, ink_now
                add     a, (hl)
                push    af
                call    colour_byte
                ld      (line_pen_byte), a
                pop     af
                ld      hl, ink_now
                sub     (hl)
                ld      hl, paper_now
                add     a, (hl)
                call    colour_byte
                ld      (fill_pen_byte), a
                ret

ink_now:        db      0                       ; the last real ones
paper_now:      db      START_PAPER
bright_now:     db      0
line_pen_byte:  db      0                       ; and the pens they come to, all
fill_pen_byte:  db      0                       ; four pixels of a byte in them

; The byte of the mask holding pixel (D across, E down) in HL, its bit as a
; mask in B.
; Corrupts: AF
mask_address:
                call    mask_row
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
                call    table_byte
                pop     hl
                ld      b, a
                ret

; The address of column zero of row E in the mask, in HL.
; Corrupts: AF
mask_row:
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
                ret

bit_masks:      db      %10000000, %01000000, %00100000, %00010000
                db      %00001000, %00000100, %00000010, %00000001

; Put down a pixel of the outline at (D, E down in screen rows), which also
; stops fills: its pen into the picture and its bit into the mask.
; Corrupts: everything but DE
plot_point:
                ld      a, e
                cp      PICTURE_ROWS
                ret     nc                      ; off the picture, leave it
                call    mask_address
                ld      a, (hl)
                or      b
                ld      (hl), a
                push    de
                call    pixel_address           ; HL the byte, A the pixel
                ld      de, pixel_masks
                add     a, e
                ld      e, a
                jr      nc, .no_carry
                inc     d
.no_carry:
                ld      a, (de)
                ld      c, a                    ; the pixel's own bits
                cpl
                and     (hl)                    ; everything but this pixel
                ld      b, a
                ld      a, (line_pen_byte)
                and     c
                or      b
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
                call    mask_address
                ld      a, (hl)
                and     b
                ret
.stops:
                ld      a, 1
                or      a
                ret

; A straight line between the two points in lin_x0 and lin_x1, which are
; sixteen bit and may lie outside the picture.
;
; Each end is brought to the edge before anything else, which is what GAC does
; at $643C, and only then are the two deltas worked out in a byte.
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
                call    plot_point
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
                call    plot_point
                pop     bc
                djnz    .across_step
                ret

.down:
                call    plot_point
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
                call    plot_point
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

; Wipe the picture and the mask with it: the mask to nothing, because a wiped
; picture stops no fill, and the picture's rows to pen nought, which is the
; paper the text is printed on -- see wipe_picture_rows.  A picture about to
; be drawn is then laid white by gfx_start_colours, once its inks are in.
; Corrupts: everything
gfx_clear:
                ld      hl, MASK
                ld      de, MASK + 1
                ld      bc, MASK_BYTES - 1
                ld      (hl), 0
                ldir
                jp      wipe_picture_rows
