; MIT License, Copyright (c) 2025 Cronomantic
;
; Drawing a picture off a Spectrum on a PC's CGA, with the Spectrum's rules.
;
; It is what the Next and the Amstrad do with such a picture -- z80/next/
; draw.asm and z80/cpc/spectrum.asm -- and for the same reasons.  A set pixel
; on a Spectrum is both a mark and a wall, and with colour a pixel there is
; nothing to read back; so a mask of one bit a pixel is kept beside the
; picture, laid out as a Spectrum's screen would be, and that is what a fill
; walks.  What is this machine's is where a pixel goes and what it is written
; as: two bits of the CGA's screen at B800, in the value its colour comes to
; in the four this picture was given.  See doc/pendiente.md.
;
; A build carries this and fill.asm, or for an adventure off an Amstrad
; amstrad.asm and amstrad_fill.asm instead, never both.  What the two
; share is in cga.asm, line.asm and shapes.asm.
;
; Throughout, a point is DL across and DH down in screen rows of the picture.

MASK_BYTES      equ PICTURE_ROWS * 32
START_PAPER     equ 7                   ; the screen starts white, as it does

; -- colours ------------------------------------------------------------------

; The colours a picture starts in: black on white, as the screen starts, and
; the picture laid down in white's value.
; Corrupts: AX, BX, CX, DI, ES
gfx_start_colours:
                xor     al, al
                mov     [gfx_ink], al
                mov     [gfx_bright], al
                mov     [gfx_flash], al
                mov     [ink_now], al
                mov     [bright_now], al
                mov     al, START_PAPER
                mov     [gfx_paper], al
                mov     [paper_now], al
                call    settle_colours
                mov     al, [fill_byte]
                test    al, al
                jz      .done
                call    paint_picture
.done:
                ret

; Settle the two colours in force into the two values a pixel is written in.
; The ink and the paper are kept as they came, because a colour of eight means
; leave the one in force alone and has to be told apart from a real colour
; later; an ink of nine means whichever of black and white reads against the
; paper; and bright is a colour of its own, the sixteen being the eight and
; the eight bright.
; Corrupts: AX, BX
settle_colours:
                mov     al, [gfx_bright]
                cmp     al, 8
                jnc     .bright_stands
                mov     [bright_now], al
.bright_stands:
                mov     al, [gfx_paper]
                cmp     al, 8
                jnc     .paper_stands
                mov     [paper_now], al
.paper_stands:
                mov     al, [gfx_ink]
                cmp     al, 8
                jb      .ink_given
                cmp     al, 9
                jne     .ink_stands
                mov     al, 0                   ; black on a light paper
                cmp     byte [paper_now], 4
                jnc     .ink_given
                mov     al, 7                   ; white on a dark one
.ink_given:
                mov     [ink_now], al
.ink_stands:
                xor     bh, bh
                mov     bl, 0
                cmp     byte [bright_now], 0
                je      .no_lift
                mov     bl, 8
.no_lift:
                push    bx
                add     bl, [ink_now]
                mov     al, [colour_value + bx]
                mov     [line_value], al
                call    value_byte
                mov     [line_byte], al
                pop     bx
                add     bl, [paper_now]
                mov     al, [colour_value + bx]
                mov     [fill_value], al
                call    value_byte
                mov     [fill_byte], al
                ret

section .data
ink_now:        db      0
paper_now:      db      START_PAPER
bright_now:     db      0
line_value:     db      0
fill_value:     db      0
line_byte:      db      0
fill_byte:      db      0
section .text

; -- the mask and the screen --------------------------------------------------

; The byte of the mask holding pixel (DL, DH) in BX, its bit as a mask in AH.
; Corrupts: AX, CX
mask_address:
                mov     bl, dh
                xor     bh, bh
                mov     cl, 5
                shl     bx, cl                  ; thirty two bytes a row
                mov     al, dl
                shr     al, 1
                shr     al, 1
                shr     al, 1
                xor     ah, ah
                add     bx, ax
                add     bx, mask
                mov     cl, dl
                and     cl, 7
                mov     ah, 80h
                shr     ah, cl
                ret

; Put down a pixel of the outline at (DL, DH), which also stops fills: its bit
; into the mask and its value into the picture.
; Corrupts: AX, BX, CX, DI, ES
plot_point:
                cmp     dh, PICTURE_ROWS
                jnc     .off
                call    mask_address
                or      [bx], ah
                call    cga_address
                mov     ax, CGA_SEGMENT
                mov     es, ax
                mov     ah, 3
                shl     ah, cl
                not     ah
                mov     al, [line_value]
                shl     al, cl
                and     ah, [es:di]
                or      al, ah
                mov     [es:di], al
.off:
                ret

; Whether a fill has to stop at (DL, DH): zero flag clear if it does.  Off
; the picture always stops it.
; Corrupts: AX, BX, CX
is_boundary:
                cmp     dh, PICTURE_ROWS
                jnc     .stops
                call    mask_address
                test    [bx], ah
                ret
.stops:
                or      dh, dh                  ; never nought here: clears Z
                ret

; Wipe the picture and the mask with it: the mask to nothing, because a wiped
; picture stops no fill, and the picture to value nought.  A picture about to
; be drawn is then laid white by gfx_start_colours, once its colours are in.
; Corrupts: AX, BX, CX, DI, ES
gfx_clear:
                push    ds
                pop     es
                mov     di, mask
                mov     cx, MASK_BYTES / 2
                xor     ax, ax
                rep     stosw
                xor     al, al
                jmp     paint_picture

section .data
; The mask: a bit a pixel, thirty two bytes a row, as a Spectrum's screen
; would be for these rows.
mask:           times MASK_BYTES db 0
section .text
