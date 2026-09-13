; MIT License, Copyright (c) 2025 Cronomantic
;
; Printing a run of text, breaking it between words.
;
; This knows nothing about any screen beyond how wide it is and where the
; cursor sits, both of which the machine's own screen layer names, so every
; machine shares it.

; Print BC characters from HL, breaking between words so none is split.
; Corrupts: AF, BC, DE, HL
print_text:
.word:
                ld      a, b
                or      c
                ret     z
                ; how long is the run up to the next space
                push    hl
                push    bc
                ld      de, 0                   ; E counts it
.measure:
                ld      a, b
                or      c
                jr      z, .measured
                ld      a, (hl)
                push    hl
                ld      hl, space_code
                cp      (hl)
                pop     hl
                jr      z, .measured
                inc     hl
                dec     bc
                inc     e
                jr      .measure
.measured:
                pop     bc
                pop     hl
                ; does it fit on what is left of this line?
                ld      a, (cursor_x)
                add     a, e
                cp      SCREEN_COLS + 1
                jr      c, .fits
                ld      a, (cursor_x)
                or      a
                jr      z, .fits                ; no point breaking at column 0
                push    hl
                push    bc
                push    de
                call    new_line                ; this treads on every register
                pop     de
                pop     bc
                pop     hl
.fits:
                ; print the run, then the space that ended it
                ld      a, e
                or      a
                jr      z, .space
.emit:
                ld      a, (hl)
                inc     hl
                dec     bc
                push    bc
                push    hl
                push    de
                call    print_char
                pop     de
                pop     hl
                pop     bc
                dec     e
                jr      nz, .emit
.space:
                ld      a, b
                or      c
                ret     z
                ld      a, (hl)                 ; the space itself
                inc     hl
                dec     bc
                push    bc
                push    hl
                call    print_char
                pop     hl
                pop     bc
                jr      .word

