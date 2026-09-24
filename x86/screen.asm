; MIT License, Copyright (c) 2025 Cronomantic
;
; The text on a PC's CGA, which is the Amstrad's text: z80/cpc/screen.asm.
;
; The screen is the same shape.  320 by 200 in four colours is forty
; characters across and twenty five down, of which the picture takes the top
; sixteen and the text the nine below; a character is eight pixels across,
; which here too is two bytes.  What differs is where a row is: a character
; row is eight scan lines, the even four of them one after another in the
; first eight kilobytes of the card and the odd four in the second, so each
; character row is three hundred and twenty bytes in each bank and the rows
; follow one another.
;
; And what a pen is.  The text is written in the values its two colours come
; to in the picture on the screen, as a colour in a picture is: the ink the
; text asks for and, behind it, the paper, which is black off a Spectrum and
; pen nought off an Amstrad -- colour_value's first entry either way.  So they
; are settled again whenever a picture brings its own.  See doc/pendiente.md.

TEXT_TOP        equ 16
TEXT_LAST       equ 25
SCREEN_COLS     equ 40
ROW_BYTES       equ 320                 ; a character row, in each bank
                %ifdef AMSTRAD_PICTURES
TEXT_INK_DEFAULT equ 1                  ; pen one, as the original prints
                %else
TEXT_INK_DEFAULT equ 7                  ; white, as on the Spectrum
                %endif

; The screen, the font, and the text window cleared.
; Corrupts: everything but DS
screen_init:
                mov     al, SECTION_FONT
                call    db_section
                mov     [font_seg], es
                mov     al, [es:si]
                mov     [font_first], al
                add     si, 2
                mov     [font_glyphs], si
                mov     ax, 0004h               ; 320 by 200 in four colours
                int     10h
                call    palette_start
                call    cga_rows_init
                mov     al, [text_ink_start]
                call    text_ink
                ; fall through

; Clear the text window and put the cursor at its top left.
; Corrupts: everything but DS
cls_window:
                mov     al, TEXT_TOP
                mov     cl, TEXT_LAST - TEXT_TOP
                call    clear_rows
                mov     byte [cursor_x], 0
                mov     byte [cursor_y], TEXT_TOP
                ret

; Clear CL character rows from row AL down, to the paper.
; Corrupts: AX, BX, CX, DI, ES
clear_rows:
                mov     bl, cl
                mov     ah, ROW_BYTES / 16
                mul     ah
                mov     cl, 4
                shl     ax, cl                  ; the row times 320
                mov     di, ax
                mov     al, bl
                mov     ah, ROW_BYTES / 16
                mul     ah
                shl     ax, cl
                shr     ax, 1
                mov     cx, ax                  ; the words in each bank
                mov     ax, CGA_SEGMENT
                mov     es, ax
                mov     al, [paper_byte]
                mov     ah, al
                push    di
                push    cx
                rep     stosw
                pop     cx
                pop     di
                add     di, CGA_BANK
                rep     stosw
                ret

; The byte of the card where the cursor's cell starts: its first scan line,
; with the second in the other bank at the same place.
; Corrupts: AX
cursor_address:
                mov     al, [cursor_y]
                mov     ah, ROW_BYTES / 16
                mul     ah
                push    cx
                mov     cl, 4
                shl     ax, cl
                pop     cx
                mov     di, ax
                mov     al, [cursor_x]
                xor     ah, ah
                shl     ax, 1                   ; two bytes a character
                add     di, ax
                ret

; Move the text window up by one character row: every row of it but the top
; one, a run in each bank, and the one left at the bottom cleared.
; Corrupts: everything but DS
scroll_window:
                mov     al, [text_top]
                mov     ah, ROW_BYTES / 16
                mul     ah
                mov     cl, 4
                shl     ax, cl
                mov     di, ax                  ; where the window begins
                lea     si, [di + ROW_BYTES]    ; and the row under it
                mov     al, TEXT_LAST - 1
                sub     al, [text_top]
                mov     ah, ROW_BYTES / 16
                mul     ah
                shl     ax, cl
                shr     ax, 1
                mov     cx, ax                  ; words: every row but the first
                push    ds
                mov     ax, CGA_SEGMENT
                mov     ds, ax
                mov     es, ax
                cld
                push    si
                push    di
                push    cx
                rep     movsw
                pop     cx
                pop     di
                pop     si
                add     si, CGA_BANK
                add     di, CGA_BANK
                rep     movsw
                pop     ds
                mov     al, TEXT_LAST - 1
                mov     cl, 1
                jmp     clear_rows

; TEXT: the text has the whole screen from now on.  Nothing is cleared and
; the cursor does not move; only how far the scrolling reaches changes.
; Corrupts: nothing
text_window_all:
                mov     byte [text_top], 0
                ret

; And back under the picture, which is what drawing a picture does.  A cursor
; left above the new top comes down to it.
; Corrupts: nothing
text_window_below:
                mov     byte [text_top], TEXT_TOP
                cmp     byte [cursor_y], TEXT_TOP
                jae     .below
                mov     byte [cursor_y], TEXT_TOP
                mov     byte [cursor_x], 0
