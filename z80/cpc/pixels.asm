; MIT License, Copyright (c) 2025 Cronomantic
;
; Where a point of the picture is on an Amstrad's screen, and the little that
; goes with that: the same for both ways this machine draws, the Amstrad's own
; and the Spectrum's.  See draw.asm and spectrum.asm.
;
; Four pens to a pixel and four pixels to a byte, and the two bits of a pixel
; are not next to each other: pixel n takes bit 7-n and bit 3-n.  So a byte
; with one pen all the way across is $00, $F0, $0F or $FF, and masking one of
; those with the pixel's own two bits gives what to write.
;
; The screen is at $C000 in eight blocks of one line in eight, the way the
; Spectrum's thirds are but more so.  The picture is 256 wide on a screen of
; 320, so it sits 32 pixels in, which is a whole byte and saves the trouble.

GAC_TOP         equ 175                 ; y=175 is its first row
; The pens with all four pixels the same, which is what SCR INK ENCODE gives.
pen_bytes:      db      $00, $F0, $0F, $FF
; The two bits belonging to each pixel of a byte.
pixel_masks:    db      %10001000, %01000100, %00100010, %00010001

; Turn a command's y into a screen row, keeping sixteen bits with their sign.
; In A, out HL.
; Corrupts: AF, C
row_of:
                ld      c, a
                ld      a, GAC_TOP
                sub     c
                ld      l, a
                sbc     a, a
                ld      h, a
                ret

; Bring an x that left the picture to its edge.  In HL, out L.
; Corrupts: AF
clamp_x:
                ld      a, h
                or      a
                ret     z
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

; The byte holding pixel (D across, E down) in HL, and which of its four
; pixels it is in A.
; Corrupts: AF, BC
pixel_address:
                ld      a, e
                and     7
                add     a, a
                add     a, a
                add     a, a                    ; the line within its block
                or      SCREEN >> 8
                ld      h, a
                ld      l, 0
                ld      a, e
                rrca
                rrca
                rrca
                and     $1F                     ; which block
                add     a, a                    ; two bytes to an entry
                ld      c, a
                ld      b, 0
                push    hl
                ld      hl, block_starts
                add     hl, bc
                ld      c, (hl)
                inc     hl
                ld      b, (hl)
                pop     hl
                add     hl, bc
                ld      a, d
                rrca
                rrca
                and     $3F                     ; four pixels to a byte
                add     a, PICTURE_LEFT / 4
                ld      c, a
                ld      b, 0
                add     hl, bc
                ld      a, d
                and     3
                ret

; The byte with the pen in A all the way across.
; Corrupts: AF, HL
pen_byte:
                and     3
                ld      hl, pen_bytes
                jr      table_byte

; The two bits belonging to pixel A of a byte.
; Corrupts: AF, HL
pixel_mask:
                and     3
                ld      hl, pixel_masks
                ; fall through

; Entry A of the table at HL.  Every one of these tables is four or eight
; bytes long and the index is small, so the carry is the whole of the care.
; Corrupts: AF, HL
table_byte:
                add     a, l
                ld      l, a
                jr      nc, .no_carry
                inc     h
.no_carry:
                ld      a, (hl)
                ret

; Turn a command's y into a screen row, in A.  Out A.
to_row:
                neg
                add     a, GAC_TOP
                ret
