; MIT License, Copyright (c) 2025 Cronomantic
;
; Filling an area of a picture off an Amstrad on a PC's CGA, with the
; Amstrad's rules -- read off that machine, and written up in
; z80/cpc/fill.asm and doc/graficos.md.  It is z80/next/amstrad_fill.asm.
;
; The walk is the same as everywhere else: up and down the one column the fill
; was started in, laying a horizontal run across each row, stopping the moment
; the point directly above or below is blocked.  A point blocks when its pen is
; no longer the pen under the seed; and what a fill lays down is a chequer of
; the two pens the colour order names, the one or the other as the column and
; the y of the commands add up even or odd.
;
; Here four pixels are a byte, and a run is walked the way the Spectrum's fill
; walks its mask: a byte it steps into is looked at whole first, because four
; points of the seed's pen are a byte of the seed's value four times over, and
; only a byte with something else in it is picked apart a pixel at a time.

PICTURE_TOP     equ 175                 ; the y a picture reaches
PICTURE_BOTTOM  equ 48
FILL_INK        equ 0                   ; the three fills, which here are one
FILL_PAPER      equ 1
FILL_SHADE      equ 2

; Whether a fill is stopped at (DL across, DH up the commands' way).  Zero flag
; set while it is still the pen the fill started on.
; Corrupts: AX, BX, CX, DI, ES
blocked:
                push    dx
                mov     al, dh
                call    to_row
                mov     dh, al
                call    pen_at
                cmp     al, [fill_seed]
                pop     dx
                ret

; Fill from (DL across, DH up).
; Corrupts: everything but DS
flood_fill:
                mov     [fill_x], dl
                push    dx
                mov     al, dh
                call    to_row
                mov     dh, al
                call    pen_at
                pop     dx
                mov     [fill_seed], al
                cmp     al, 255
                je      .done                   ; the seed is off the picture
                call    value_byte
                mov     [fill_seed_byte], al
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

; Lay the two pens across the run through (fill_x, fill_y).
; Corrupts: everything but DS
fill_run:
                mov     al, [fill_y]
                call    to_row
                mov     [fill_row], al
                mov     dh, al
                mov     dl, [fill_x]
                call    run_extent
                ; The two pens, the first where the column and the y add up
                ; even: which one a point gets turns on the y of the commands,
                ; as the original picks between its two pattern bytes with bit
                ; nought of that y, and not on the screen row.  A byte starts
                ; on an even column, so every byte of the run is the same.
                mov     bl, [gfx_pen1]
                and     bl, 3
                xor     bh, bh
                mov     dl, [colour_value + bx]         ; an even column
                mov     bl, [gfx_pen2]
                and     bl, 3
                mov     dh, [colour_value + bx]         ; and an odd one
                test    byte [fill_y], 1
                jz      .lined_up
                xchg    dl, dh
.lined_up:
                mov     cl, 2
                shl     dl, cl
                or      dl, dh                          ; two pixels
                mov     al, dl
                mov     cl, 4
                shl     al, cl
                or      dl, al                          ; and four
                mov     dh, dl
                mov     al, [fill_row]
                mov     bl, [fill_left]
                mov     bh, [fill_right]
                jmp     lay_run

; How far the run of the seed's pen through (DL, DH) reaches, into fill_left
; and fill_right.  ES:DI walks the screen and CL is how far the pixel's two
; bits are from the bottom of its byte: six for the first of the four, nought
; for the last.
; Corrupts: AX, BX, CX, DI, ES
run_extent:
                mov     [fill_left], dl
                mov     [fill_right], dl
                call    cga_address
                mov     ax, CGA_SEGMENT
                mov     es, ax
                mov     [run_start], di
                mov     [run_shift], cl
                mov     ah, [fill_seed]
.leftwards:
                cmp     byte [fill_left], 0
                je      .left_done
                cmp     cl, 6                   ; the first of its byte:
                jne     .pixel_before           ; over into the byte before
                dec     di
                mov     al, [es:di]
                cmp     al, [fill_seed_byte]
                jne     .last_of_byte           ; something else: one at a time
                sub     byte [fill_left], 4     ; all four the seed's, and we
                jmp     .leftwards              ; stand at its first
.last_of_byte:
                mov     cl, 0
                jmp     .look_left
.pixel_before:
                add     cl, 2
.look_left:
                mov     al, [es:di]
                shr     al, cl
                and     al, 3
                cmp     al, ah
                jne     .left_done
                dec     byte [fill_left]
                jmp     .leftwards
.left_done:
                mov     di, [run_start]
                mov     cl, [run_shift]
.rightwards:
                cmp     byte [fill_right], 255
                je      .right_done             ; the edge of the picture
                test    cl, cl                  ; the last of its byte:
                jnz     .pixel_after            ; over into the next
                inc     di
                mov     al, [es:di]
                cmp     al, [fill_seed_byte]
                jne     .first_of_byte
                add     byte [fill_right], 4    ; standing at its last
                jmp     .rightwards
.first_of_byte:
                mov     cl, 6
                jmp     .look_right
.pixel_after:
                sub     cl, 2
.look_right:
                mov     al, [es:di]
                shr     al, cl
                and     al, 3
                cmp     al, ah
                jne     .right_done
                inc     byte [fill_right]
                jmp     .rightwards
.right_done:
                ret

; Which of the three fills this is.  The Amstrad has only one: what it lays
; down is whatever the colour order last named, so the three come to the same
; thing here and the pens are left alone.
set_fill_pattern:
                ret

fill_x:         db      0
fill_seed_y:    db      0
fill_y:         db      0
fill_row:       db      0
fill_left:      db      0
fill_right:     db      0
fill_seed:      db      0
fill_seed_byte: db      0
run_shift:      db      0
run_start:      dw      0
