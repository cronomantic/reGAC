; MIT License, Copyright (c) 2025 Cronomantic
;
; Drawing on an MSX1 in screen 2: the primitives the picture interpreter asks
; for, into the copy of the screen that screen.asm sends to the video chip.
;
; One bit per pixel and a lit pixel stops a fill, exactly as on the Spectrum,
; so there is no mask here and the fill is that machine's.  Two things are
; this one's own: a colour belongs to eight pixels of one line rather than to
; a cell of eight by eight, so a fill lays colour down once a row instead of
; once every eight; and the fifteen colours are not the Spectrum's sixteen, so
; each is matched to the nearest -- by the same table the reference renderer
; works out, which is how the two are held to each other.

GAC_TOP         equ 175                 ; y=175 is the first row of the screen
SHADOW_STEP     equ (SHADOW_COLOURS - SHADOW) >> 8       ; rows between tables

; The nearest colour this machine has to each of the Spectrum's eight, worked
; out by plain distance in red, green and blue.  Bright and flash have nowhere
; to go here, so they are not looked at.
msx_colours:    db      1, 4, 6, 13, 2, 7, 10, 14

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

; The border, which here is one of the video chip's registers.  A routine and
; not a macro of its own because the colour has to go through the table above,
; and the picture interpreter's loop wants its registers back.
; Corrupts: AF
                MACRO   GFX_BORDER
                call    set_border
                ENDM

set_border:
                push    hl
                and     7
                ld      hl, msx_colours
                add     a, l
                ld      l, a
                jr      nc, .no_carry
                inc     h
.no_carry:
                ld      a, (hl)
                out     (VDP_ADDR), a
                ld      a, $87                  ; register seven
                out     (VDP_ADDR), a
                pop     hl
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

; The byte holding pixel (D across, E down) in HL, its bit as a mask in B.
;
; The copy is kept row by row, thirty two bytes to a row, so the row is the
; high byte and the whole of it fits in the low one -- which is what lets the
; fill walk a run with inc l and dec l, as the Spectrum's does.
; Corrupts: AF
pixel_address:
                ld      a, e
                rrca
                rrca
                rrca
                and     %00011111               ; which page of eight rows
                add     a, SHADOW >> 8
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

; The colour of those same eight pixels lives in the other copy, the same
; distance into it.  In HL, out HL.
; Corrupts: AF
to_colour:
                ld      a, h
                add     a, SHADOW_STEP
                ld      h, a
                ret

; Settle the colours in force into the byte this machine wants, once per shape
; rather than once per point.  Matching the Spectrum's sixteen colours to the
; fifteen here is two table lookups and some shifting, and a line of any length
; would pay for them at every pixel.
;
; When one of the colours is an eight, or the ink is nine, the byte depends on
; what is already on the screen and cannot be settled: then colour_varies says
; so and every point works it out for itself, as before.
; Corrupts: AF, BC, HL
settle_colours:
                call    colour_const
                ld      hl, colour_varies
                jr      c, .varies
                ld      (colour_now), a
                ld      (hl), 0
                ret
.varies:
                ld      (hl), 1
                ret

colour_now:     db      0
colour_varies:  db      1

; The colour byte the colours in force come to, when it does not depend on
; what is already there.  Carry clear and the byte in A when it does not;
; carry set when one of them is an eight, meaning leave what is there, or the
; ink is nine, meaning choose against the paper.
; Corrupts: AF, BC, HL
colour_const:
                ld      a, (gfx_ink)
                cp      8
                jr      nc, .varies
                call    msx_colour
                rlca
                rlca
                rlca
                rlca
                ld      c, a
                ld      a, (gfx_paper)
                cp      8
                jr      nc, .varies
                call    msx_colour
                or      c
                ret                             ; carry is clear after OR
.varies:
                scf
                ret

; The colour this machine shows for the Spectrum's colour A.
; Corrupts: AF, HL
msx_colour:
                and     7
                ld      hl, msx_colours
                add     a, l
                ld      l, a
                jr      nc, .no_carry
                inc     h
.no_carry:
                ld      a, (hl)
                ret

; Give the eight pixels holding (D, E) the colours in force.  A colour of
; eight means leave what is there, and an ink of nine means pick black or
; white, whichever will be read against the paper.
; Corrupts: everything but DE
colour_cell:
                push    de
                call    pixel_address
                call    to_colour
                jr      colour_there

; The same, when the address has already been worked out: HL points at the
; colour, and DE has been put away by the caller.  Every point of an outline
; comes through here, which is why the address is not worked out twice.
; Corrupts: everything but DE
colour_at:
                push    de
                ; fall through
colour_there:
                ld      a, (colour_varies)
                or      a
                jr      nz, .the_hard_way
                ld      a, (colour_now)         ; settled for this whole shape
                ld      (hl), a
                pop     de
                ret
.the_hard_way:
                ld      c, (hl)                 ; what is there now
                push    hl
                ld      a, (gfx_paper)
                cp      8
                jr      nc, .keep_paper
                call    msx_colour
                jr      .have_paper
.keep_paper:
                ld      a, c
                and     15
.have_paper:
                ld      e, a                    ; the paper
                ld      a, (gfx_ink)
                cp      8
                jr      c, .plain_ink
                cp      9
                jr      z, .contrast
                ld      a, c                    ; leave the ink alone
                rrca
                rrca
                rrca
                rrca
                jr      .have_ink
.contrast:
                ; Which way this goes is decided on the paper the picture
                ; asked for, not on the colour it came out as: the order of
                ; this machine's fifteen says nothing about how light they are.
                ld      a, (gfx_paper)
                cp      4
                ld      a, 0                    ; black on a light paper
                jr      nc, .dark_ink
                ld      a, 7                    ; white on a dark one
.dark_ink:
                call    msx_colour
                jr      .have_ink
.plain_ink:
                call    msx_colour
.have_ink:
                and     15
                rlca
                rlca
                rlca
                rlca
                or      e
                pop     hl
                ld      (hl), a
                pop     de
                ret

; Put down a pixel of the outline at (D, E), which also stops fills.  The
; address is worked out once and used twice: the pattern is in one copy and
; the colour of those eight pixels is in the other, the same distance in.
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
                call    to_colour
                pop     de
                jp      colour_at

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
