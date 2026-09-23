; MIT License, Copyright (c) 2025 Cronomantic
;
; Filling an area of a picture off a Spectrum on a PC's CGA, which is the
; Spectrum's fill -- z80/next/fill.asm, which is the same thing for the same
; reason, walk for walk.
;
; The walk is the Spectrum's: up and down the one column the fill was started
; in, laying a horizontal run across each row, stopping the moment the point
; directly above or below is blocked.  What it walks is the mask, which holds
; what a Spectrum's screen would hold.  What is this machine's is the colour:
; a run lays the ink's value where the pattern is lit and the paper's where it
; is not, into a screen of four pixels to a byte.

PICTURE_TOP     equ 175                 ; the y a picture reaches
PICTURE_BOTTOM  equ 48
FILL_INK        equ 0
FILL_PAPER      equ 1
FILL_SHADE      equ 2

; Whether a fill is stopped at (DL across, DH up the commands' way): zero flag
; clear if it is.
; Corrupts: AX, BX, CX
blocked:
                push    dx
                mov     al, dh
                call    to_row
                mov     dh, al
                call    is_boundary
                pop     dx
                ret

; Fill from (DL across, DH up).
; Corrupts: everything but DS
flood_fill:
                mov     [fill_x], dl
                call    blocked
                jnz     .done
                mov     [fill_seed_y], dh
                mov     [fill_y], dh
.upwards:
                mov     al, [fill_y]
                cmp     al, PICTURE_TOP + 1
                jnc     .downwards
                mov     dh, al
                mov     dl, [fill_x]
                call    blocked
                jnz     .downwards
                call    fill_run
                inc     byte [fill_y]
                jmp     .upwards
.downwards:
                mov     al, [fill_seed_y]
                dec     al
                mov     [fill_y], al
.each_below:
                mov     al, [fill_y]
                cmp     al, PICTURE_BOTTOM
                jb      .done
                mov     dh, al
                mov     dl, [fill_x]
                call    blocked
                jnz     .done
                call    fill_run
                dec     byte [fill_y]
                jmp     .each_below
.done:
                ret

; Lay the pattern across the run of clear pixels through (fill_x, fill_y).
; Corrupts: everything but DS
fill_run:
                ; the byte for this row: the low one, turned about on odd rows
                mov     al, [fill_low]
                test    byte [fill_y], 1
                jz      .have_pattern
                xor     al, [fill_high]
.have_pattern:
                mov     [span_pattern], al
                mov     al, [fill_y]
                call    to_row
                mov     [fill_row], al
                mov     dh, al
                mov     dl, [fill_x]
                call    span_extent
                call    colour_span
                jmp     mark_span

; How far the clear run through (DL, DH) reaches, into fill_left and
; fill_right.  Whenever the walk steps into a byte of the mask it has not
; looked at yet it looks at the whole byte first, because eight clear pixels
; are a byte of nought; only the two ends are picked apart a pixel at a time.
; SI walks the mask and CH is the pixel's bit.
; Corrupts: AX, BX, CX, SI
span_extent:
                mov     bl, dh
                xor     bh, bh
                mov     cl, 5
                shl     bx, cl                  ; thirty two bytes a row
                add     bx, mask
                mov     [row_base], bx
                mov     [fill_left], dl
                mov     [fill_right], dl
                mov     al, dl
                call    point_at
.leftwards:
                cmp     byte [fill_left], 0
                je      .left_done
                rol     ch, 1                   ; one pixel to the left
                jnc     .pixel_left
                dec     si                      ; over into the byte before
                cmp     byte [si], 0
                jne     .pixel_left             ; something in it: one at a time
                sub     byte [fill_left], 8     ; all eight of it clear, and
                mov     ch, 80h                 ; we stand at its first
                jmp     .leftwards
.pixel_left:
                test    [si], ch
                jnz     .left_done
                dec     byte [fill_left]
                jmp     .leftwards
.left_done:
                mov     al, dl
                call    point_at
.rightwards:
                mov     al, [fill_right]
                inc     al
                jz      .right_done             ; the edge of the picture
                ror     ch, 1                   ; one pixel to the right
                jnc     .pixel_right
                inc     si
                cmp     byte [si], 0
                jne     .pixel_right
                add     byte [fill_right], 8
                mov     ch, 01h                 ; standing at its last pixel
                jmp     .rightwards
.pixel_right:
                test    [si], ch
                jnz     .right_done
                inc     byte [fill_right]
                jmp     .rightwards
.right_done:
                ret

; Point SI at the byte of the mask holding column AL of the row, with CH its
; bit.
; Corrupts: AX, CL
point_at:
                mov     cl, al
                xor     ah, ah
                shr     al, 1
                shr     al, 1
                shr     al, 1                   ; which byte across
                mov     si, [row_base]
                add     si, ax
                and     cl, 7
                mov     ch, 80h
                shr     ch, cl
                ret

; Put the pattern into the mask over the run, eight pixels at a stroke where
; it can: the pattern's lit points stop later fills, as the Spectrum's do.
; Corrupts: AX, BX, CX, SI
mark_span:
                mov     bl, [fill_left]
                and     bl, 7
                xor     bh, bh
                mov     ah, [mask_from + bx]
                mov     bl, [fill_right]
                and     bl, 7
                mov     al, [mask_to + bx]
                mov     [span_last], al
                mov     cl, [fill_right]
                shr     cl, 1
                shr     cl, 1
                shr     cl, 1
                mov     al, [fill_left]
                shr     al, 1
                shr     al, 1
                shr     al, 1
                sub     cl, al                  ; bytes after the first
                xor     ch, ch
                xor     bh, bh
                mov     bl, al
                mov     si, [row_base]
                add     si, bx
                test    cx, cx
                jnz     .several
                and     ah, [span_last]         ; one byte, both ends in it
                jmp     blend_mask
.several:
                call    blend_mask
                inc     si
                dec     cx
                jz      .last
                mov     al, [span_pattern]
.middle:
                mov     [si], al                ; a whole byte, eight pixels
                inc     si
                loop    .middle
.last:
                mov     ah, [span_last]
                ; fall through

; Put the pattern where AH says, leaving the rest of the mask's byte alone.
; Corrupts: AL, BL
blend_mask:
                mov     al, ah
                not     al
                and     al, [si]
                mov     bl, [span_pattern]
                and     bl, ah
                or      al, bl
                mov     [si], al
                ret

; Give the run the colours in force: the ink's value where the pattern is lit
; and the paper's everywhere else.
;
; The pattern is eight pixels and lines up with the x of the picture, so a byte
; of the screen, which is four pixels, always takes either the pattern's first
; four -- in an even column of bytes -- or its last four, in an odd one.  Both
; are worked out once for the run, and lay_run lays them.
; Corrupts: AX, BX, CX, DX, DI, ES
colour_span:
                mov     al, [span_pattern]
                mov     cl, 4
                shr     al, cl
                call    nibble_byte
                mov     dl, al                  ; an even column of bytes
                mov     al, [span_pattern]
                and     al, 0Fh
                call    nibble_byte
                mov     dh, al                  ; an odd one
                mov     al, [fill_row]
                mov     bl, [fill_left]
                mov     bh, [fill_right]
                jmp     lay_run

; The byte of the screen for four pixels of the pattern, the low four bits of
; AL with the first of them in bit three: the ink's value where one is lit and
; the paper's where it is not.
; Corrupts: AX, BX
nibble_byte:
                and     al, 0Fh
                mov     bl, al
                xor     bh, bh
                mov     al, [lit_pixels + bx]
                mov     ah, al
                and     al, [line_byte]
                not     ah
                and     ah, [fill_byte]
                or      al, ah
                ret

; The two bits of every pixel lit in a nibble, the first pixel in bit three.
lit_pixels:     db      00h, 03h, 0Ch, 0Fh, 30h, 33h, 3Ch, 3Fh
                db      0C0h, 0C3h, 0CCh, 0CFh, 0F0h, 0F3h, 0FCh, 0FFh
; Every bit of a mask byte from this one rightwards, and up to this one.
mask_from:      db      0FFh, 7Fh, 3Fh, 1Fh, 0Fh, 07h, 03h, 01h
mask_to:        db      80h, 0C0h, 0E0h, 0F0h, 0F8h, 0FCh, 0FEh, 0FFh

; Choose what a fill lays down: AL says which of the three.
; Corrupts: AX, BX
set_fill_pattern:
                mov     bl, al
                xor     bh, bh
                shl     bx, 1
                mov     al, [fill_patterns + bx]
                mov     [fill_low], al
                mov     al, [fill_patterns + bx + 1]
                mov     [fill_high], al
                ret

; Solid, wiped, half tone: the three pairs the original holds at $6364.
fill_patterns:  db      0FFh, 00h
                db      00h, 00h
                db      0AAh, 0FFh

fill_x:         db      0
fill_seed_y:    db      0
fill_y:         db      0
fill_row:       db      0
fill_left:      db      0
fill_right:     db      0
fill_low:       db      0
fill_high:      db      0
span_pattern:   db      0
span_last:      db      0
row_base:       dw      0
