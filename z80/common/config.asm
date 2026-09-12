; MIT License, Copyright (c) 2025 Cronomantic
;
; The pieces of the config section every machine needs: the codes of the
; digits, so a score can be printed, the table that turns what the player
; types into this adventure's own codes, and the code of the space, which is
; what words are separated by.

; Corrupts: AF, BC, DE, HL
config_init:
                ld      a, SECTION_CONFIG
                call    db_section
                push    hl
                ld      de, CONFIG_DIGITS
                add     hl, de
                ld      de, digit_codes
                ld      bc, 10
                ldir
                pop     hl
                push    hl
                ld      de, CONFIG_ASCII
                add     hl, de
                ld      de, ascii_codes
                ld      bc, 96
                ldir
                pop     hl
                ld      de, CONFIG_PUNCTUATION + 1
                add     hl, de
                ld      a, (hl)                 ; the space comes first
                ld      (space_code), a
                ret

; The code for the ASCII character in A, or NO_CHARACTER.
; Corrupts: HL
ascii_to_code:
                sub     32
                jr      c, .missing
                cp      96
                ccf
                jr      c, .missing
                ld      hl, ascii_codes
                add     a, l
                ld      l, a
                jr      nc, .no_carry
                inc     h
.no_carry:
                ld      a, (hl)
                ret
.missing:
                ld      a, NO_CHARACTER
                ret

digit_codes:    ds      10
ascii_codes:    ds      96
space_code:     db      0
