; MIT License, Copyright (c) 2025 Cronomantic
;
; The screen of a PC's CGA in its 320 by 200 mode in four colours, as a
; picture uses it, whichever GAC's rules the picture is drawn with: where each
; row starts, where a pixel is, and the four colours each picture was given.
;
; A picture is 256 pixels by 128 rows at the top of the screen, eight bytes
; in, which puts it in the middle of the 320.  Four pixels to a byte, the first
; in the top two bits; eighty bytes to a row; the even rows in the first eight
; kilobytes of the card and the odd ones in the second.  A pixel is written as
; a value, nought to three, and which colour each value shows is what the
; picture carries in front of its orders: see picture_colours_set.
;
; Throughout, a point is DL across and DH down in screen rows of the picture.

GAC_TOP         equ 175                 ; y=175 is the picture's first row
PICTURE_ROWS    equ 128

CGA_SEGMENT     equ 0B800h
CGA_BANK        equ 2000h               ; the odd rows are in the second eight K
CGA_ACROSS      equ 80                  ; bytes to a row
CGA_MARGIN      equ 8                   ; the picture is 256 of the 320, centred
CGA_STATUS      equ 3DAh
CGA_FLYBACK     equ 08h                 ; the beam is going back up
FLASH_FRAMES    equ 10

; Where each row of the picture starts in the card's memory, worked out once.
; Corrupts: AX, BX, CX, DX
cga_rows_init:
                xor     bx, bx
                xor     cx, cx                  ; the row
.each:
                mov     ax, cx
                shr     ax, 1                   ; which pair of rows
                push    cx
                mov     cl, 4
                shl     ax, cl                  ; times sixteen
                mov     dx, ax
                shl     ax, 1
                shl     ax, 1                   ; times sixty four
                add     ax, dx                  ; eighty
                pop     cx
                test    cl, 1
                jz      .even
                add     ax, CGA_BANK
.even:
                add     ax, CGA_MARGIN
                mov     [cga_rows + bx], ax
                add     bx, 2
                inc     cx
                cmp     cx, PICTURE_ROWS
                jne     .each
                ret

; Turn the adventure's y into a screen row.  In AL, out AL.
to_row:
                neg     al
                add     al, GAC_TOP
                ret

; Turn a command's y into a screen row, keeping sixteen bits with their sign,
; so that a y above the top stays above it.  In AL, out AX.
row_of:
                xor     ah, ah
                neg     ax
                add     ax, GAC_TOP
                ret

; Bring an x that left the picture to its edge.  In AX, out AL.
clamp_x:
                test    ah, ah
                jz      .inside
                mov     al, 0
                test    ah, 80h
                jnz     .inside
                mov     al, 255
.inside:
                ret

; The same for a row.  In AX, out AL.
clamp_row:
                test    ah, ah
                jnz     .outside
                cmp     al, PICTURE_ROWS
                jb      .inside
                mov     al, PICTURE_ROWS - 1
.inside:
                ret
.outside:
                mov     al, 0
                test    ah, 80h
                jnz     .inside
                mov     al, PICTURE_ROWS - 1
                ret

; Where pixel (DL, DH) is in the card's memory, in DI, and how far its two bits
; are from the bottom of the byte, in CL.
; Corrupts: AX, BX
cga_address:
                mov     bl, dh
                xor     bh, bh
                shl     bx, 1
                mov     di, [cga_rows + bx]
                mov     al, dl
                shr     al, 1
                shr     al, 1
                xor     ah, ah
                add     di, ax
                mov     cl, dl
                and     cl, 3
                shl     cl, 1
                neg     cl
                add     cl, 6                   ; the first pixel is the top two
                ret

; Lay the byte in AL over the whole of the picture.
; Corrupts: AX, BX, CX, DI, ES
paint_picture:
                mov     ah, al
                mov     bx, CGA_SEGMENT
                mov     es, bx
                xor     bx, bx
.each_row:
                mov     di, [cga_rows + bx]
                mov     cx, 64 / 2
                rep     stosw
                add     bx, 2
                cmp     bx, PICTURE_ROWS * 2
                jne     .each_row
                ret

