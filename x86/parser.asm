; MIT License, Copyright (c) 2025 Cronomantic
;
; Making sense of what the player typed: z80/common/parser.asm, where why each
; rule is the original's is written.
;
; A line is cut into orders at a mark that ends one and at the words the
; adventure names as parting them; each order is cut into words and each word
; is looked for in the vocabulary.  Typing the start of a word is enough, and
; a word longer than the entry does not match it; the first word that matches
; takes the first empty slot.
;
; The line is in the data segment and the vocabulary in the database's, so
; the one is DS:SI and the other ES.

WORD_VERB       equ 0
WORD_NOUN       equ 1
WORD_ADVERB     equ 2
WORD_PRONOUN    equ 3

; Where the vocabulary is.
; Corrupts: AX, BX, CX, SI, ES
vocab_init:
                mov     al, SECTION_VOCAB
                call    db_section
                mov     [vocab_seg], es
                mov     ax, [es:si]
                mov     [vocab_count], ax
                add     si, 2
                mov     [vocab_start], si
                ret

; The next order on the line: its start in SI and its length in CX.
; Corrupts: everything but DS
next_statement:
                mov     ax, [line_at]
                mov     [stmt_start], ax
                mov     word [stmt_len], 0
                mov     byte [word_len], 0
.each:
                cmp     word [line_left], 0
                je      .line_ended
                mov     bx, [line_at]
                mov     al, [bx]
                call    ends_statement
                je      .a_mark
                call    word_ends_at            ; punctuation parts words now
                je      .a_space
                inc     byte [word_len]         ; it belongs to the word
                call    .keep
                jmp     .each
.a_space:
                call    .parting_word
                jc      .cut_before_word
                mov     byte [word_len], 0
                call    .keep
                jmp     .each
.a_mark:
                call    .step                   ; the mark belongs to neither
                jmp     .done
.line_ended:
                call    .parting_word
                jc      .cut_before_word
                jmp     .done
.cut_before_word:
                mov     al, [word_len]          ; the order ends before it
                xor     ah, ah
                sub     [stmt_len], ax
.done:
                mov     cx, [stmt_len]
                mov     si, [stmt_start]
                ret

; Whether the word that has just ended parts two orders.  Carry set if so.
.parting_word:
                mov     cl, [word_len]
                test    cl, cl
                jz      .no_word                ; (which clears the carry)
                xor     ch, ch
                mov     si, [line_at]
                sub     si, cx                  ; where the word began
                jmp     separator_find
.no_word:
                clc
                ret

; One character further along, and it counts towards this order.
.keep:
                inc     word [stmt_len]
.step:
                inc     word [line_at]
                dec     word [line_left]
                ret

; Whether the word of CL codes at DS:SI is one the adventure names as parting
; two orders.  Carry set when it is.
; Corrupts: AX, BX, CX, DX, DI, ES
separator_find:
                mov     al, SECTION_CONFIG
                call    db_segment
                mov     di, [seps_at]
                mov     dl, [es:di]             ; how many words it names
                inc     di
.each:
                test    dl, dl
                jz      .none
                mov     al, [es:di]             ; how long this one is
                inc     di
                cmp     al, cl
                jne     .skip
                xor     bx, bx
.compare:
                mov     ah, [si + bx]
                cmp     ah, [es:di + bx]
                jne     .skip
                inc     bx
                cmp     bl, cl
                jb      .compare
                stc
                ret
.skip:
                xor     ah, ah
                add     di, ax                  ; past this word's codes
                dec     dl
                jmp     .each
.none:
                clc
                ret

; Look for the word of find_length codes at find_word among the entries of
; kind find_kind.  The number comes back in AL, nought when nothing matched.
; Corrupts: everything but DS
vocab_find:
                mov     es, [vocab_seg]
                mov     bx, [vocab_start]
                mov     cx, [vocab_count]
                mov     dl, [find_length]
.each:
                jcxz    .none
                dec     cx
                mov     al, [es:bx]             ; what kind of word it is
                mov     ah, [es:bx + 2]         ; how long it is
                cmp     al, [find_kind]
                jne     .next
                cmp     dl, ah
                ja      .next                   ; more typed than the word holds
                test    dl, dl
                jz      .next
                push    cx
                mov     cl, dl
                xor     ch, ch
                mov     si, [find_word]
                lea     di, [bx + 3]
