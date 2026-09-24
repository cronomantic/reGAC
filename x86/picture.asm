; MIT License, Copyright (c) 2025 Cronomantic
;
; The picture interpreter: it walks the drawing commands of a picture and asks
; the machine underneath to put them on the screen.  It is z80/common/
; picture.asm, command for command, and what it asks for is the same: gfx_line,
; gfx_rect, gfx_ellipse, gfx_plot, gfx_fill, set_fill_pattern, set_border,
; settle_colours and gfx_start_colours, from cga.asm and shapes.asm and from
; the rules the build carries: draw.asm and fill.asm for an adventure off a
; Spectrum, amstrad.asm and amstrad_fill.asm for one off an Amstrad.
;
; The commands are read out of the pictures' segment through ES, and the
; primitives are free to take ES for the screen: the walk loads it again for
; every command it reads.

GFX_MAX_DEPTH   equ 8                   ; a picture may call others

CMD_BORDER      equ 01h
CMD_PLOT        equ 02h
CMD_ELLIPSE     equ 03h
CMD_FILL        equ 04h
CMD_BGFILL      equ 05h
CMD_SHADE       equ 06h
CMD_CALL        equ 07h
CMD_RECT        equ 08h
CMD_LINE        equ 09h
CMD_INK         equ 10h
CMD_PAPER       equ 11h
CMD_BRIGHT      equ 12h
CMD_FLASH       equ 13h
CMD_PENS        equ 14h

; Where the pictures are.
; Corrupts: AX, BX, CX, SI, ES
picture_init:
                mov     al, SECTION_GRAPHICS
                call    db_section
                mov     [gfx_seg], es
                mov     [gfx_section], si
                mov     ax, [es:si]
                mov     [gfx_count], ax
                add     si, 2
                mov     [gfx_index], si
                xor     ax, ax                  ; nothing known yet, and no
                mov     [gfx_known], ax         ; picture is numbered nought
                mov     [gfx_behind], ax
                ret

; Find picture AX.  Its commands come back at ES:SI with their length in CX;
; carry set when there is no such picture.  The last two found are kept,
; because a picture that calls another calls it over and over: see
; z80/common/picture.asm, where that was counted.
; Corrupts: BX
picture_find:
                mov     es, [gfx_seg]
                cmp     ax, [gfx_known]
                jne     .behind
                mov     si, [gfx_known_at]
                mov     cx, [gfx_known_size]
                clc
                ret
.behind:
                cmp     ax, [gfx_behind]
                jne     .look
                mov     si, [gfx_behind_at]
                mov     cx, [gfx_behind_size]
                clc
                ret
.look:
                ; Neither of the two knew it, so the one in front steps back
                ; and the search puts the new one in its place.
                mov     bx, [gfx_known]
                mov     [gfx_behind], bx
                mov     bx, [gfx_known_at]
                mov     [gfx_behind_at], bx
                mov     bx, [gfx_known_size]
                mov     [gfx_behind_size], bx
                mov     si, [gfx_index]
                mov     cx, [gfx_count]
.each:
                jcxz    .none
                cmp     ax, [es:si]
                je      .found
                add     si, 4
                dec     cx
                jmp     .each
.none:
                stc
                ret
.found:
                mov     si, [es:si + 2]
                add     si, [gfx_section]       ; the block for this picture
                mov     cx, [es:si]
                add     si, 2                   ; CX = how many bytes of commands
                mov     [gfx_known_at], si
                mov     [gfx_known_size], cx
                mov     [gfx_known], ax
                clc
                ret

; Draw picture AX.
; Corrupts: everything but DS
draw_picture:
                push    ax
                call    text_window_below       ; a picture takes its rows back
                mov     byte [gfx_depth], 0
                mov     byte [gfx_border_now], 0FFh     ; no colour yet
                call    gfx_clear
                pop     ax
                push    ax
                call    picture_colours_set     ; its palette and its pens
                call    text_recolour           ; which the text is in as well
                call    gfx_start_colours       ; what a picture starts in
                pop     ax
                call    run_picture
                jmp     gfx_show                ; and let the machine show it

; Draw picture AX without clearing first, which is what CALL needs.
; Corrupts: everything but DS
run_picture:
                call    picture_find
                jc      .done
                mov     dx, cx                  ; DX counts the bytes left
