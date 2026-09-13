; MIT License, Copyright (c) 2025 Cronomantic
;
; Making sense of what the player typed.
;
; A line is cut into sentences wherever a separator or a mark of punctuation
; appears, so "COGE LA LLAVE Y ABRE LA PUERTA" is two orders and they are
; obeyed one after the other.  Each sentence is then cut into words and each
; word is looked for in the vocabulary.
;
; It is enough to type the start of a word, which is what the original does:
; typing EX at MegaCorp makes it ask what to examine, and typing EXAMINAR, one
; letter more than the word it holds, makes it say it does not understand.  So
; a typed word matches an entry it is the start of, and never one shorter than
; itself.  The price is that LA is swallowed by LAMPARA, and the original pays
; it too.
;
; Our vocabulary is kept in alphabetical order, so of the entries a short word
; starts, the shortest wins: typing LA where both LA and LAMPARA exist finds
; LA.
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

; The next order on the line, in HL with its length in BC.
;
; A line may hold more than one order.  The original parted them at a mark of
; punctuation: typing "XYZY.SUR" at it makes it answer that it does not know
; the first word and then walk south.  An adventure may also name words that
; part two orders, which the original never did; those are honoured here, for
; adventures written from now on, and an adventure that names none behaves
; exactly as the original.
; Corrupts: everything
next_statement:
                ld      hl, (line_at)
                ld      (stmt_start), hl
                ld      hl, 0
                ld      (stmt_len), hl
                xor     a
                ld      (word_len), a
.each:
                ld      hl, (line_left)
                ld      a, h
                or      l
                jr      z, .line_ended
                ld      hl, (line_at)
                ld      c, (hl)
                ld      a, c
                call    ends_statement
                jr      z, .a_mark
                ld      a, (space_code)
                cp      c
                jr      z, .a_space
                ld      hl, word_len            ; it belongs to the word
                inc     (hl)
                call    .keep
                jr      .each
.a_space:
                call    .parting_word
                jr      c, .cut_before_word
                xor     a
                ld      (word_len), a
                call    .keep
                jr      .each
.a_mark:
                call    .step                   ; the mark belongs to neither
                jr      .done
.line_ended:
                call    .parting_word
                jr      c, .cut_before_word
                jr      .done
.cut_before_word:
                ld      a, (word_len)           ; the order ends before it
                ld      c, a
                ld      b, 0
                ld      hl, (stmt_len)
                or      a
                sbc     hl, bc
                ld      (stmt_len), hl
.done:
                ld      bc, (stmt_len)
                ld      hl, (stmt_start)
                ret

; Whether the word that has just ended parts two orders.  Carry set when it
; does.
.parting_word:
                ld      a, (word_len)
                or      a
                ret     z
                ld      c, a
                ld      b, 0
                ld      hl, (line_at)
                or      a
                sbc     hl, bc                  ; where the word began
                ld      b, c
                jp      separator_find

; One character further along, and it counts towards this order.
.keep:
                ld      hl, (stmt_len)
                inc     hl
                ld      (stmt_len), hl
                ; and on along the line
.step:
                ld      hl, (line_at)
                inc     hl
                ld      (line_at), hl
                ld      hl, (line_left)
                dec     hl
                ld      (line_left), hl
                ret

; Whether the word of B codes at HL is one the adventure names as parting two
; orders.  Carry set when it is.
; Corrupts: everything
separator_find:
                ld      (sep_word), hl
                ld      a, b
                ld      (sep_length), a
                ld      hl, (seps_at)
                ld      a, (hl)
                inc     hl
                or      a
                ret     z                       ; the adventure names none
                ld      (seps_left), a
.each:
                ld      c, (hl)                 ; how long this one is
                inc     hl
                ld      a, (sep_length)
                cp      c
                jr      nz, .skip
                push    hl
                ld      de, (sep_word)
                ld      b, c
.compare:
                ld      a, (de)
                cp      (hl)
                jr      nz, .no
                inc     hl
                inc     de
                djnz    .compare
                pop     hl
                scf
                ret
.no:
                pop     hl
.skip:
                ld      b, 0
                add     hl, bc                  ; past this word's codes
                push    hl
                ld      hl, seps_left
                dec     (hl)
                pop     hl
                jr      nz, .each
                or      a
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
                jr      z, .long_enough
                jr      nc, .next               ; more typed than the word holds
.long_enough:
                ld      b, a
                or      a
                jr      z, .next
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
line_at:        dw      0                       ; what is left of the line
line_left:      dw      0
stmt_start:     dw      0
stmt_len:       dw      0
word_len:       db      0
sep_word:       dw      0
sep_length:     db      0
seps_left:      db      0

parse_left:     dw      0
word_length:    db      0
vm_old_noun:    db      0
