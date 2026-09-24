; MIT License, Copyright (c) 2025 Cronomantic
;
; Drawing a picture off an Amstrad on a PC's CGA, with the Amstrad's rules.
;
; An adventure is drawn with the rules of the GAC it was written with, on any
; machine that has room for them, and the CGA needs nothing it has not got:
; like the Amstrad's own screen it holds two bits a pixel, so the pen of every
; point is on the screen to be read back, and a fill that stops where the pen
; changes has the pens to look at.  No mask, then -- a build carries this and
; amstrad_fill.asm instead of draw.asm and fill.asm, never both.  It is
; z80/next/amstrad.asm, and what is the Amstrad's was read off that machine:
; see z80/cpc/draw.asm.
;
; The one thing that is the CGA's is that a pen is not written as itself.
; The values nought to three show the background and the trio as they come,
; and the four pens of a picture are dealt out among them in whatever order
; brings the colours closest (see cga_amstrad_colours in regac/devices.py):
; colour_value holds, for each pen, the value it is written as.  A fill only
; asks whether a point is still the seed's pen, and that is the same question
; asked of the values, since no two pens share one.

section .data
; The value an outline is written in: its pen's.
ink_value:      db      0
section .text

; The colours a picture starts in.  Pen one, and nothing in the picture data
; says so: the frame every room of the Amstrad adventures draws carries no
; colour order at all and comes out in pen one on the machine.  The picture
; has been wiped to value nought, and is laid in pen nought's value if that is
; another.
; Corrupts: AX, BX, CX, DI, ES
gfx_start_colours:
                mov     al, 1
                mov     [gfx_ink], al
                mov     [gfx_pen1], al
                mov     [gfx_pen2], al
                xor     al, al
                mov     [gfx_paper], al
                mov     [gfx_bright], al
                mov     [gfx_flash], al
                call    settle_colours
                mov     al, [colour_value]
                test    al, al
                jz      .done
                call    value_byte
                call    paint_picture
.done:
                ret

; The colours in force have changed.  An ink of eight or more is the format's
; way of saying leave the colour alone, so only a real one settles anything,
; and what it settles is its low two bits, the pen.
; Corrupts: AX, BX
settle_colours:
                mov     al, [gfx_ink]
                cmp     al, 8
                jnc     .stands
                and     al, 3
                mov     bl, al
                xor     bh, bh
                mov     al, [colour_value + bx]
                mov     [ink_value], al
.stands:
                ret

; Put down a pixel of the outline at (DL, DH).  A picture may reach past the
; top or the bottom, and those pixels are simply not put down.
; Corrupts: AX, BX, CX, DI, ES
plot_point:
                cmp     dh, PICTURE_ROWS
                jnc     .off
                call    cga_address
                mov     ax, CGA_SEGMENT
                mov     es, ax
                mov     ah, 3
                shl     ah, cl
                not     ah
                mov     al, [ink_value]
                shl     al, cl
                and     ah, [es:di]
                or      al, ah
                mov     [es:di], al
.off:
                ret

; Which value is at (DL, DH), in AL.  Off the picture comes back as 255,
; which is no pen at all and stops a fill.
; Corrupts: AX, BX, CX, DI, ES
pen_at:
                cmp     dh, PICTURE_ROWS
                jnc     .outside
                call    cga_address
                mov     ax, CGA_SEGMENT
                mov     es, ax
                mov     al, [es:di]
                shr     al, cl
                and     al, 3
                ret
.outside:
                mov     al, 255
                ret

; Wipe the picture's rows to value nought: see wipe_picture_rows.
; Corrupts: AX, BX, CX, DI, ES
gfx_clear:
                jmp     wipe_picture_rows