; Wipe the rows the picture lives in to value nought, the whole width of the
; screen and not only the picture's 256 points: the text may have had those
; rows -- TEXT gives it the whole screen, and so does a room with no picture
; -- and what it left either side of the picture stayed beside the next one.
; Value nought is the paper and the border, so the rows come out as a picture
; with nothing round it.  The Amstrad does the same; see doc/pendiente.md.
; Corrupts: AX, BX, CX, DI, ES
wipe_picture_rows:
                mov     ax, CGA_SEGMENT
                mov     es, ax
                xor     bx, bx
.each_row:
                mov     di, [cga_rows + bx]
                sub     di, CGA_MARGIN          ; back to the edge of the screen
                mov     cx, CGA_ACROSS / 2
                xor     ax, ax
                rep     stosw
                add     bx, 2
                cmp     bx, PICTURE_ROWS * 2
                jne     .each_row
                ret

; Lay a run of a fill across row AL, from pixel BL to pixel BH, with DL the
; byte for an even column of bytes and DH for an odd one: a fill's pattern
; comes round every eight pixels, which is two bytes.  Only the two ends are
; merged into what is there; every byte between is written whole.
; Corrupts: AX, BX, CX, DX, DI, ES
lay_run:
                push    bx
                mov     bl, al
                xor     bh, bh
                shl     bx, 1
                mov     di, [cga_rows + bx]
                pop     bx
                ; the pixels of the first byte from the run's start, and of
                ; the last up to its end
                mov     al, bl
                and     al, 3
                mov     [lay_first], al
                mov     al, bh
                and     al, 3
                mov     [lay_last], al
                ; where the run starts, and how many bytes follow
                mov     al, bl
                shr     al, 1
                shr     al, 1
                xor     ah, ah
                add     di, ax
                mov     cl, bh
                shr     cl, 1
                shr     cl, 1
                sub     cl, al
                xor     ch, ch
                test    al, 1                   ; an odd column starts on the
                jz      .lined_up               ; pattern's second half
                xchg    dl, dh
.lined_up:
                mov     ax, CGA_SEGMENT
                mov     es, ax
                mov     bl, [lay_first]
                xor     bh, bh
                mov     ah, [from_pixel + bx]
                mov     bl, [lay_last]
                mov     bl, [upto_pixel + bx]
                mov     [lay_last], bl
                jcxz    .one_byte
                call    blend_screen
                inc     di
                xchg    dl, dh                  ; the other half of the pattern
                dec     cx
                jz      .last
.middle:
                mov     [es:di], dl             ; a whole byte, four pixels
                inc     di
                xchg    dl, dh
                loop    .middle
.last:
                mov     ah, [lay_last]
                jmp     blend_screen
.one_byte:
                and     ah, [lay_last]          ; both ends in the one byte
                ; fall through

; Put DL where AH says, leaving the rest of the screen's byte at ES:DI alone.
; Corrupts: AL, BL
blend_screen:
                mov     bl, dl
                and     bl, ah
                mov     al, ah
                not     al
                and     al, [es:di]
                or      al, bl
                mov     [es:di], al
                ret

section .data
; The pixels of a screen byte from pixel n on, and up to pixel n.
from_pixel:     db      0FFh, 3Fh, 0Fh, 03h
upto_pixel:     db      0C0h, 0F0h, 0FCh, 0FFh
lay_first:      db      0
lay_last:       db      0
section .text

; The byte with value AL in all four of its pixels.
; Corrupts: AH
value_byte:
                mov     ah, 55h
                mul     ah
                ret

; -- colours ------------------------------------------------------------------

section .data
; The pixel value each of the sixteen colours of the original comes to, for
; the picture on the screen, out of the four bytes the picture carries.  A
; picture off an Amstrad carries its four pens' values there four times over,
; so that an ink is looked up here as it is, and its low two bits pick the
; pen.
;
; Until a picture brings its own they are what the reference takes for a
; screen with no picture on it: cyan, magenta and white on black, the brighter
; of the CGA's second trio -- the colours of the original to the nearest of
; those, or the four pens as themselves.  tests/test_cga.py holds these to
; the reference.
                %ifdef AMSTRAD_PICTURES
colour_value:   db      0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3
                %else
colour_value:   db      0, 0, 0, 2, 0, 1, 3, 3, 0, 0, 0, 2, 1, 1, 3, 3
                %endif
