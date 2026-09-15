; MIT License, Copyright (c) 2025 Cronomantic
;
; Printing a run of text, breaking it between words.
;
; This knows nothing about any screen beyond how wide it is and where the
; cursor sits, both of which the machine's own screen layer names, so every
; machine shares it.

; A code that is not a letter but a command to whoever is printing: the one
; there is says the ink changes, and the code after it says to what.  See
; doc/textos.md.
INK_CODE        equ 1
INK_ZERO        equ 48                  ; the colour rides as a character

; Print BC characters from HL, breaking between words so none is split.
; Corrupts: AF, BC, DE, HL
print_text:
.word:
                call    obey_commands           ; a change of ink, if there is
                ld      a, b                    ; one waiting
                or      c
                ret     z
                ; how long is the run up to the next space or command
                push    hl
                push    bc
                ld      de, 0                   ; E counts it
.measure:
                ld      a, b
                or      c
                jr      z, .measured
                ld      a, (hl)
                push    hl
                cp      SPACE_CODE
                pop     hl
                jr      z, .measured
                cp      INK_CODE
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
                ld      a, (hl)                 ; the space itself, unless what
                cp      INK_CODE                ; stopped the run was a command
                jr      z, .word
                inc     hl
                dec     bc
                push    bc
                push    hl
                call    print_char
                pop     hl
                pop     bc
                jr      .word

; Obey whatever commands are at HL, of which there is one: a change of ink.
; HL and BC come back past them, so a run of commands costs one call.
; Corrupts: AF, DE
obey_commands:
                ld      a, b
                or      c
                ret     z
                ld      a, (hl)
                cp      INK_CODE
                ret     nz
                inc     hl
                dec     bc
                ld      a, (hl)                 ; the colour follows it
                inc     hl
                dec     bc
                sub     INK_ZERO
                push    bc
                push    hl
                push    de
                call    text_ink
                pop     de
                pop     hl
                pop     bc
                jr      obey_commands