.below:
                ret

; Start a new line, scrolling if the window is full.
; Corrupts: everything but DS
new_line:
                %ifdef TRANSCRIPT
                mov     al, 10
                call    transcript_put
                %endif
                mov     byte [cursor_x], 0
                mov     al, [cursor_y]
                inc     al
                cmp     al, TEXT_LAST
                jb      .fits
                call    scroll_window
                mov     al, TEXT_LAST - 1
.fits:
                mov     [cursor_y], al
                ret

; The ink the text is printed in, AL, from a change of ink in a message or
; from the adventure's own: a colour of the sixteen off a Spectrum, a pen off
; an Amstrad, and either way the value it comes to in the picture on the
; screen.  The paper is colour nought's, whatever the ink.
; Corrupts: AX, BX
text_ink:
                and     al, 0Fh
                mov     [text_colour], al
                ; fall through

; Settle the two again from the picture's values, which have just changed.
; Corrupts: AX, BX
text_recolour:
                mov     bl, [text_colour]
                xor     bh, bh
                mov     al, [colour_value + bx]
                call    value_byte
                mov     [ink_byte], al
                mov     al, [colour_value]
                call    value_byte
                mov     [paper_byte], al
                ret

; Draw the glyph for code AL at the cursor and step right.  Each line of the
; glyph is two bytes of the card: the top half of the font's byte the first,
; the bottom half the second, a lit pixel in the ink's value and the rest in
; the paper's.
; Corrupts: everything but DS
print_char:
                %ifdef TRANSCRIPT
                call    transcript_put
                %endif
                sub     al, [font_first]
                xor     ah, ah
                mov     cl, 3
                shl     ax, cl                  ; eight bytes a glyph
                add     ax, [font_glyphs]
                mov     si, ax
                call    cursor_address
                mov     es, [font_seg]
                mov     cx, 8                   ; eight lines, two a pass
                xor     bp, bp                  ; the bank the line is in
.each_line:
                mov     es, [font_seg]
                mov     al, [es:si]
                inc     si
                mov     ah, al
                push    cx
                mov     cl, 4
                shr     al, cl
                pop     cx
                call    in_ink                  ; the left four pixels
                mov     dl, al
                mov     al, ah
                and     al, 0Fh
                call    in_ink                  ; and the right four
                mov     dh, al
                mov     ax, CGA_SEGMENT
                mov     es, ax
                mov     [es:di + bp], dx
                xor     bp, CGA_BANK            ; the next line is in the other
                jnz     .same_place             ; bank, at the same place...
                add     di, CGA_ACROSS          ; ...or down a line in this one
.same_place:
                loop    .each_line
                mov     al, [cursor_x]
                inc     al
                cmp     al, SCREEN_COLS
                jb      .same_line
                jmp     new_line
.same_line:
                mov     [cursor_x], al
                ret

; Four pixels, the low four bits of AL with the first in bit three, as a byte
; of the card in the text's two colours.
; Corrupts: AL, BX
in_ink:
                mov     bl, al
                xor     bh, bh
                mov     al, [lit_four + bx]
                mov     bl, al
                and     al, [ink_byte]
                not     bl
                and     bl, [paper_byte]
                or      al, bl
                ret

; Step back one place and rub out what was there.
; Corrupts: everything but DS
backspace:
                %ifdef TRANSCRIPT
                mov     al, 8
                call    transcript_put
                %endif
                mov     al, [cursor_x]
                test    al, al
                jnz     .same_line
                mov     al, [cursor_y]
                cmp     al, [text_top]
                je      .done                   ; nothing left to rub out
                dec     al
                mov     [cursor_y], al
                mov     al, SCREEN_COLS - 1
                jmp     .place
.same_line:
                dec     al
.place:
                mov     [cursor_x], al
                call    cursor_address
                mov     ax, CGA_SEGMENT
                mov     es, ax
                mov     al, [paper_byte]
                mov     ah, al
                mov     cx, 4
.each_pair:
                mov     [es:di], ax
                mov     [es:di + CGA_BANK], ax
                add     di, CGA_ACROSS
                loop    .each_pair
.done:
                ret

section .data
; The two bits of every pixel lit in a nibble, the first pixel in bit three.
lit_four:       db      00h, 03h, 0Ch, 0Fh, 30h, 33h, 3Ch, 3Fh
                db      0C0h, 0C3h, 0CCh, 0CFh, 0F0h, 0F3h, 0FCh, 0FFh
font_seg:       dw      0
font_glyphs:    dw      0
font_first:     db      0
cursor_x:       db      0
cursor_y:       db      TEXT_TOP
text_top:       db      TEXT_TOP                ; the first row the text may use
text_colour:    db      TEXT_INK_DEFAULT        ; the colour the text asked for
ink_byte:       db      0FFh
paper_byte:     db      0
section .text
