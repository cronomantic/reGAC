; MIT License, Copyright (c) 2025 Cronomantic
;
; The straight line, which both GACs draw the same way but for one thing: on
; the Amstrad a line from A to B lights the same points as one from B to A,
; because its firmware puts the two ends in order first, and on the Spectrum
; it does not.  A build off an Amstrad is assembled with AMSTRAD_PICTURES and
; orders them; see z80/next/amstrad.asm and z80/next/draw.asm, which this is.
;
; What it draws with is plot_point, at (DL across, DH down in screen rows),
; from draw.asm or amstrad.asm.

; A straight line between the two points in lin_x0 and lin_x1, which are
; sixteen bit and may lie outside the picture.  Each end is brought to the
; edge before anything else, which is what GAC does at $643C, and only then
; are the two deltas worked out in a byte.
; Corrupts: everything but DS
draw_line:
                mov     ax, [lin_x0]
                call    clamp_x
                mov     [gfx_x0], al
                mov     ax, [lin_y0]
                call    clamp_row
                mov     [gfx_y0], al
                mov     ax, [lin_x1]
                call    clamp_x
                mov     [gfx_x1], al
                mov     ax, [lin_y1]
                call    clamp_row
                mov     [gfx_y1], al
%ifdef AMSTRAD_PICTURES
                call    order_ends
%endif
                ; fall through

; The line between two points known to be inside, in screen rows, drawn the
; way the Spectrum ROM draws one, because that is what GAC called: the error
; starts at half the longer side, counts up by the shorter one, and when it
; reaches the longer side it comes off again and that step goes diagonal.
; Corrupts: everything but DS
line_between:
                mov     dl, [gfx_x0]
                mov     dh, [gfx_y0]
                mov     al, [gfx_x1]
                sub     al, dl
                mov     ah, 1
                jnc     .have_dx
                neg     al
                mov     ah, -1
.have_dx:
                mov     [line_dx], al
                mov     [line_sx], ah
                mov     al, [gfx_y1]
                sub     al, dh
                mov     ah, 1
                jnc     .have_dy
                neg     al
                mov     ah, -1
.have_dy:
                mov     [line_dy], al
                mov     [line_sy], ah
                mov     al, [line_dy]
                cmp     al, [line_dx]
                jbe     .across
                jmp     .down
.across:
                call    plot_point
                mov     al, [line_dx]
                shr     al, 1
                mov     [line_err], al
                mov     al, [line_dx]
                test    al, al
                jz      .done
                xor     ah, ah
                mov     si, ax                  ; the steps to take
.across_step:
                mov     al, [line_err]
                add     al, [line_dy]
                cmp     al, [line_dx]
                jb      .across_straight
                sub     al, [line_dx]
                add     dh, [line_sy]           ; the step goes diagonal
.across_straight:
                mov     [line_err], al
                add     dl, [line_sx]
                call    plot_point
                dec     si
                jnz     .across_step
.done:
                ret
.down:
                call    plot_point
                mov     al, [line_dy]
                shr     al, 1
                mov     [line_err], al
                mov     al, [line_dy]
                test    al, al
                jz      .done
                xor     ah, ah
                mov     si, ax
.down_step:
                mov     al, [line_err]
                add     al, [line_dx]
                cmp     al, [line_dy]
                jb      .down_straight
                sub     al, [line_dy]
                add     dl, [line_sx]
.down_straight:
                mov     [line_err], al
                add     dh, [line_sy]
                call    plot_point
                dec     si
                jnz     .down_step
                ret

%ifdef AMSTRAD_PICTURES
; Put the two ends in order along the longer side, as the Amstrad's firmware
; does: by x when the line is at least as wide as it is tall, with the smaller
; x first; otherwise with the larger row first, which is the smaller y of the
; commands.
; Corrupts: AX, BX
order_ends:
                mov     al, [gfx_x0]
                sub     al, [gfx_x1]
                jnc     .have_dx
                neg     al
.have_dx:
                mov     bl, al                  ; how far across
                mov     al, [gfx_y0]
                sub     al, [gfx_y1]
                jnc     .have_dy
                neg     al
.have_dy:
                cmp     al, bl
                jbe     .by_x
                mov     al, [gfx_y1]
                cmp     al, [gfx_y0]
                jbe     .in_order
                jmp     .swap
.by_x:
                mov     al, [gfx_x1]
                cmp     al, [gfx_x0]
                jnc     .in_order
.swap:
                mov     ax, [gfx_x0]            ; x0 and y0, side by side
                xchg    ax, [gfx_x1]            ; for x1 and y1
                mov     [gfx_x0], ax
.in_order:
                ret
%endif

section .data
lin_x0:         dw      0                       ; a line's two ends, before
lin_y0:         dw      0                       ; they are brought inside
lin_x1:         dw      0
lin_y1:         dw      0

line_dx:        db      0
line_dy:        db      0
line_sx:        db      0
line_sy:        db      0
line_err:       db      0
section .text
