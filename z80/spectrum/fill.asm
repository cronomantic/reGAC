; MIT License, Copyright (c) 2025 Cronomantic
;
; Filling an area, and the handful of routines the picture interpreter calls.
;
; Written the way these routines were written at the time, which matters more
; here than anywhere else: the address of a pixel is never worked out twice.
; A row of the screen is thirty two bytes whose low five bits are the column,
; so once the start of a row is known, moving along it is inc l and dec l, and
; moving from pixel to pixel is rotating a mask.  Whole bytes are eight pixels
; at a stroke, which is where most of the work goes: a byte of zero is eight
; clear pixels and a byte of 255 is eight boundaries.
;
; The spreading itself takes a whole stretch at a time and keeps only the
; start of each new stretch it finds above and below.  Over the 196 pictures
; of the eight adventures it never had more than 28 stretches waiting.
;
; One catch is worth spelling out.  Filling an area with ink changes no pixel
; at all, so the area stays as passable as it was and the spreading would go
; round for ever.  The way out is to light the pixels while spreading, which
; costs nothing because every pixel inside an area was unlit to begin with.
; Each stretch is written down as it is lit, and once the spreading is over
; the list is walked again to put the real colours and marks down.  No fill
; among the 196 pictures painted more than 513 stretches.

FILL_STACK_RUNS equ 128
SPAN_LIST_MAX   equ 768                 ; the worst picture needed 513

FILL_INK        equ 0                   ; recolour, leaving the area unmarked
FILL_PAPER      equ 1                   ; recolour and wipe the marks
FILL_SHADE      equ 2                   ; lay a half tone over it

; The address of column zero of row E, in HL.  The thirty two bytes of the row
; follow in L, so nothing after this needs the address working out again.
; Corrupts: AF
row_address:
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
                ret

; Spread out from (D, E) until the boundaries stop it.
; Corrupts: everything
flood_fill:
                ld      hl, fill_stack
                ld      (fill_sp), hl
                ld      hl, span_list
                ld      (span_end), hl
                call    is_boundary
                ret     nz
                call    push_run
.next_run:
                call    pop_run
                jp      c, apply_spans
                call    is_boundary
                jr      nz, .next_run
                ld      a, e
                ld      (fill_row), a
                call    span_extent             ; fill_left and fill_right
                call    write_down_span
                call    light_span              ; so the spreading cannot return
                ; then look for fresh stretches above and below
                ld      a, (fill_row)
                or      a
                jr      z, .nothing_above
                dec     a
                call    scan_row
.nothing_above:
                ld      a, (fill_row)
                inc     a
                cp      PICTURE_ROWS
                jr      nc, .nothing_below
                call    scan_row
.nothing_below:
                jr      .next_run

; How far the clear stretch through (D, E) reaches, into fill_left and
; fill_right.  The address is worked out once and the mask rotated from there.
; Corrupts: everything
span_extent:
                call    row_address
                ld      (row_base), hl
                ld      a, d
                ld      (fill_left), a
                ld      (fill_right), a
                ; leftwards
                call    point_at
.leftwards:
                ld      a, (fill_left)
                or      a
                jr      z, .left_done
                rlc     b                       ; one pixel to the left
                jr      nc, .same_byte_left
                dec     l                       ; over into the byte before
.same_byte_left:
                ld      a, (hl)
                and     b
                jr      nz, .left_done
                ld      a, (fill_left)
                dec     a
                ld      (fill_left), a
                jr      .leftwards
.left_done:
                ; rightwards, starting again from where we came in
                ld      a, d
                ld      (fill_right), a
                call    point_at
.rightwards:
                ld      a, (fill_right)
                inc     a
                jr      z, .right_done          ; the edge of the screen
                rrc     b                       ; one pixel to the right
                jr      nc, .same_byte_right
                inc     l                       ; over into the next byte
.same_byte_right:
                ld      a, (hl)
                and     b
                ret     nz
                ld      a, (fill_right)
                inc     a
                ld      (fill_right), a
                jr      .rightwards
.right_done:
                ret