.letters:
                mov     al, [si]
                cmp     al, [es:di]
                jne     .mismatch
                inc     si
                inc     di
                loop    .letters
                pop     cx
                mov     al, [es:bx + 1]         ; its number
                ret
.mismatch:
                pop     cx
.next:
                mov     al, ah
                xor     ah, ah
                add     bx, ax
                add     bx, 3                   ; step over the codes
                jmp     .each
.none:
                xor     al, al
                ret

; Make sense of the order of CX codes at DS:SI.  Sets the verb, the nouns and
; the adverb; carry set if anything was understood.
; Corrupts: everything but DS
parse_sentence:
                ; What a pronoun in this order will stand for: the last noun
                ; the order before named.
                mov     al, [vm_noun2]
                test    al, al
                jnz     .remember
                mov     al, [vm_noun1]
                test    al, al
                jz      .nothing_named
.remember:
                mov     [vm_old_noun], al
.nothing_named:
                xor     al, al
                mov     [vm_verb], al
                mov     [vm_noun1], al
                mov     [vm_noun2], al
                mov     [vm_adverb], al
                mov     [parse_ptr], si
                mov     [parse_left], cx
.each_word:
                ; step over any spaces
                mov     si, [parse_ptr]
                mov     cx, [parse_left]
.skip_spaces:
                jcxz    .finished
                mov     al, [si]
                call    word_ends_at
                jne     .word_start
                inc     si
                dec     cx
                jmp     .skip_spaces
.word_start:
                mov     [parse_ptr], si
                ; measure it
                xor     dl, dl
.measure:
                jcxz    .measured
                mov     al, [si]
                call    word_ends_at
                je      .measured
                inc     si
                dec     cx
                inc     dl
                jmp     .measure
.measured:
                mov     [parse_left], cx
                push    si
                mov     [word_length], dl
                test    dl, dl
                jz      .after_word
                call    try_word                ; first empty slot wins
.after_word:
                pop     si
                mov     [parse_ptr], si
                cmp     word [parse_left], 0
                jne     .each_word
.finished:
                ; something was understood if there is a verb or a noun
                mov     al, [vm_verb]
                or      al, [vm_noun1]
                jz      .nothing
                stc
                ret
.nothing:
                clc
                ret

; The word at parse_ptr, tried as each kind in turn, and the first slot that
; is empty takes it: the verb, then the adverb, then the nouns, and a pronoun
; stands for the last noun named.
; Corrupts: everything but DS
try_word:
                cmp     byte [vm_verb], 0
                jne     .try_adverb
                mov     al, WORD_VERB
                call    look_up
                test    al, al
                jz      .try_adverb
                mov     [vm_verb], al
                ret
.try_adverb:
                cmp     byte [vm_adverb], 0
                jne     .a_noun
                mov     al, WORD_ADVERB
                call    look_up
                test    al, al
                jz      .a_noun
                mov     [vm_adverb], al
                ret
.a_noun:
                cmp     byte [vm_noun2], 0
                jne     .done                   ; both named already
                mov     al, WORD_NOUN
                call    look_up
                test    al, al
                jnz     .found
                mov     al, WORD_PRONOUN
                call    look_up
                test    al, al
                jz      .done
                mov     al, [vm_old_noun]
                test    al, al
                jz      .done
.found:
                cmp     byte [vm_noun1], 0
                jne     .the_second
                mov     [vm_noun1], al
                ret
.the_second:
                mov     [vm_noun2], al
.done:
                ret

; Look the current word up as kind AL.
look_up:
                mov     [find_kind], al
                mov     ax, [parse_ptr]
                mov     [find_word], ax
                mov     al, [word_length]
                mov     [find_length], al
                jmp     vocab_find

section .data
vocab_seg:      dw      0
vocab_start:    dw      0
vocab_count:    dw      0
find_word:      dw      0
find_length:    db      0
find_kind:      db      0
parse_ptr:      dw      0
parse_left:     dw      0
line_at:        dw      0                       ; what is left of the line
line_left:      dw      0
stmt_start:     dw      0
stmt_len:       dw      0
word_len:       db      0
word_length:    db      0
vm_old_noun:    db      0
section .text
