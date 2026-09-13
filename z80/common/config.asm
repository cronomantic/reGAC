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
                ld      de, CONFIG_PUNCTUATION
                add     hl, de
                ld      a, (hl)                 ; how many marks there are
                ld      (punct_count), a
                inc     hl
                ld      a, (hl)                 ; the space comes first
                ld      (space_code), a
                ld      a, (punct_count)
                ld      c, a
                ld      b, 0
                ld      de, punct_codes
                ldir
                ld      (seps_at), hl           ; the words come after them
                ret

; Whether the code in A is a mark that ends one order and starts the next.
; A space is not one of them: it only parts words.
; Zero flag set when it is.
; Corrupts: AF, BC, HL
ends_statement:
                ld      c, a
                ld      a, (space_code)
                cp      c
                jr      z, .no
                ld      a, (punct_count)
                or      a
                jr      z, .no
                ld      b, a
                ld      hl, punct_codes
.each:
                ld      a, (hl)
                inc     hl
                cp      c
                ret     z
                djnz    .each
.no:
                or      $FF
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
punct_count:    db      0
punct_codes:    ds      8
seps_at:        dw      0                       ; the separator words, if any
