; MIT License, Copyright (c) 2025 Cronomantic
;
; Where a point of the picture is on a Spectrum Next, and the little that goes
; with that: the same for both ways this machine draws, the Spectrum's -- in
; draw.asm and fill.asm -- and the Amstrad's, in amstrad.asm and
; amstrad_fill.asm.  A build carries one or the other.

GAC_TOP         equ 175                 ; y=175 is the first row of the screen

; Turn the adventure's y into a screen row.  In A, out A.
to_row:
                neg
                add     a, GAC_TOP
                ret

; Turn a command's y into a screen row, keeping sixteen bits with their sign.
; A picture may name a y above the top or below the bottom, and those have to
; stay outside rather than come round in a byte.  In A, out HL.
; Corrupts: AF, C
row_of:
                ld      c, a
                ld      a, GAC_TOP
                sub     c
                ld      l, a
                sbc     a, a                    ; all ones when it went below
                ld      h, a
                ret

; Bring an x that left the picture to its edge.  In HL, out L.
; Corrupts: AF
clamp_x:
                ld      a, h
                or      a
                ret     z                       ; nought to 255 already
                ld      l, 0
                bit     7, h
                ret     nz
                ld      l, 255
                ret

; The same for a row.  In HL, out L.
; Corrupts: AF
clamp_row:
                ld      a, h
                or      a
                jr      nz, .outside
                ld      a, l
                cp      PICTURE_ROWS
                ret     c
                ld      l, PICTURE_ROWS - 1
                ret
.outside:
                ld      l, 0
                bit     7, h
                ret     nz
                ld      l, PICTURE_ROWS - 1
                ret

; Where pixel (D across, E down) is in layer 2, with its half of the picture
; mapped.  Inside a piece the row is the high byte and the column the low one.
; Corrupts: AF, HL
colour_address:
                ld      a, e
                rlca
                rlca                            ; bit six of the row: which half
                and     1
                call    map_piece
                ld      a, e
                and     PIECE_LINES - 1
                add     a, WINDOW >> 8
                ld      h, a
                ld      l, d
                ret
