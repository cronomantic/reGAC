; MIT License, Copyright (c) 2025 Cronomantic
;
; The pieces of the config section every machine needs: the marks that end one
; order and start the next, and where the words that do the same are kept.
; It is z80/common/config.asm; see there for why each is as it is.
;
; Every code from the space upwards is the character's own ASCII, in every
; adventure, so a key is a code as it comes.  See doc/textos.md.

SPACE_CODE      equ 32                  ; which is what words are parted by
DIGIT_ZERO      equ 48
CONFIG_PUNCTUATION equ 3                ; how many, then the codes
NO_CHARACTER    equ 0FFh                ; the adventure has no such character
MOST_MARKS      equ 8

; Corrupts: AX, BX, CX, SI, DI, ES
config_init:
                mov     al, SECTION_CONFIG
                call    db_section
                add     si, CONFIG_PUNCTUATION
                mov     cl, [es:si]             ; how many marks there are
                inc     si
                xor     ch, ch
                cmp     cx, MOST_MARKS
                jbe     .fits
                mov     cx, MOST_MARKS
.fits:
                mov     [punct_count], cl
                mov     di, punct_codes
.each_mark:
                jcxz    .marks_done
                mov     al, [es:si]
                inc     si
                mov     [di], al
                inc     di
                dec     cx
                jmp     .each_mark
.marks_done:
                call    .past_marks             ; any past the eighth, too
                mov     [seps_at], si           ; the words come after them
                ; and after those, where the word for having nothing is kept
                mov     al, [es:si]             ; how many separator words
                inc     si
.skip:
                test    al, al
                jz      .counted
                dec     al
                mov     cl, [es:si]             ; how long this one is
                inc     si
                xor     ch, ch
                add     si, cx
                jmp     .skip
.counted:
                mov     ax, [es:si]
                mov     [nothing_at], ax
                add     si, 2
                ; And the last byte of the section but one: the ink this
                ; adventure wants its text in, or nought for the one the
                ; machine came with.  The last is how many bytes each picture
                ; carries, which db_picture_head reads.
                mov     al, [es:si]
                test    al, al
                jz      .own_ink
                mov     [text_ink_start], al
.own_ink:
                ret

; SI at the first byte past the marks, however many the section held.
.past_marks:
                mov     al, SECTION_CONFIG
                call    db_section
                add     si, CONFIG_PUNCTUATION
                mov     cl, [es:si]
                xor     ch, ch
                inc     si
                add     si, cx
                ret

; Whether the code in AL ends one order and starts the next.  The original has
; these four written into it and nothing else: see z80/common/config.asm.
; Zero flag set when it does.
ends_statement:
                cmp     al, ','
                je      .yes
                cmp     al, '.'
                je      .yes
                cmp     al, ';'
                je      .yes
                cmp     al, '!'
.yes:
                ret

; Whether the code in AL parts one word from the next: a space, or any of the
; marks of punctuation this adventure knows.  Zero flag set when it does.
; Keeps every register.
word_ends_at:
                cmp     al, SPACE_CODE
                je      .yes
                push    cx
                push    si
                mov     cl, [punct_count]
                xor     ch, ch
                mov     si, punct_codes
                jcxz    .no
.each:
                cmp     al, [si]
                je      .found
                inc     si
                loop    .each
.no:
                cmp     al, SPACE_CODE          ; which is not equal: clears Z
                pop     si
                pop     cx
                ret
.found:
                pop     si
                pop     cx
.yes:
                ret

; The code for the ASCII character in AL, or NO_CHARACTER.
ascii_to_code:
                cmp     al, SPACE_CODE
                jae     .is_one
                mov     al, NO_CHARACTER
.is_one:
                ret

section .data
; What a message starts in, and goes back to when it ends: the machine's own
; unless the adventure asked for another.
text_ink_start: db      TEXT_INK_DEFAULT
punct_count:    db      0
punct_codes:    times MOST_MARKS db 0
seps_at:        dw      0                       ; the separator words, if any
nothing_at:     dw      0                       ; the word for having none
section .text
