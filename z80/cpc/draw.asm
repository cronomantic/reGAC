; MIT License, Copyright (c) 2025 Cronomantic
;
; Putting points and lines on an Amstrad, in mode 1.
;
; Four pens to a pixel and four pixels to a byte, and the two bits of a pixel
; are not next to each other: pixel n takes bit 7-n and bit 3-n.  So a byte
; with one pen all the way across is $00, $F0, $0F or $FF, and masking one of
; those with the pixel's own two bits gives what to write.
;
; The screen is at $C000 in eight blocks of one line in eight, the way the
; Spectrum's thirds are but more so.  The picture is 256 wide on a screen of
; 320, so it sits 32 pixels in, which is a whole byte and saves the trouble.
;
; What this machine does that the Spectrum does not was measured on a real one
; and is written up in doc/graficos.md: a line is the same whichever end it
; starts from, and an ellipse counts in halves of a pixel.

GAC_TOP         equ 175                 ; y=175 is its first row
; The pens with all four pixels the same, which is what SCR INK ENCODE gives.
pen_bytes:      db      $00, $F0, $0F, $FF
; The two bits belonging to each pixel of a byte.
pixel_masks:    db      %10001000, %01000100, %00100010, %00010001

; Turn a command's y into a screen row, keeping sixteen bits with their sign.
; In A, out HL.
; Corrupts: AF, C
row_of:
                ld      c, a
                ld      a, GAC_TOP
                sub     c
                ld      l, a
                sbc     a, a
                ld      h, a
                ret

; Bring an x that left the picture to its edge.  In HL, out L.
; Corrupts: AF
clamp_x:
                ld      a, h
                or      a
                ret     z
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

; The byte holding pixel (D across, E down) in HL, and which of its four
; pixels it is in A.
; Corrupts: AF, BC
pixel_address:
                ld      a, e
                and     7
                add     a, a
                add     a, a
                add     a, a                    ; the line within its block
                or      SCREEN >> 8
                ld      h, a
                ld      l, 0
                ld      a, e
                rrca
                rrca
                rrca
                and     $1F                     ; which block
                add     a, a                    ; two bytes to an entry
                ld      c, a
                ld      b, 0
                push    hl
                ld      hl, block_starts
                add     hl, bc
                ld      c, (hl)
                inc     hl
                ld      b, (hl)
                pop     hl
                add     hl, bc
                ld      a, d
                rrca
                rrca
                and     $3F                     ; four pixels to a byte
                add     a, PICTURE_LEFT / 4
                ld      c, a
                ld      b, 0
                add     hl, bc
                ld      a, d
                and     3
                ret

; The byte with the pen in A all the way across.
; Corrupts: AF, HL
pen_byte:
                and     3
                ld      hl, pen_bytes
                jr      table_byte

; The two bits belonging to pixel A of a byte.
; Corrupts: AF, HL
pixel_mask:
                and     3
                ld      hl, pixel_masks
                ; fall through

; Entry A of the table at HL.  Every one of these tables is four or eight
; bytes long and the index is small, so the carry is the whole of the care.
; Corrupts: AF, HL
table_byte:
                add     a, l
                ld      l, a
                jr      nc, .no_carry
                inc     h
.no_carry:
                ld      a, (hl)
                ret

