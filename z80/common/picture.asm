; MIT License, Copyright (c) 2025 Cronomantic
;
; The picture interpreter: it walks the drawing commands of a picture and asks
; the machine underneath to put them on the screen.
;
; Nothing here knows how a screen works, what colour means or how many pixels
; there are.  That is all on the other side of gfx_line, gfx_fill and the
; rest, which is the same boundary the Python renderer draws between its
; devices.  See doc/graficos.md.
;
; Two of those commands are handed straight over as macros rather than calls,
; because they are met inside this loop and a picture can meet them tens of
; thousands of times: GFX_BORDER, which most machines do in three
; instructions, and GFX_COLOURS, which is empty on every machine that settles
; its colours once per shape.  A machine whose colours belong to a pixel
; rather than to a cell cannot wait that long -- an ink of nine is settled
; against the paper of the moment, and the paper may change before the shape
; arrives -- so it settles here instead.

GFX_MAX_DEPTH   equ 8                   ; a picture may call others

CMD_BORDER      equ $01
CMD_PLOT        equ $02
CMD_ELLIPSE     equ $03
CMD_FILL        equ $04
CMD_BGFILL      equ $05
CMD_SHADE       equ $06
CMD_CALL        equ $07
CMD_RECT        equ $08
CMD_LINE        equ $09
CMD_INK         equ $10
CMD_PAPER       equ $11
CMD_BRIGHT      equ $12
CMD_FLASH       equ $13
CMD_PENS        equ $14                 ; the two pens a fill weaves, on the
                                        ; machines that have such a thing

; Where the pictures are.
; Corrupts: AF, BC, DE, HL
picture_init:
                ld      a, SECTION_GRAPHICS
                call    db_section
                ld      (gfx_section), hl
                ld      e, (hl)
                inc     hl
                ld      d, (hl)
                inc     hl
                ld      (gfx_count), de
                ld      (gfx_index), hl
                ld      hl, 0                   ; nothing known yet, and no
                ld      (gfx_known), hl         ; picture is numbered zero
                ret

; Find picture HL.  Its commands come back in HL with their length in BC;
; carry set when there is no such picture.
;
; The last one found is kept, because a picture that calls another calls it
; over and over: the animations are built as one small picture called a dozen
; times, from a picture called a dozen times, four deep.  Without this the
; index is walked from the top for every one of those.
; Corrupts: AF, DE
picture_find:
                ld      (gfx_wanted), hl
                ld      de, (gfx_known)
                or      a
                sbc     hl, de
                jr      nz, .look
                ld      hl, (gfx_known_at)
                ld      bc, (gfx_known_size)
                or      a
                ret
.look:
                ld      hl, (gfx_index)
                ld      bc, (gfx_count)
.each:
                ld      a, b
                or      c
                scf
                ret     z
                dec     bc
                ld      e, (hl)
                inc     hl
                ld      d, (hl)
                inc     hl
                push    hl
                ld      hl, (gfx_wanted)
                or      a
                sbc     hl, de
                pop     hl
                jr      z, .found
                inc     hl
                inc     hl
                jr      .each
.found:
                ld      e, (hl)
                inc     hl
                ld      d, (hl)
                ld      hl, (gfx_section)
                add     hl, de                  ; the block for this picture
                ld      c, (hl)
                inc     hl
                ld      b, (hl)
                inc     hl                      ; BC = how many bytes of commands
                ld      (gfx_known_at), hl
                ld      (gfx_known_size), bc
                ld      de, (gfx_wanted)
                ld      (gfx_known), de
                or      a
                ret

; Draw picture HL.
; Corrupts: everything
draw_picture:
                push    hl                      ; clearing treads on HL
                ld      a, SECTION_GRAPHICS     ; printing may have taken the
                call    db_bank_in              ; pictures' bank away
                xor     a
                ld      (gfx_depth), a
                call    gfx_clear
                pop     hl
                call    gfx_start_colours       ; what a picture starts in
                call    run_picture
                jp      gfx_show                ; and let the machine show it

; Draw picture HL without clearing first, which is what CALL needs.
; Corrupts: everything
run_picture:
                call    picture_find
                ret     c
                ld      d, b
                ld      e, c                    ; DE counts the bytes left