; Point HL at the byte holding column A of the row, with B the bit mask.
; Corrupts: AF
point_at:
                push    de
                ld      e, a
                srl     a
                srl     a
                srl     a                       ; which byte across
                ld      hl, (row_base)
                or      l
                ld      l, a
                ld      a, e
                and     7
                ld      de, bit_masks
                add     a, e
                ld      e, a
                ld      a, (de)
                ld      b, a
                pop     de
                ret

; Keep where this stretch was: its row, and where it starts and ends.
; Corrupts: AF, HL
write_down_span:
                push    de
                ld      hl, (span_end)
                ld      de, span_list + SPAN_LIST_MAX * 3
                or      a
                sbc     hl, de
                jr      nc, .no_room
                add     hl, de
                ld      a, (fill_row)
                ld      (hl), a
                inc     hl
                ld      a, (fill_left)
                ld      (hl), a
                inc     hl
                ld      a, (fill_right)
                ld      (hl), a
                inc     hl
                ld      (span_end), hl
.no_room:
                pop     de
                ret

; Work out where a stretch sits in bytes: HL at its first byte, C how many
; whole bytes follow the first, and the masks for the two ends.
; Corrupts: AF, DE
span_bytes:
                ld      a, (fill_row)
                ld      e, a
                call    row_address
                ld      (row_base), hl
                ; the mask at the left end: everything from that bit rightwards
                ld      a, (fill_left)
                and     7
                ld      de, mask_from
                add     a, e
                ld      e, a
                ld      a, (de)
                ld      (span_first), a
                ; and at the right end: everything up to that bit
                ld      a, (fill_right)
                and     7
                ld      de, mask_to
                add     a, e
                ld      e, a
                ld      a, (de)
                ld      (span_last), a
                ; how many bytes the stretch covers
                ld      a, (fill_right)
                srl     a
                srl     a
                srl     a
                ld      c, a
                ld      a, (fill_left)
                srl     a
                srl     a
                srl     a
                ld      b, a
                ld      hl, (row_base)
                or      l
                ld      l, a                    ; the first byte of the stretch
                ld      a, c
                sub     b
                ld      c, a                    ; bytes after the first
                ret

; Light every pixel of the stretch, eight at a time.  This is only a marker;
; the real marks go down afterwards.
; Corrupts: everything
light_span:
                call    span_bytes
                ld      a, c
                or      a
                jr      nz, .several
                ; all inside one byte
                ld      a, (span_first)
                ld      b, a
                ld      a, (span_last)
                and     b
                or      (hl)
                ld      (hl), a
                ret
.several:
                ld      a, (span_first)
                or      (hl)
                ld      (hl), a
                inc     l
                dec     c
                jr      z, .last
.middle:
                ld      (hl), $FF               ; eight pixels at a stroke
                inc     l
                dec     c
                jr      nz, .middle
.last:
                ld      a, (span_last)
                or      (hl)
                ld      (hl), a
                ret

; Look along row A between fill_left and fill_right, keeping the start of
; every stretch that a fill could still reach.  Whole bytes are dealt with as
; whole bytes: zero is eight clear pixels, 255 is eight boundaries.
; Corrupts: everything
scan_row:
                ld      (scan_line), a
                ld      e, a
                call    row_address
                ld      (scan_base), hl
                ld      a, (fill_left)
                ld      (scan_x), a
                ld      c, 0                    ; not inside a stretch
.each_pixel:
                ld      a, (scan_x)
                and     7
                jr      nz, .test_bit
                ; at the start of a byte: can eight be settled at once?
                ld      a, (fill_right)
                ld      b, a
                ld      a, (scan_x)
                add     a, 7
                jr      c, .test_bit
                cp      b
                jr      nc, .test_bit           ; the stretch ends inside it
                call    byte_at_scan
                ld      a, (hl)
                or      a
                jr      z, .eight_clear
                inc     a
                jr      z, .eight_solid
                jr      .test_bit
.eight_clear:
                ld      a, c
                or      a
                jr      nz, .skip_eight
                ld      c, 1
                call    remember_here
