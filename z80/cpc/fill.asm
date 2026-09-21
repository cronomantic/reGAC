; MIT License, Copyright (c) 2025 Cronomantic
;
; Filling an area on the Amstrad.
;
; The walk is the same as everywhere else: up and down the one column the fill
; was started in, laying a horizontal run across each row, stopping the moment
; the point directly above or below is blocked.  Two things are this machine's
; own, and both were read off it.
;
; A point blocks when its pen is no longer the pen under the seed, rather than
; when a pixel happens to be set.  That is why a fill here can run over a
; colour and stop at another, which on a one bit screen has no meaning.
;
; And what it lays down is a chequer of two pens, the ones the colour order
; names.  With the two the same it comes out solid; with two different ones it
; is how four pens are made to look like more.  Which of the two a point gets
; turns on the y of the commands, not on the screen row.

PICTURE_TOP     equ 175                 ; the y a picture reaches
PICTURE_BOTTOM  equ 48

FILL_INK        equ 0
FILL_PAPER      equ 1
FILL_SHADE      equ 2

; Whether a fill is stopped at (D across, E up the commands' way).
; Zero flag set while it is still the pen the fill started on.
;
; It is also where the row gets worked out: which screen row it is, where that
; row begins, and the byte and the pixel the fill's own column falls in.  That
; is not tidy, but fill_run wants exactly the same sums and every call here is
; followed by one or by the fill stopping, and working an address out on this
; machine is forty instructions: asking four times a row instead of once was
; an eighth of what a picture cost.
; Corrupts: AF, BC, HL
blocked:
                push    de
                ld      a, e
                call    to_row
                ld      e, a
                ld      d, 0
                call    pixel_address           ; where the row begins
                ld      (row_at), hl
                ld      a, (fill_x)
                call    byte_of                 ; and the column's own byte
                ld      (seed_at), hl
                ld      b, a                    ; which pixel of it
                call    pixel_mask
                ld      (seed_mask), a
                ld      hl, (seed_at)
                ld      a, (hl)
                call    pen_of                  ; the pen of pixel B
                ld      hl, fill_seed
                cp      (hl)
                pop     de
                ret

; Fill from (D across, E up).
; Corrupts: everything
flood_fill:
                ld      a, d
                ld      (fill_x), a
                push    de
                ld      a, e
                call    to_row
                ld      e, a
                call    pen_at
                ld      (fill_seed), a
                pop     de
                cp      255
                ret     z                       ; the seed is off the picture
                call    pen_byte                ; and what four of it look like
                ld      (seed_byte), a
                ld      a, e
                ld      (fill_seed_y), a
                ld      (fill_y), a
.upwards:
                ld      a, (fill_y)
                cp      PICTURE_TOP + 1
                jr      nc, .downwards
                ld      e, a
                ld      a, (fill_x)
                ld      d, a
                call    blocked
                jr      nz, .downwards
                call    fill_run
                ld      hl, fill_y
                inc     (hl)
                jr      .upwards
.downwards:
                ld      a, (fill_seed_y)
                dec     a
                ld      (fill_y), a
.each_below:
                ld      a, (fill_y)
                cp      PICTURE_BOTTOM
                ret     c
                ld      e, a
                ld      a, (fill_x)
                ld      d, a
                call    blocked
                ret     nz
                call    fill_run
                ld      hl, fill_y
                dec     (hl)
                jr      .each_below

; Lay the two pens across the run through (fill_x, fill_y).
; Corrupts: everything
fill_run:
                ; Where the seed is -- the byte it is in and its two bits of
                ; it -- is already worked out, because blocked had to work out
                ; the same thing to answer and this always follows one.
                ; The two walks below keep the byte in HL and the two bits in
                ; C, and step them with a rotate -- moving one pixel to the
                ; right is rrc, and the carry it puts out is exactly "and over
                ; into the next byte".  Which is why neither the address nor
                ; the pen of a point is ever worked out again: a fill looks at
                ; every point of every run it lays, and that was costing a
                ; picture of MegaCorp twenty seconds.  See doc/pendiente.md.
                ; how far it reaches to the left
                ld      a, (fill_x)
                ld      (fill_left), a
                call    from_the_seed
.leftwards:
                ld      a, (fill_left)
                or      a
                jr      z, .left_done
                ; a whole byte at a stride while all four of its pixels are
                ; the seed's pen, which is what most of a run is made of
                ld      a, c
                cp      %10001000               ; standing on the first of one
                jr      nz, .one_to_the_left
                ; Standing on the first pixel of a byte, so everything to the
                ; left of here is whole bytes, and cpd walks them: it compares,
                ; steps and counts in one instruction, which is thirty three
                ; clocks for four pixels against a hundred and thirty eight
                ; asking for each byte the long way round.  How many there are
                ; is the x over four, which is exact because the x is a
                ; multiple of four wherever this is reached.  The count wants
                ; BC, so the pen the walk carries in B is put back afterwards;
                ; C goes back to the pixel it was on, which a whole byte at a
                ; time never moves off.
                ld      a, (fill_left)
                rrca
                rrca                            ; and no mask: the x is a
                ld      c, a                    ; multiple of four here, so
                ld      b, 0                    ; nothing wraps round
                ld      a, (seed_byte)
                dec     hl                      ; the first one to the left
.whole_left:
                cpd
                jr      nz, .left_differs
                jp      pe, .whole_left
                ; every one of them was the seed's, so the run reaches the
                ; edge of the picture and there is nothing more to ask.  What
                ; the walk was carrying is not put back: the walk is over, and
                ; what comes next starts again from the seed.
                xor     a
                ld      (fill_left), a
                jr      .left_done
.left_differs:
                ; the one just looked at is not the seed's, so the run stops
                ; somewhere inside it and its pixels are asked for one at a
                ; time.  What is left in BC says where it stands: the bytes not
                ; walked, without the one it stopped on.  The pen goes back
                ; into B without being read again, because cpd leaves A alone
                ; and A is what it was comparing against.
                ld      b, a
                inc     hl
                inc     hl
                ld      a, c
                inc     a
                add     a, a
                add     a, a                    ; four pixels to each of them
                ld      (fill_left), a
                ld      c, %10001000
.one_to_the_left:
                rlc     c                       ; the pixel to the left of it
                jr      nc, .same_byte_left
                dec     hl
.same_byte_left:
                ld      a, (hl)
                xor     b                       ; where it differs from the pen
                and     c                       ; the fill started on
                jr      nz, .left_done
                ld      a, (fill_left)
                dec     a
                ld      (fill_left), a
                jr      .leftwards
.left_done:
                ld      a, (fill_x)
                ld      (fill_right), a
                call    from_the_seed
.rightwards:
                ld      a, (fill_right)
                inc     a
                jr      z, .right_done          ; the edge of the picture
                ld      a, c
                cp      %00010001               ; standing on the last of one
                jr      nz, .one_to_the_right
                ; The same the other way about, with cpi, and the count is
                ; what is left of the row over four.
                ld      a, (fill_right)
                cpl                             ; 255 less the x, which is
                rrca                            ; again a multiple of four
                rrca
                ld      c, a
                ld      b, 0
                ld      a, (seed_byte)
                inc     hl                      ; the first one to the right
.whole_right:
                cpi
                jr      nz, .right_differs
                jp      pe, .whole_right
                ld      a, 255                  ; out to the edge of the row
                ld      (fill_right), a
                jr      .right_done
.right_differs:
                ld      b, a                    ; the pen, still in A
                dec     hl
                dec     hl
                ld      a, c
                inc     a
                add     a, a
                add     a, a
                cpl                             ; 255 less four to each of them
                ld      (fill_right), a
                ld      c, %00010001
.one_to_the_right:
                rrc     c                       ; the pixel to the right of it
                jr      nc, .same_byte_right
                inc     hl
.same_byte_right:
                ld      a, (hl)
                xor     b
                and     c
                jr      nz, .right_done
                ld      a, (fill_right)
                inc     a
                ld      (fill_right), a
                jr      .rightwards
.right_done:
                ; And then lay it, by bytes and not by points.  Four pixels
                ; to a byte in this mode, and a byte begins at a multiple of
                ; four, so which of the two pens each of its pixels gets turns
                ; on y alone: every whole byte of a run is the same byte, and
                ; only the two at the ends have to be picked apart.  Laying a
                ; point at a time is what made a picture of MegaCorp take
                ; twenty seconds; see doc/pendiente.md.
                call    run_byte
                ld      (fill_byte), a
                ld      a, (fill_left)
                call    byte_of                 ; where it begins
                ld      (fill_from), hl
                ld      (fill_first), a
                ld      a, (fill_right)
                call    byte_of                 ; and where it ends
                ld      (fill_to), hl
                ld      (fill_last), a
                ld      a, (fill_first)
                call    from_pixel
                ld      c, a                    ; from where it begins on
                ld      hl, (fill_from)
                ld      de, (fill_to)
                or      a
                sbc     hl, de
                jr      nz, .several
                ; all of it inside one byte, so cut the mask short at the end
                ld      a, (fill_last)
                call    upto_pixel
                and     c
                ld      hl, (fill_from)
                jp      merge_byte
.several:
                ld      a, c
                ld      hl, (fill_from)
                call    merge_byte
                ld      a, (fill_last)
                call    upto_pixel
                ld      hl, (fill_to)
                call    merge_byte
                ; and the whole bytes between the two ends, which is how
                ; many bytes apart they are less the one that is the end
                ld      hl, (fill_to)
                ld      de, (fill_from)
                or      a
                sbc     hl, de
                ld      b, l
                dec     b
                ret     z                       ; they are next to each other
                ; Laid one at a time.  Eight at a time is a fifth quicker
                ; on the runs long enough to pay for the splitting, and it was
                ; written and measured and handed back: it costs forty odd
                ; bytes, and on this machine the tape build had none to spare.
                ; There is room now that the tune player has gone; see
                ; doc/pendiente.md.
                ld      hl, (fill_from)
                inc     hl
                ld      a, (fill_byte)
.whole:
                ld      (hl), a
                inc     hl
                djnz    .whole
                ret

; Put the walk back where the seed is: the byte in HL, its two bits in C, and
; in B what four pixels of the pen the fill started on look like.
; Corrupts: AF, BC, HL
from_the_seed:
                ld      hl, (seed_at)
                ld      a, (seed_mask)
                ld      c, a
                ld      a, (seed_byte)
                ld      b, a
                ret

; The byte point A of the row being laid is in, and which pixel of it.  Where
; the row begins is already known, so this is a shift and an add rather than
; the forty instructions an address costs from nothing.
; Corrupts: AF, BC, HL
byte_of:
                ld      b, a                    ; the x, kept for its pixel
                rrca
                rrca
                and     %00111111               ; four pixels to a byte
                ld      c, a
                ld      a, b
                ld      b, 0
                ld      hl, (row_at)
                add     hl, bc
                and     3                       ; which of the four it is
                ret

; The byte four whole pixels of the run come to: the two pens woven, with the
; one that goes on an even x in the even pixels.  A byte begins at a multiple
; of four, so that is the same for every whole byte of the run.
; Corrupts: everything
run_byte:
                ld      hl, gfx_pen1
                ld      de, gfx_pen2
                ld      a, (fill_y)
                and     1
                jr      z, .this_way_round
                ex      de, hl
.this_way_round:
                ld      a, (hl)
                call    pen_byte
                and     %10101010               ; pixels nought and two
                ld      c, a
                ld      a, (de)
                call    pen_byte
                and     %01010101               ; and pixels one and three
                or      c
                ret

; Put the bits A names of (fill_byte) into the byte at HL, leaving the rest of
; it as it was.
; Corrupts: AF, BC
merge_byte:
                ld      c, a
                cpl
                and     (hl)
                ld      b, a
                ld      a, (fill_byte)
                and     c
                or      b
                ld      (hl), a
                ret

; The bits of pixel A of a byte and of every pixel after it, and the bits of
; it and of every pixel before it.  The two halves of one table, because the
; second follows the first and four more is all the difference.
; Corrupts: AF, HL
upto_pixel:
                add     a, 4
from_pixel:
                and     7
                ld      hl, pixel_run_bits
                jp      table_byte

pixel_run_bits: db      %11111111, %01110111, %00110011, %00010001
                db      %10001000, %11001100, %11101110, %11111111

; -- what the picture interpreter calls -------------------------------------

gfx_to_words:
                ld      a, (gfx_x0)
                ld      l, a
                ld      h, 0
                ld      (lin_x0), hl
                ld      a, (gfx_y0)
                call    row_of
                ld      (lin_y0), hl
                ld      a, (gfx_x1)
                ld      l, a
                ld      h, 0
                ld      (lin_x1), hl
                ld      a, (gfx_y1)
                call    row_of
                ld      (lin_y1), hl
                ret

gfx_line:
                call    gfx_to_words
                jp      draw_line

gfx_rect:
                call    gfx_to_words
                jp      draw_rect

gfx_ellipse:
                call    gfx_to_words
                jp      draw_ellipse

gfx_plot:
                ld      a, (gfx_x0)
                ld      d, a
                ld      a, (gfx_y0)
                ld      e, a
                jp      plot_point

gfx_fill:
                ld      a, (gfx_x0)
                ld      d, a
                ld      a, (gfx_y0)
                ld      e, a
                jp      flood_fill

; Which of the three fills this is.  The Amstrad has only one: what it lays
; down is whatever the colour order last named, so the three come to the same
; thing here and the pens are left alone.
set_fill_pattern:
                ret

; The picture is finished.  This machine draws straight at its screen, so
; there is nothing to send anywhere.
gfx_show:
                ret

fill_x:         db      0
fill_seed_y:    db      0
fill_y:         db      0
row_at:         dw      0                       ; where the row being laid begins
fill_left:      db      0
fill_right:     db      0
seed_byte:      db      0                       ; four pixels of the seed's pen
seed_at:        dw      0                       ; the byte the seed is in
seed_mask:      db      0                       ; and its two bits of it
fill_byte:      db      0                       ; what a whole four pixels come to
fill_from:      dw      0                       ; the byte the run begins in
fill_to:        dw      0                       ; and the one it ends in
fill_first:     db      0                       ; the pixel of each that is in it
fill_last:      db      0
fill_seed:      db      0