.next:
                ld      a, d
                or      e
                ret     z
                dec     de
                ld      a, (hl)
                inc     hl
                ld      c, a
                ; one byte commands first
                cp      CMD_BORDER
                jp      z, .one_byte
                cp      CMD_INK
                jp      z, .one_byte
                cp      CMD_PAPER
                jp      z, .one_byte
                cp      CMD_BRIGHT
                jp      z, .one_byte
                cp      CMD_FLASH
                jp      z, .one_byte
                cp      CMD_PENS
                jp      z, .two_pens
                cp      CMD_CALL
                jp      z, .call_picture
                cp      CMD_PLOT
                jp      z, .two_bytes
                cp      CMD_FILL
                jp      z, .two_bytes
                cp      CMD_BGFILL
                jp      z, .two_bytes
                cp      CMD_SHADE
                jp      z, .two_bytes
                ; the rest take four
                ld      a, (hl)
                inc     hl
                dec     de
                ld      (gfx_x0), a
                ld      a, (hl)
                inc     hl
                dec     de
                ld      (gfx_y0), a
                ld      a, (hl)
                inc     hl
                dec     de
                ld      (gfx_x1), a
                ld      a, (hl)
                inc     hl
                dec     de
                ld      (gfx_y1), a
                call    .keep_place
                ld      a, c
                cp      CMD_LINE
                jr      nz, .not_line
                call    gfx_line
                jr      .resume
.not_line:
                cp      CMD_RECT
                jr      nz, .not_rect
                call    gfx_rect
                jr      .resume
.not_rect:
                call    gfx_ellipse
.resume:
                ld      hl, (gfx_code)
                ld      de, (gfx_left)
                jp      .next

; Drawing treads on every register, so the place in the commands goes to
; memory for as long as that takes.  The commands that only set a colour cost
; nothing at all, which matters: the animations are thousands of them.  That
; is why the border does not come through here either, and why the machine
; gives it as a macro that may only touch AF: one picture of Los pájaros de
; Bangkok sets the border forty three thousand times, and putting the place
; away and fetching it back for each of them cost it a second and three
; quarters, and even the call and the return cost it half a second.
.keep_place:
                ld      (gfx_code), hl
                ld      (gfx_left), de
                ret

.one_byte:
                ld      a, (hl)
                inc     hl
                dec     de
                ld      b, a
                ld      a, c
                cp      CMD_BORDER
                jr      nz, .not_border
                ld      a, b
                GFX_BORDER                      ; the machine knows how
                jp      .next
.not_border:
                push    hl
                ld      hl, gfx_ink
                cp      CMD_INK
                jr      z, .store
                ld      hl, gfx_paper
                cp      CMD_PAPER
                jr      z, .store
                ld      hl, gfx_bright
                cp      CMD_BRIGHT
                jr      z, .store
                ld      hl, gfx_flash
.store:
                ld      (hl), b
                pop     hl
                GFX_COLOURS                     ; only for a machine that has
                jp      .next                   ; to settle them here: see below
.two_pens:
                ld      a, (hl)
                inc     hl
                dec     de
                ld      (gfx_pen1), a
                ld      a, (hl)
                inc     hl
                dec     de
                ld      (gfx_pen2), a
                jp      .next
.two_bytes:
                ld      a, (hl)
                inc     hl
                dec     de
                ld      (gfx_x0), a
                ld      a, (hl)
                inc     hl
                dec     de
                ld      (gfx_y0), a
                call    .keep_place
                ld      a, c
                cp      CMD_PLOT
                jr      nz, .a_fill
                call    gfx_plot
                jr      .resume
.a_fill:
                ld      b, FILL_INK
                cp      CMD_FILL
                jr      z, .fill_kind
                ld      b, FILL_PAPER
                cp      CMD_BGFILL
                jr      z, .fill_kind
                ld      b, FILL_SHADE
.fill_kind:
                ld      a, b
                call    set_fill_pattern
                call    gfx_fill
                jp      .resume
.call_picture:
                ld      a, (hl)
                inc     hl
                dec     de
                ld      c, a
                ld      a, (hl)
                inc     hl
                dec     de
                ld      b, a                    ; the number is two bytes here
                ld      a, (gfx_depth)
                inc     a
                cp      GFX_MAX_DEPTH
                jp      nc, .next               ; too deep, leave it
                ld      (gfx_depth), a
                push    hl                      ; keep our place, draw the
                push    de                      ; other one, then carry on
                ld      h, b
                ld      l, c
                call    run_picture
                pop     de
                pop     hl
                ld      a, (gfx_depth)
                dec     a
                ld      (gfx_depth), a
                jp      .next

gfx_section:    dw      0
gfx_index:      dw      0
gfx_count:      dw      0
gfx_wanted:     dw      0
gfx_known:      dw      0                       ; the last picture looked up
gfx_known_at:   dw      0
gfx_known_size: dw      0
gfx_code:       dw      0
gfx_left:       dw      0
gfx_depth:      db      0
gfx_x0:         db      0
gfx_y0:         db      0
gfx_x1:         db      0
gfx_y1:         db      0
gfx_ink:        db      0
gfx_paper:      db      7
gfx_pen1:       db      1               ; only the machines with pens use these
gfx_pen2:       db      1
gfx_bright:     db      0
gfx_flash:      db      0