START_SELECT    equ 30h                 ; that trio on black, port 3D9h
START_MODE      equ 0Ah                 ; and the mode, port 3D8h
shown_select:   db      START_SELECT    ; the palette on the screen
shown_mode:     db      START_MODE
other_select:   db      START_SELECT    ; and the one a flashing pen changes to
other_mode:     db      START_MODE
flashing:       db      0
flash_frames:   db      FLASH_FRAMES
section .text

; Put up the palette a screen starts in, before any picture.
; Corrupts: AX, DX
palette_start:
                jmp     palette_out

; Put up the palette of picture AX and the values its colours come to: the two
; port bytes and four bytes of values it carries in front of its length.
; Corrupts: AX, BX, CX, DX, SI, ES
picture_colours_set:
                cmp     byte [picture_head], 0
                je      .none
                call    picture_find
                jc      .none
                mov     al, [picture_head]
                xor     ah, ah
                add     ax, 2                   ; in front of the length
                sub     si, ax
                mov     al, [es:si]             ; the colour select, port 3D9h
                mov     [shown_select], al
                mov     al, [es:si + 1]         ; and the mode, port 3D8h
                mov     [shown_mode], al
                call    palette_out
                add     si, 2
                mov     bx, colour_value
                mov     cx, 4
.each_byte:
                mov     al, [es:si]
                inc     si
                push    cx
                mov     cx, 4
.each_colour:
                mov     ah, al
                and     ah, 3
                mov     [bx], ah
                inc     bx
                shr     al, 1
                shr     al, 1
                loop    .each_colour
                pop     cx
                loop    .each_byte
                ; and the palette it flashes to, which is the same one when
                ; nothing flashes
                mov     al, [es:si]
                mov     [other_select], al
                mov     al, [es:si + 1]
                mov     [other_mode], al
                mov     byte [flash_frames], FLASH_FRAMES
                cmp     al, [shown_mode]
                jne     .flashes
                mov     al, [other_select]
                cmp     al, [shown_select]
.flashes:
                mov     al, 0
                je      .still
                inc     al
.still:
                mov     [flashing], al
.none:
                ret

; Put up the palette in shown_select and shown_mode.
; Corrupts: AX, DX
palette_out:
                mov     dx, 3D8h
                mov     al, [shown_mode]
                out     dx, al
                inc     dx
                mov     al, [shown_select]
                out     dx, al
                %ifdef TRANSCRIPT
                jmp     transcript_palette      ; the ports cannot be read back
                %endif
                ret

; A frame has gone by while the game waits for a key: every ten of them a
; picture whose pens flash changes to its other palette, and back.  The
; Amstrad's firmware changes a flashing ink every ten frames, and the original
; never asks for anything else; and there, as here, it only happens while a
; key is waited for.  It is done as the frame flyback starts, as the firmware
; does it, or the top of one frame would come out in one palette and the
; bottom in the other.  Nothing happens unless a pen flashes, which only one
; off an Amstrad can: see cga_amstrad_flash in regac/devices.py.
; Corrupts: AX
flash_frame:
                cmp     byte [flashing], 0
                je      .done
                dec     byte [flash_frames]
                jnz     .done
                mov     byte [flash_frames], FLASH_FRAMES
                push    dx
                mov     dx, CGA_STATUS
.in_flyback:
                in      al, dx
                test    al, CGA_FLYBACK
                jnz     .in_flyback
.not_yet:
                in      al, dx
                test    al, CGA_FLYBACK
                jz      .not_yet
                mov     al, [shown_select]
                xchg    al, [other_select]
                mov     [shown_select], al
                mov     al, [shown_mode]
                xchg    al, [other_mode]
                mov     [shown_mode], al
                call    palette_out
                pop     dx
.done:
                ret

; What the machine does once a picture is drawn, which here is nothing: it is
; drawn where it is seen.
gfx_show:
                ret

; The border.  In the CGA's 320 by 200 mode the border is the background, one
; register for the two, so it cannot be a colour of its own without changing
; every point of the picture in the background's value.  So a picture's BORDER
; changes nothing here: see doc/pendiente.md.
set_border:
                ret

section .data
cga_rows:       times PICTURE_ROWS dw 0         ; see cga_rows_init
section .text