.skip_eight:
                ld      a, (scan_x)
                add     a, 8
                ld      (scan_x), a
                jr      .more_left
.eight_solid:
                ld      c, 0
                ld      a, (scan_x)
                add     a, 8
                ld      (scan_x), a
                jr      .more_left
.test_bit:
                call    byte_at_scan            ; HL at the byte, B the mask
                ld      a, (hl)
                and     b
                jr      nz, .a_boundary
                ld      a, c
                or      a
                jr      nz, .step_on
                ld      c, 1
                call    remember_here
                jr      .step_on
.a_boundary:
                ld      c, 0
.step_on:
                ld      a, (scan_x)
                inc     a
                ld      (scan_x), a
.more_left:
                ld      a, (fill_right)
                ld      b, a
                ld      a, (scan_x)
                dec     a
                cp      b
                ret     nc                      ; past the end of the stretch
                jr      .each_pixel

; HL at the byte holding scan_x on the row being scanned, B its bit mask.
byte_at_scan:
                push    de
                ld      hl, (scan_base)
                ld      (row_base), hl
                pop     de
                ld      a, (scan_x)
                jp      point_at

; Keep where the scan is, as the start of a stretch to come back to.
; Corrupts: AF
remember_here:
                push    de
                ld      a, (scan_x)
                ld      d, a
                ld      a, (scan_line)
                ld      e, a
                call    push_run
                pop     de
                ret

; Walk the stretches that were lit and put the real colours and marks down.
; Corrupts: everything
apply_spans:
                ld      hl, span_list
                ld      (span_at), hl
.each_span:
                ld      hl, (span_at)
                ld      de, (span_end)
                push    hl
                or      a
                sbc     hl, de
                pop     hl
                ret     nc                      ; every stretch dealt with
                ld      a, (hl)
                ld      (fill_row), a
                inc     hl
                ld      a, (hl)
                ld      (fill_left), a
                inc     hl
                ld      a, (hl)
                ld      (fill_right), a
                inc     hl
                ld      (span_at), hl
                call    colour_span
                call    mark_span
                jr      .each_span

; Give every cell the stretch passes through the colours in force.  A colour
; belongs to a cell of eight by eight, so this steps by bytes.
; Corrupts: everything
colour_span:
                ld      a, (fill_row)
                ld      e, a
                ld      a, (fill_left)
                ld      d, a
                ld      a, (fill_right)
                srl     a
                srl     a
                srl     a
                ld      c, a                    ; the last byte across
.each_cell:
                push    bc
                push    de
                call    colour_cell
                pop     de
                pop     bc
                ld      a, d
                srl     a
                srl     a
                srl     a
                cp      c
                ret     z
                ; on to the first pixel of the next cell
                ld      a, d
                and     %11111000
                add     a, 8
                ld      d, a
                jr      .each_cell

; Put the real marks down over the stretch, eight pixels at a time.
; Corrupts: everything
mark_span:
                ; the pattern is worked out first, because span_bytes leaves HL
                ; pointing at the stretch and that must not be trodden on
                ld      a, (fill_mode)
                cp      FILL_SHADE
                jr      nz, .plain
                ; a half tone.  It is a pattern eight rows deep, one byte to a
                ; row, which is what makes it cost the same as a plain fill:
                ; one byte written covers eight pixels either way.  A different
                ; dither is a change to the table and nothing else.
                ld      a, (fill_row)
                and     7
                ld      hl, shade_pattern
                add     a, l
                ld      l, a
                jr      nc, .pattern_row
                inc     h
.pattern_row:
                ld      a, (hl)
                jr      .have_pattern
.plain:
                xor     a                       ; the marker pixels go out again
.have_pattern:
                ld      (span_pattern), a
                call    span_bytes
                ld      a, c
                or      a
                jr      nz, .several
                ld      a, (span_first)
                ld      b, a
                ld      a, (span_last)
                and     b
                call    .blend
                ret
.several:
                ld      a, (span_first)
                call    .blend
                inc     l
                dec     c
                jr      z, .last
