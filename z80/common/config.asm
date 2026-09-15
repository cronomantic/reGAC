; MIT License, Copyright (c) 2025 Cronomantic
;
; The pieces of the config section every machine needs: the marks that end one
; order and start the next, and where the words that do the same are kept.
;
; What used to be here as well was a table turning what the player typed into
; this adventure's codes, and another saying where the ten digits were.
; Neither is needed now that the character set is the same in every adventure:
; a code from the space upwards is the character's own ASCII, so a keyboard
; hands over what it read and a digit is a nought and a number.  See
; doc/textos.md.

SPACE_CODE      equ 32                  ; which is what words are parted by
DIGIT_ZERO      equ 48

; Corrupts: AF, BC, DE, HL
config_init:
                ld      a, SECTION_CONFIG
                call    db_section
                ld      de, CONFIG_PUNCTUATION
                add     hl, de
                ld      a, (hl)                 ; how many marks there are
                ld      (punct_count), a
                inc     hl
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
                ld      a, SPACE_CODE
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

; The code for the ASCII character in A, or NO_CHARACTER.  They are the same
; thing from the space up, so all this does is say what is not a character at
; all; it stays a routine because every keyboard calls it and none of them
; should have to know that.
; Corrupts: AF
ascii_to_code:
                cp      SPACE_CODE
                ret     nc                      ; the space and everything above
                ld      a, NO_CHARACTER
                ret

punct_count:    db      0
punct_codes:    ds      8
seps_at:        dw      0                       ; the separator words, if any
