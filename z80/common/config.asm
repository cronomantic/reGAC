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
                ; and after those, where the word for having nothing is kept
                ld      a, (hl)                 ; how many separator words
                inc     hl
.skip:
                or      a
                jr      z, .counted
                dec     a
                ld      c, a
                ld      a, (hl)                 ; how long this one is
                inc     hl
                ld      e, a
                ld      d, 0
                add     hl, de
                ld      a, c
                jr      .skip
.counted:
                ld      e, (hl)
                inc     hl
                ld      d, (hl)
                ld      (nothing_at), de
                ret

; Whether the code in A ends one order and starts the next.  The original
; has these four written into it and nothing else, and uses the adventure's
; own table of punctuation only to part words: measured on it, a comma or a
; full stop make two orders out of one line, and the -, the ? and the : that
; MegaCorp's table holds do not.
; Zero flag set when it does.
; Corrupts: AF
ends_statement:
                cp      ','
                ret     z
                cp      '.'
                ret     z
                cp      ';'
                ret     z
                cp      '!'
                ret

; Whether the code in A parts one word from the next: a space, or any of the
; marks of punctuation this adventure knows.  Zero flag set when it does.
; Corrupts: AF, BC, HL
parts_word:
                cp      SPACE_CODE
                ret     z
                ld      c, a
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

; The same question, asked from the middle of a loop that is using the
; registers: whether the code in A parts a word.  Zero flag set when it does.
; Keeps BC, DE and HL.
word_ends_at:
                push    bc
                push    hl
                call    parts_word
                pop     hl
                pop     bc
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
nothing_at:     dw      0                       ; the word for having none