.next:
                test    dx, dx
                jz      .done
                dec     dx
                mov     es, [gfx_seg]
                mov     al, [es:si]
                inc     si
                mov     cl, al
                cmp     al, CMD_BORDER
                je      .a_border
                cmp     al, CMD_INK
                je      .one_byte
                cmp     al, CMD_PAPER
                je      .one_byte
                cmp     al, CMD_BRIGHT
                je      .one_byte
                cmp     al, CMD_FLASH
                je      .one_byte
                cmp     al, CMD_PENS
                je      .two_pens
                cmp     al, CMD_CALL
                je      .call_picture
                cmp     al, CMD_PLOT
                je      .two_bytes
                cmp     al, CMD_FILL
                je      .two_bytes
                cmp     al, CMD_BGFILL
                je      .two_bytes
                cmp     al, CMD_SHADE
                je      .two_bytes
                ; the rest take four
                mov     al, [es:si]
                mov     [gfx_x0], al
                mov     al, [es:si + 1]
                mov     [gfx_y0], al
                mov     al, [es:si + 2]
                mov     [gfx_x1], al
                mov     al, [es:si + 3]
                mov     [gfx_y1], al
                add     si, 4
                sub     dx, 4
                call    .keep_place
                cmp     cl, CMD_LINE
                jne     .not_line
                call    gfx_line
                jmp     .resume
.not_line:
                cmp     cl, CMD_RECT
                jne     .not_rect
                call    gfx_rect
                jmp     .resume
.not_rect:
                call    gfx_ellipse
.resume:
                mov     si, [gfx_code]
                mov     dx, [gfx_left]
                jmp     .next
.done:
                ret

; Drawing treads on every register, so the place in the commands goes to
; memory for as long as that takes.
.keep_place:
                mov     [gfx_code], si
                mov     [gfx_left], dx
                ret

; The border, which is not written again when it is the one already asked
; for: see z80/common/picture.asm, where one picture asks for it forty three
; thousand times.
.a_border:
                mov     al, [es:si]
                inc     si
                dec     dx
                cmp     al, [gfx_border_now]
                je      .next
                mov     [gfx_border_now], al
                call    set_border              ; keeps everything but AX
                jmp     .next

; INK, PAPER, BRIGHT and FLASH, which are kept and settled at once.
.one_byte:
                mov     al, [es:si]
                inc     si
                dec     dx
                mov     bx, gfx_ink
                cmp     cl, CMD_INK
                je      .store
                mov     bx, gfx_paper
                cmp     cl, CMD_PAPER
                je      .store
                mov     bx, gfx_bright
                cmp     cl, CMD_BRIGHT
                je      .store
                mov     bx, gfx_flash
.store:
                mov     [bx], al
                push    si
                push    dx
                call    settle_colours
                pop     dx
                pop     si
                jmp     .next
.two_pens:
                mov     al, [es:si]
                mov     [gfx_pen1], al
                mov     al, [es:si + 1]
                mov     [gfx_pen2], al
                add     si, 2
                sub     dx, 2
                jmp     .next
.two_bytes:
                mov     al, [es:si]
                mov     [gfx_x0], al
                mov     al, [es:si + 1]
                mov     [gfx_y0], al
                add     si, 2
                sub     dx, 2
                call    .keep_place
                cmp     cl, CMD_PLOT
                jne     .a_fill
                ; A point outside the picture is not drawn at all, and the
                ; picture carries on: measured on the original, whose ROM
                ; refuses to plot out of range.
                mov     al, [gfx_y0]
                sub     al, PICTURE_BOTTOM
                cmp     al, PICTURE_TOP - PICTURE_BOTTOM + 1
                jnc     .resume
                call    gfx_plot
                jmp     .resume
.a_fill:
                mov     al, FILL_INK
                cmp     cl, CMD_FILL
                je      .fill_kind
                mov     al, FILL_PAPER
                cmp     cl, CMD_BGFILL
                je      .fill_kind
                mov     al, FILL_SHADE
.fill_kind:
                call    set_fill_pattern
                call    gfx_fill
                jmp     .resume
.call_picture:
                mov     bx, [es:si]             ; the number is two bytes here
                add     si, 2
                sub     dx, 2
                mov     al, [gfx_depth]
                inc     al
                cmp     al, GFX_MAX_DEPTH
                jnc     .next                   ; too deep, leave it
                mov     [gfx_depth], al
                push    si                      ; keep our place, draw the
                push    dx                      ; other one, then carry on
                mov     ax, bx
                call    run_picture
                pop     dx
                pop     si
                dec     byte [gfx_depth]
                jmp     .next

section .data
gfx_seg:        dw      0
gfx_section:    dw      0
gfx_index:      dw      0
gfx_count:      dw      0
gfx_behind:     dw      0
gfx_behind_at:  dw      0
gfx_behind_size: dw     0
gfx_known:      dw      0
gfx_known_at:   dw      0
gfx_known_size: dw      0
gfx_code:       dw      0
gfx_left:       dw      0
gfx_depth:      db      0
gfx_border_now: db      0FFh
gfx_x0:         db      0
gfx_y0:         db      0
gfx_x1:         db      0
gfx_y1:         db      0
gfx_ink:        db      0
gfx_paper:      db      7
gfx_pen1:       db      1
gfx_pen2:       db      1
gfx_bright:     db      0
gfx_flash:      db      0
section .text
