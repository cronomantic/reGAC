; MIT License, Copyright (c) 2025 Cronomantic
;
; Filling an area, and the handful of routines the picture interpreter calls.
;
; The fill spreads a whole stretch at a time rather than a pixel at a time, and
; keeps only the start of each new stretch it finds above and below.  That is
; what makes its stack small: over the 196 pictures of the eight adventures it
; never went past 28 stretches waiting.
;
; There is a catch that is worth spelling out.  Filling an area with ink does
; not change a single pixel, so the area stays as passable as it was and the
; spreading would go round for ever.  The way out is to light the pixels while
; spreading, which both stops it coming back on itself and costs nothing,
; because every pixel inside an area was unlit to begin with.  Each stretch is
; written down as it is lit, and once the spreading is over the list is walked
; again to put the real colours and marks down.  No fill among the 196 pictures
; painted more than 513 stretches.

FILL_STACK_RUNS equ 128
SPAN_LIST_MAX   equ 768                 ; the worst picture needed 513

FILL_INK        equ 0                   ; recolour, leaving the area unmarked
FILL_PAPER      equ 1                   ; recolour and wipe the marks
FILL_SHADE      equ 2                   ; lay a half tone over it

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
                ld      a, d
                ld      (fill_seed), a
                ld      a, e
                ld      (fill_row), a
                ; how far left the stretch goes
.leftwards:
                ld      a, d
                or      a
                jr      z, .left_end
                dec     d
                call    is_boundary
                jr      z, .leftwards
                inc     d
.left_end:
                ld      a, d
                ld      (fill_left), a
                ; and how far right, starting again from the seed
                ld      a, (fill_seed)
                ld      d, a
.rightwards:
                ld      a, d
                inc     a
                jr      z, .right_end           ; the edge of the screen
                inc     d
                call    is_boundary
                jr      z, .rightwards
                dec     d
.right_end:
                ld      a, d
                ld      (fill_right), a
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

; Light every pixel of the stretch.  This is only a marker; the real marks go
; down afterwards.
; Corrupts: everything
light_span:
                ld      a, (fill_row)
                ld      e, a
                ld      a, (fill_left)
                ld      d, a
.each:
                push    de
                call    pixel_address
                ld      a, (hl)
                or      b
                ld      (hl), a
                pop     de
                ld      a, (fill_right)
                cp      d
                ret     z
                inc     d
                jr      .each

; Walk the stretches that were lit and put the real colours and marks down.
; Corrupts: everything
apply_spans:
                ld      hl, span_list
.each_span:
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
                push    hl
                ld      a, (fill_row)
                ld      e, a
                ld      a, (fill_left)
                ld      d, a
                ld      c, 1                    ; colour the first cell
.each_pixel:
                ; the colour belongs to a cell of eight, not to a pixel, so it
                ; is only worth writing when the stretch crosses into one
                ld      a, d
                and     7
                jr      z, .new_cell
                ld      a, c
                or      a
                jr      z, .same_cell
.new_cell:
                push    bc
                push    de
                call    colour_cell
                pop     de
                pop     bc
.same_cell:
                ld      c, 0
                push    bc
                push    de
                call    fill_pixel
                pop     de
                pop     bc
                ld      a, (fill_right)
                cp      d
                jr      z, .span_done
                inc     d
                jr      .each_pixel
.span_done:
                pop     hl
                jr      .each_span

; Look along row A between fill_left and fill_right, keeping the start of
; every stretch that a fill could still reach.
; Corrupts: everything
scan_row:
                ld      e, a
                ld      a, (fill_left)
                ld      d, a
                ld      c, 0                    ; not inside a stretch
.each:
                push    bc
                push    de
                call    is_boundary
                pop     de
                pop     bc
                jr      nz, .edge
                ld      a, c
                or      a
                jr      nz, .carry_on
                ld      c, 1
                call    push_run
                jr      .carry_on
.edge:
                ld      c, 0
.carry_on:
                ld      a, (fill_right)
                cp      d
                ret     z
                inc     d
                jr      .each

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

fill_sp:        dw      0
fill_seed:      db      0
fill_row:       db      0
fill_left:      db      0
fill_right:     db      0
fill_mode:      db      0
span_end:       dw      0
fill_stack:     ds      FILL_STACK_RUNS * 2
span_list:      ds      SPAN_LIST_MAX * 3
