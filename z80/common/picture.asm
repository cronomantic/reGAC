; MIT License, Copyright (c) 2025 Cronomantic
;
; The picture interpreter: it walks the drawing commands of a picture and asks
; the machine underneath to put them on the screen.
;
; Nothing here knows how a screen works, what colour means or how many pixels
; there are.  That is all on the other side of gfx_line, gfx_fill and the
; rest, which is the same boundary the Python renderer draws between its
; devices.  See doc/graficos.md.

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
                ret

; Find picture HL.  Its commands come back in HL with their length in BC;
; carry set when there is no such picture.
; Corrupts: AF, DE
picture_find:
                ld      (gfx_wanted), hl
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
                or      a
                ret

; Draw picture HL.
; Corrupts: everything
draw_picture:
                push    hl                      ; clearing treads on HL
                xor     a
                ld      (gfx_depth), a
                call    gfx_clear
                pop     hl
                ; the colours a picture starts with
                xor     a
                ld      (gfx_ink), a
                ld      (gfx_bright), a
                ld      (gfx_flash), a
                ld      a, 7
                ld      (gfx_paper), a
                jr      run_picture

; Draw picture HL without clearing first, which is what CALL needs.
; Corrupts: everything
run_picture:
                call    picture_find
                ret     c
                ld      (gfx_code), hl
                ld      (gfx_left), bc
.next:
                ld      bc, (gfx_left)
                ld      a, b
                or      c
                ret     z
                dec     bc
                ld      (gfx_left), bc
                ld      hl, (gfx_code)
                ld      a, (hl)
                inc     hl
                ld      (gfx_code), hl
                ld      c, a
                ; one byte commands first
                cp      CMD_INK
                jr      z, .one_byte
                cp      CMD_PAPER
                jr      z, .one_byte
                cp      CMD_BRIGHT
                jr      z, .one_byte
                cp      CMD_FLASH
                jr      z, .one_byte
                cp      CMD_BORDER
                jr      z, .one_byte
                cp      CMD_CALL
                jp      z, .call_picture
                cp      CMD_PLOT
                jr      z, .two_bytes
                cp      CMD_FILL
                jr      z, .two_bytes
                cp      CMD_BGFILL
                jr      z, .two_bytes
                cp      CMD_SHADE
                jr      z, .two_bytes
                ; the rest take four
                call    take_byte
                ld      (gfx_x0), a
                call    take_byte
                ld      (gfx_y0), a
                call    take_byte
                ld      (gfx_x1), a
                call    take_byte
                ld      (gfx_y1), a
                ld      a, c
                cp      CMD_LINE
                jr      nz, .not_line
                call    gfx_line
                jp      .next
.not_line:
                cp      CMD_RECT
                jr      nz, .not_rect
                call    gfx_rect
                jp      .next
.not_rect:
                call    gfx_ellipse
                jp      .next
.one_byte:
                call    take_byte
                ld      b, a
                ld      a, c
                cp      CMD_BORDER
                jr      nz, .not_border
                ld      a, b
                and     7
                out     ($FE), a
                jp      .next
.not_border:
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
                jp      .next
.two_bytes:
                call    take_byte
                ld      (gfx_x0), a
                call    take_byte
                ld      (gfx_y0), a
                ld      a, c
                cp      CMD_PLOT
                jr      nz, .a_fill
                call    gfx_plot
                jp      .next
.a_fill:
                ld      b, FILL_INK
                cp      CMD_FILL
                jr      z, .fill_mode
                ld      b, FILL_PAPER
                cp      CMD_BGFILL
                jr      z, .fill_mode
                ld      b, FILL_SHADE
.fill_mode:
                ld      a, b
                ld      (fill_mode), a
                call    gfx_fill
                jp      .next
.call_picture:
                call    take_byte
                ld      e, a
                call    take_byte
                ld      d, a                    ; the number is two bytes here
                ld      a, (gfx_depth)
                inc     a
                cp      GFX_MAX_DEPTH
                jp      nc, .next               ; too deep, leave it
                ld      (gfx_depth), a
                ; keep our place, draw the other one, then carry on
                ld      hl, (gfx_code)
                push    hl
                ld      hl, (gfx_left)
                push    hl
                ex      de, hl
                call    run_picture
                pop     hl
                ld      (gfx_left), hl
                pop     hl
                ld      (gfx_code), hl
                ld      hl, gfx_depth
                dec     (hl)
                jp      .next

; The next byte of the commands, in A.
; Corrupts: HL
take_byte:
                ld      hl, (gfx_code)
                ld      a, (hl)
                inc     hl
                ld      (gfx_code), hl
                push    hl
                ld      hl, (gfx_left)
                dec     hl
                ld      (gfx_left), hl
                pop     hl
                ret

gfx_section:    dw      0
gfx_index:      dw      0
gfx_count:      dw      0
gfx_wanted:     dw      0
gfx_code:       dw      0
gfx_left:       dw      0
gfx_depth:      db      0
gfx_x0:         db      0
gfx_y0:         db      0
gfx_x1:         db      0
gfx_y1:         db      0
gfx_ink:        db      0
gfx_paper:      db      7
gfx_bright:     db      0
gfx_flash:      db      0
