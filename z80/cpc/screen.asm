; MIT License, Copyright (c) 2025 Cronomantic
;
; The Amstrad's screen, without asking the firmware for anything.
;
; The gate array takes everything through port $7Fxx: a byte with the top two
; bits 01 chooses which pen is being set and 010 what colour to give it, and
; 100 sets the mode.  The colours are the hardware's own numbering, which is
; not the firmware's, so what a picture names has to be looked up.

GATE_ARRAY      equ $7F00
MODE_1          equ %10001100           ; mode 1, both ROMs out of the way

; The twenty seven colours the hardware knows, in the order the firmware
; numbers them, which is the order an adventure names them in.
firmware_inks:  db      $54, $44, $55, $5C, $58, $5D, $4C, $45
                db      $4D, $56, $46, $57, $5E, $40, $5F, $4E
                db      $47, $4F, $52, $42, $53, $5A, $59, $5B
                db      $4B, $43, $4A

; Put the machine in mode 1 with the picture's four pens.
; Corrupts: everything
screen_init:
                ld      bc, GATE_ARRAY
                ld      a, MODE_1
                out     (c), a
                ; the four pens, and the border with them
                ld      hl, picture_inks
                ld      d, 0
.each_pen:
                ld      a, d
                or      %01000000               ; choose this pen
                ld      bc, GATE_ARRAY
                out     (c), a
                ld      a, (hl)
                call    hardware_ink
                or      %01000000               ; give it a colour
                ld      bc, GATE_ARRAY
                out     (c), a
                inc     hl
                inc     d
                ld      a, d
                cp      4
                jr      nz, .each_pen
                ; the border, which is pen sixteen
                ld      bc, GATE_ARRAY
                ld      a, %01010000
                out     (c), a
                ld      a, (picture_inks)
                call    hardware_ink
                or      %01000000
                ld      bc, GATE_ARRAY
                out     (c), a
                ret

; The hardware's colour for the firmware's number in A.
; Corrupts: AF, HL
hardware_ink:
                cp      27
                jr      c, .known
                xor     a
.known:
                ld      hl, firmware_inks
                add     a, l
                ld      l, a
                jr      nc, .no_carry
                inc     h
.no_carry:
                ld      a, (hl)
                ret

; The colours a picture starts in.  Pen one, and nothing in the picture data
; says so: the frame every room of the Amstrad adventures draws carries no
; colour order at all and comes out in pen one on the machine.
; Corrupts: AF
gfx_start_colours:
                ld      a, 1
                ld      (gfx_ink), a
                ld      (gfx_pen1), a
                ld      (gfx_pen2), a
                xor     a
                ld      (gfx_paper), a
                ld      (gfx_bright), a
                ld      (gfx_flash), a
                ret

; The border, which here is one more pen.
; Corrupts: everything
gfx_border:
                push    af
                ld      bc, GATE_ARRAY
                ld      a, %01010000
                out     (c), a
                pop     af
                call    hardware_ink
                or      %01000000
                ld      bc, GATE_ARRAY
                out     (c), a
                ret

; Wipe the picture area to pen nought.  It is 64 bytes of every line, 32
; pixels in from the left, and 128 lines of them.
; Corrupts: everything
gfx_clear:
                ld      e, 0
.each_row:
                ld      d, 0
                push    de
                call    pixel_address
                ld      b, 64
                xor     a
.across:
                ld      (hl), a
                inc     hl
                djnz    .across
                pop     de
                inc     e
                ld      a, e
                cp      PICTURE_ROWS
                jr      nz, .each_row
                ret

; The four pens a picture wants, in the firmware's numbering.  An adventure
; off an Amstrad carries its own; until the format holds them these are the
; four the machine starts with.
picture_inks:   db      0, 24, 20, 6
