; MIT License, Copyright (c) 2025 Cronomantic
;
; Making sense of what the player typed.
;
; A line is cut into sentences wherever a separator or a mark of punctuation
; appears, so "COGE LA LLAVE Y ABRE LA PUERTA" is two orders and they are
; obeyed one after the other.  Each sentence is then cut into words and each
; word is looked for in the vocabulary.
;
; A word has to be typed in full to match, which is what the original did:
; abbreviations like N for NORTE or INVENT for INVENTARIO are separate entries
; in the vocabulary sharing a number, not something the matching works out.
; Matching on the start of a word instead would have LA swallowed by LAMPARA.
;
; The first word that matches takes the first empty slot: verb, then noun,
; then adverb, then second noun.
;
; Everything here works in the adventure's own character codes, so an accented
; letter is matched like any other.

WORD_VERB       equ 0
WORD_NOUN       equ 1
WORD_ADVERB     equ 2
WORD_PRONOUN    equ 3

INPUT_MAX       equ 64

; Read the vocabulary out of the database.
; Corrupts: AF, BC, DE, HL
vocab_init:
                ld      a, SECTION_VOCAB
                call    db_section
                ld      e, (hl)
                inc     hl
                ld      d, (hl)
                inc     hl
                ld      (vocab_count), de
                ld      (vocab_start), hl
                ret

; Look for the word of B codes at HL among the entries of kind find_kind.
; The number comes back in A, zero when nothing matched.
; Corrupts: everything
vocab_find:
                ld      (find_word), hl
                ld      a, b
                ld      (find_length), a
                ld      hl, (vocab_start)
                ld      de, (vocab_count)
.each:
                ld      a, d
                or      e
                jr      z, .none
                dec     de
                ld      a, (hl)                 ; what kind of word it is
                inc     hl
                ld      b, (hl)                 ; its number
                inc     hl
                ld      c, (hl)                 ; how long it is
                inc     hl                      ; HL is now at the codes
                push    de
                push    bc
                push    hl
                ld      d, a
                ld      a, (find_kind)
                cp      d
                jr      nz, .next
                ld      a, (find_length)
                cp      c
                jr      nz, .next               ; the whole word or nothing
                ld      b, a
                ld      de, (find_word)
.letters:
                ld      a, (de)
                cp      (hl)
                jr      nz, .next
                inc     hl
                inc     de
                djnz    .letters
                pop     hl
                pop     bc
                pop     de
                ld      a, b                    ; its number
                ret
.next:
                pop     hl
                pop     bc
                ld      b, 0
                add     hl, bc                  ; step over the codes
                pop     de
                jr      .each
.none:
                xor     a
                ret

; Make sense of the sentence of BC codes at HL.
; Sets the verb, the nouns and the adverb; carry set if anything was understood.
; Corrupts: everything
parse_sentence:
                xor     a
                ld      (vm_verb), a
                ld      (vm_noun1), a
                ld      (vm_noun2), a
                ld      (vm_adverb), a
                ld      (parse_ptr), hl
                ld      (parse_left), bc
.each_word:
                ; step over any spaces
                ld      hl, (parse_ptr)
                ld      bc, (parse_left)
.skip_spaces:
                ld      a, b
                or      c
                jr      z, .finished
                ld      a, (space_code)
                cp      (hl)
                jr      nz, .word_start
                inc     hl
                dec     bc
                jr      .skip_spaces
.word_start:
                ld      (parse_ptr), hl
                ; measure it
                ld      d, 0
.measure:
                ld      a, b
                or      c
                jr      z, .measured
                ld      a, (space_code)
                cp      (hl)
                jr      z, .measured
                inc     hl
                dec     bc
                inc     d
                jr      .measure
.measured:
                ld      (parse_left), bc
                push    hl
                ld      a, d
                ld      (word_length), a
                or      a
                jr      z, .after_word
                ; try it as each kind of word in turn, first empty slot wins
                call    try_word
.after_word:
                pop     hl
                ld      (parse_ptr), hl
                ld      bc, (parse_left)
                ld      a, b
                or      c
                jr      nz, .each_word
.finished:
                ; something was understood if there is a verb or a noun
                ld      a, (vm_verb)
                ld      b, a
                ld      a, (vm_noun1)
                or      b
                ret     z
                scf
                ret

; Try the word at parse_ptr against each kind, filling the first empty slot.
; Corrupts: everything
try_word:
                ld      a, (vm_verb)
                or      a
                jr      nz, .try_noun
                ld      a, WORD_VERB
                call    look_up
                or      a
                jr      z, .try_noun
                ld      (vm_verb), a
                ret
.try_noun:
                ld      a, (vm_noun1)
                or      a
                jr      nz, .try_adverb
                ld      a, WORD_NOUN
                call    look_up
                or      a
                jr      nz, .got_noun
                ; not a noun; a pronoun stands for the last one named
                ld      a, WORD_PRONOUN
                call    look_up
                or      a
                jr      z, .try_adverb
                ld      a, (vm_old_noun)
                or      a
                ret     z
                ld      (vm_noun1), a
                ret
.got_noun:
                ld      (vm_noun1), a
                ld      (vm_old_noun), a
                ret
.try_adverb:
                ld      a, (vm_adverb)
                or      a
                jr      nz, .try_noun2
                ld      a, WORD_ADVERB
                call    look_up
                or      a
                jr      z, .try_noun2
                ld      (vm_adverb), a
                ret
.try_noun2:
                ld      a, (vm_noun2)
                or      a
                ret     nz
                ld      a, (vm_noun1)
                or      a
                ret     z                       ; no first noun, no second
                ld      a, WORD_NOUN
                call    look_up
                or      a
                ret     z
                ld      (vm_noun2), a
                ret

; Look the current word up as kind A.
look_up:
                ld      (find_kind), a
                ld      hl, (parse_ptr)
                ld      a, (word_length)
                ld      b, a
                jp      vocab_find

vocab_start:    dw      0
vocab_count:    dw      0
find_word:      dw      0
find_length:    db      0
find_kind:      db      0
parse_ptr:      dw      0
parse_left:     dw      0
word_length:    db      0
vm_old_noun:    db      0
input_buffer:   ds      INPUT_MAX