; Put down a pixel of the outline at (D across, E up the commands' way).
; This is where a y becomes a screen row, and the only place: a picture may
; reach past the top or the bottom, and those pixels are simply not put down.
; Corrupts: everything but DE
plot_point:
                ld      a, e
                call    to_row
                cp      PICTURE_ROWS
                ret     nc
                push    de
                ld      e, a
                call    pixel_address
                push    hl
                call    pixel_mask
                ld      c, a                    ; the pixel's own bits
                ld      a, (ink_byte)           ; settled when the ink was set
                and     c
                ld      b, a                    ; the pen, in place
                ld      a, c
                cpl
                pop     hl
                and     (hl)                    ; everything but this pixel
                or      b
                ld      (hl), a
                pop     de
                ret

; Which pen is at (D across, E down in screen rows), in A.  Off the picture
; comes back as 255, which is no pen at all and stops a fill.
; Corrupts: everything but DE
pen_at:
                ld      a, e
                cp      PICTURE_ROWS
                jr      nc, .outside
                push    de
                call    pixel_address           ; HL the byte, A the pixel
                ld      b, a
                ld      a, (hl)
                call    pen_of
                pop     de
                ret
.outside:
                ld      a, 255
                ret

; The pen of pixel B of the byte in A.
;
; A pixel's two bits are seven less its number and three less its number, and
; pen_bytes says which is which: pen one is $F0, so the high one is the pen's
; low bit and the low one its high bit.  Rotating the byte left by the pixel's
; number brings them to seven and three whatever pixel it was, and then they
; are two ands and a shift.  What was here before walked the four pens
; comparing masked bytes, which is four times the work for every point a fill
; looks at; see doc/pendiente.md.
; Corrupts: AF, BC
pen_of:
                inc     b
.align:
                dec     b
                jr      z, .aligned
                rlca
                jr      .align
.aligned:
                ld      c, a
                and     %00001000               ; bit three, the pen's high bit
                rrca
                rrca                            ; down to bit one
                ld      b, a
                ld      a, c
                rlca                            ; bit seven round to bit nought
                and     %00000001
                or      b
                ret

; Turn a command's y into a screen row, in A.  Out A.
to_row:
                neg
                add     a, GAC_TOP
                ret

; A straight line between the two points in lin_x0 and lin_x1, which are
; sixteen bit and may lie outside the picture.
;
; Each end is brought to the edge first, and then they are put in order along
; the longer side: on this machine a line from A to B lights the same points
; as one from B to A, which was measured, and the Spectrum's ROM does not do
; that.
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
                ; the rows are screen rows here, and the commands' y counts
                ; the other way, so the ends are put in order to match
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
                push    de
                call    plot_row
                pop     de
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
                push    de
                call    plot_row
                pop     de
                pop     bc
                djnz    .across_step
                ret
.down:
                push    de
                call    plot_row
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
                call    plot_row
                pop     de
                pop     bc
                djnz    .down_step
                ret

; Put down a pixel at (D across, E down in screen rows), which is what the
; line works in; plot_point takes the commands' y instead.
; Corrupts: everything but DE
plot_row:
                ld      a, e
                cp      PICTURE_ROWS
                ret     nc
                push    de
                call    pixel_address
                push    hl
                call    pixel_mask
                ld      c, a
                ld      a, (ink_byte)           ; settled when the ink was set
                and     c
                ld      b, a
                ld      a, c
                cpl
                pop     hl
                and     (hl)
                or      b
                ld      (hl), a
                pop     de
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
                ld      a, 1                    ; and the pen that ink comes to
                jp      settle_ink

; The colours in force have changed, and on this machine that is where the ink
; is turned into one of the four pens.  An ink of eight or more is the format's
; way of saying leave the colour alone -- it came from a machine whose BASIC
; spelt transparent that way -- so only a real one settles anything, and the
; carry the compare leaves does the asking without a jump.
                MACRO   GFX_COLOURS
                ld      a, (gfx_ink)
                cp      8
                call    c, settle_ink
                ENDM

; The pen of the ink in A, kept for the plotting to use.  Here and not at each
; point because a picture sets a colour a few thousand times and plots a few
; hundred thousand: what the two sites did before was a load, a call and a walk
; through a table for every point, and now it is a load.
; Corrupts: AF
settle_ink:
                push    hl
                call    pen_byte
                ld      (ink_byte), a
                pop     hl
                ret

ink_byte:       db      $F0                     ; pen one, where a picture starts

; The border, which here is one more pen.  Too long to put inline, so the
; macro the picture interpreter expands is the call, and the routine keeps
; every register but AF, which is what that promises.
; Corrupts: AF
                MACRO   GFX_BORDER
                call    set_border
                ENDM

set_border:
                push    hl
                push    bc
                push    af
                ld      bc, GATE_ARRAY
                ld      a, %01010000
                out     (c), a
                pop     af
                call    hardware_ink
                or      %01000000
                ld      bc, GATE_ARRAY
                out     (c), a
                pop     bc
                pop     hl
                ret

; Wipe the picture area to pen nought.  It is 64 bytes of every line, 32
; pixels in from the left, and 128 lines of them.
; Corrupts: everything
gfx_clear:
                ld      e, 0
.each_row:
                ld      d, 0
                push    de
                call    pixel_address
                ld      b, 64
                xor     a
.across:
                ld      (hl), a
                inc     hl
                djnz    .across
                pop     de
                inc     e
                ld      a, e
                cp      PICTURE_ROWS
                jr      nz, .each_row
                ret
