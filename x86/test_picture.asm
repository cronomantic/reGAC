; MIT License, Copyright (c) 2025 Cronomantic
;
; A test build for the pictures on a PC: every picture of the database is
; drawn in turn, and the card's memory is written after each to a file named
; after it, P0001.BIN and so on, in hexadecimal.  tests/test_graphics_pc.py
; compares those with the reference.  How long each took goes to TIMES.BIN,
; four bytes a picture: its number and the ticks of the BIOS's clock, which
; counts 18.2 a second, from asking for it to having it on the screen.
;
; Assembled with NASM into a flat image and given its .EXE header by regac:
;
;   nasm -f bin -I x86/ -DDATABASE="picture.rgac" -o picture.bin
;        x86/test_picture.asm
;
; with -DAMSTRAD_PICTURES as well for an adventure off an Amstrad.
;
; The image is one piece: code and data behind CS, which is also DS, and the
; database behind them on a paragraph of its own, which is its segment.

bits 16
cpu 8086
org 0

CGA_SCREEN_BYTES equ 4000h
BIOS_SEGMENT    equ 40h
BIOS_TICKS      equ 6Ch                 ; the clock's count, in the BIOS's data
MOST_PICTURES   equ 1024

start:
                mov     ax, cs
                mov     ds, ax
                mov     ax, (database - $$) >> 4
                mov     bx, cs
                add     ax, bx
                mov     [db_seg], ax
                call    cga_rows_init
                call    db_init
                call    db_picture_head
                call    picture_init
                mov     ax, 0004h               ; 320 by 200 in four colours
                int     10h
                mov     cx, [gfx_count]
                mov     si, [gfx_index]
.each:
                jcxz    .finished
                push    cx
                push    si
                mov     es, [db_seg]
                mov     ax, [es:si]
                push    ax
                mov     bx, [times_at]
                mov     [took + bx], ax
                call    ticks_now
                mov     [started], ax
                pop     ax
                push    ax
                call    draw_picture
                call    ticks_now
                sub     ax, [started]
                mov     bx, [times_at]
                mov     [took + bx + 2], ax
                add     word [times_at], 4
                pop     ax
                call    write_screen
                pop     si
                pop     cx
                add     si, 4
                dec     cx
                jmp     .each
.finished:
                call    write_times
                mov     ax, 0003h               ; the text screen again
                int     10h
                mov     ax, 4C00h
                int     21h

; Write the card's memory to a file named after picture AX.
; Corrupts: everything but DS
write_screen:
                mov     di, file_name + 1
                mov     cx, 4
.each_digit:
                push    cx
                mov     cl, 4
                rol     ax, cl                  ; the top four bits first
                pop     cx
                mov     bx, ax
                and     bx, 0Fh
                mov     dl, [hex_digits + bx]
                mov     [di], dl
                inc     di
                loop    .each_digit
                mov     ah, 3Ch                 ; make it
                xor     cx, cx
                mov     dx, file_name
                int     21h
                jc      .failed
                mov     bx, ax
                push    ds
                mov     ax, CGA_SEGMENT
                mov     ds, ax
                mov     ah, 40h                 ; write the whole of it
                mov     cx, CGA_SCREEN_BYTES
                xor     dx, dx
                int     21h
                pop     ds
                mov     ah, 3Eh
                int     21h
.failed:
                ret

; The BIOS's clock, in AX.
; Corrupts: ES
ticks_now:
                mov     ax, BIOS_SEGMENT
                mov     es, ax
                mov     ax, [es:BIOS_TICKS]
                ret

; How long each picture took, to TIMES.BIN.
; Corrupts: everything but DS
write_times:
                mov     ah, 3Ch
                xor     cx, cx
                mov     dx, times_name
                int     21h
                jc      .failed
                mov     bx, ax
                mov     ah, 40h
                mov     cx, [times_at]
                mov     dx, took
                int     21h
                mov     ah, 3Eh
                int     21h
.failed:
                ret

file_name:      db      "P0000.BIN", 0
times_name:     db      "TIMES.BIN", 0
started:        dw      0
times_at:       dw      0
took:           times MOST_PICTURES * 2 dw 0
hex_digits:     db      "0123456789ABCDEF"

%include "database.asm"
%include "picture.asm"
%include "cga.asm"
%include "line.asm"
%include "shapes.asm"
; The rules of the GAC the adventure was written with: an adventure off an
; Amstrad is built with -DAMSTRAD_PICTURES and draws with the Amstrad's, and
; one off a Spectrum with the Spectrum's.  One or the other, never both.
%ifdef AMSTRAD_PICTURES
%include "amstrad.asm"
%include "amstrad_fill.asm"
%else
%include "draw.asm"
%include "fill.asm"
%endif

                align   16
database:
                incbin  DATABASE