.middle:
                ld      a, (span_pattern)
                ld      (hl), a
                inc     l
                dec     c
                jr      nz, .middle
.last:
                ld      a, (span_last)
                call    .blend
                ret
; Put the pattern where the mask says, leaving the rest of the byte alone.
.blend:
                ld      b, a
                cpl
                and     (hl)
                ld      d, a                    ; C carries the byte count
                ld      a, (span_pattern)
                and     b
                or      d
                ld      (hl), a
                ret

; Keep (D, E) for later.  Stretches are dropped rather than overflowing, which
; cannot happen with any of the pictures to hand.
; Corrupts: AF
push_run:
                push    hl
                ld      hl, (fill_sp)
                ld      a, h
                cp      high (fill_stack + FILL_STACK_RUNS * 2)
                jr      c, .room
                ld      a, l
                cp      low (fill_stack + FILL_STACK_RUNS * 2)
                jr      nc, .full
.room:
                ld      (hl), d
                inc     hl
                ld      (hl), e
                inc     hl
                ld      (fill_sp), hl
.full:
                pop     hl
                ret

; Take one back into (D, E).  Carry set when there are none left.
; Corrupts: AF
pop_run:
                push    hl
                ld      hl, (fill_sp)
                ld      de, fill_stack
                or      a
                sbc     hl, de
                jr      z, .empty
                add     hl, de
                dec     hl
                ld      e, (hl)
                dec     hl
                ld      d, (hl)
                ld      (fill_sp), hl
                pop     hl
                or      a
                ret
.empty:
                pop     hl
                scf
                ret

; -- what the picture interpreter calls -------------------------------------

; The y in the commands counts up from the bottom of the screen; the screen
; counts rows down from the top.
gfx_to_rows:
                ld      a, (gfx_y0)
                call    to_row
                ld      (gfx_y0), a
                ld      a, (gfx_y1)
                call    to_row
                ld      (gfx_y1), a
                ret

gfx_line:
                call    gfx_to_rows
                jp      draw_line

gfx_rect:
                call    gfx_to_rows
                jp      draw_rect

gfx_ellipse:
                call    gfx_to_rows
                jp      draw_ellipse

gfx_plot:
                call    gfx_to_rows
                call    gfx_start_point
                jp      plot_point

gfx_fill:
                call    gfx_to_rows
                call    gfx_start_point
                jp      flood_fill

gfx_start_point:
                ld      a, (gfx_x0)
                ld      d, a
                ld      a, (gfx_y0)
                ld      e, a
                ret

; Wipe the picture area and give it back the colours it starts with.
; Corrupts: everything
gfx_clear:
                ld      hl, $4000
                ld      de, $4001
                ld      bc, PICTURE_ROWS * 32 - 1
                ld      (hl), 0
                ldir
                ld      hl, ATTRIBUTES
                ld      de, ATTRIBUTES + 1
                ld      bc, (PICTURE_ROWS / 8) * 32 - 1
                ld      (hl), $38               ; black on white, as it starts
                ldir
                ret

; Every bit from this one rightwards, and every bit up to this one.
; The half tone, eight rows of it.
shade_pattern:  db      %10101010, %01010101, %10101010, %01010101
                db      %10101010, %01010101, %10101010, %01010101

; Every bit from this one rightwards, and every bit up to this one.
mask_from:      db      %11111111, %01111111, %00111111, %00011111
                db      %00001111, %00000111, %00000011, %00000001
mask_to:        db      %10000000, %11000000, %11100000, %11110000
                db      %11111000, %11111100, %11111110, %11111111

fill_sp:        dw      0
fill_row:       db      0
fill_left:      db      0
fill_right:     db      0
fill_mode:      db      0
row_base:       dw      0
scan_base:      dw      0
scan_line:      db      0
scan_x:         db      0
span_first:     db      0
span_last:      db      0
span_pattern:   db      0
span_end:       dw      0
span_at:        dw      0
fill_stack:     ds      FILL_STACK_RUNS * 2
span_list:      ds      SPAN_LIST_MAX * 3
