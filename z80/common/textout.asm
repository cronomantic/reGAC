; MIT License, Copyright (c) 2025 Cronomantic
;
; Printing text, breaking it between words.
;
; This knows nothing about any screen beyond how wide it is and where the
; cursor sits, both of which the machine's own screen layer names, so every
; machine shares it.
;
; Text comes in a character at a time, through text_put, and goes out a word at
; a time: a word is held until whatever ends it arrives, because only then is
; it known whether it fits on what is left of the line.  That is what lets a
; message be printed while it is still being unpacked, with no more than one
; word in memory at once.  Before, a message was unpacked whole into a buffer of
; 256 bytes and printed afterwards, and one longer than that ran straight off
; the end of the buffer and over the code behind it.  None of the original
; adventures has a text of more than 255 characters, because GAC's editor
; would not let one be typed: its line reader beeps at the 256th (read in the
; Amstrad's, see doc/pendiente.md).  A source of ours can say whatever it
; likes.

; A code that is not a letter but a command to whoever is printing, and the
; code after it says which: a colour, for a change of ink, or a letter for a
; hole -- something only known now, which is printed where it stands: the
; turns, what a counter holds, or the name of an object, the last two with
; their number behind in two codes of four bits.  See regac/text.py.
INK_CODE        equ 1
INK_ZERO        equ 48                  ; the colour rides as a character
INK_COLOURS     equ 16
HOLE_TURNS      equ 'T'
HOLE_COUNTER    equ 'C'
HOLE_OBJECT     equ 'O'

; How much of a word is held.  One more than the line is wide is enough for
; any word at all: one that long does not fit on a line wherever it starts, so
; what happens to it is decided on its first piece exactly as it would be on
; the whole of it -- a new line, unless the cursor is at the start of one --
; and the rest of it only has to be printed.
WORD_ROOM       equ SCREEN_COLS + 1

; In held_sep, the bit that says another separator came just before this one.
; No character of a text carries it, so the two ride in the one byte, and the
; mark on its own means "one has just gone out and nothing is waiting".
AFTER_SEP       equ $80

; Move to the beginning of the next line, unless nothing has been written on
; this one yet.  The original leaves no blank line where a line has just
; filled itself: MegaCorp's rule of thirty two asterisks ends exactly at the
; edge, and its prompt comes on the line straight after it.
; Corrupts: everything
start_a_line:
                ld      a, (cursor_x)
                or      a
                ret     z
                jp      new_line

; Print BC characters from HL, breaking between words so none is split.  A
; word ends at a space, at a mark of punctuation, or at a command.
; Corrupts: everything
print_text:
                ld      a, b
                or      c
                jr      z, text_end
                ld      a, (hl)
                inc     hl
                dec     bc
                push    hl
                push    bc
                call    text_put
                pop     bc
                pop     hl
                jr      print_text

; A text has come to its end: the word it was in the middle of goes out, and
; nothing is left waiting for the text after it.
; Corrupts: everything
text_end:
                xor     a
                ld      (ink_next), a
                call    word_out
                jp      put_held_sep

; One character of a text, in A.
; Corrupts: everything
text_put:
                ld      c, a
                ld      hl, ink_next
                ld      a, (hl)
                or      a
                jr      nz, .a_command
                ld      a, c
                cp      INK_CODE
                jr      z, .ink_coming
                cp      SPACE_CODE
                jr      z, .word_over
                ; A mark of punctuation ends a word as surely as a space
                ; does, which is what the original's text is made of: words
                ; with a terminator of three bits each.  Without this, a
                ; description that runs "Salidas:Sur." followed by a rule of
                ; asterisks is one word of forty four letters and gets broken
                ; wherever the line happens to end, instead of falling into
                ; the three lines its author laid out.
                call    word_ends_at
                jr      z, .word_over
                ; a letter of the word, kept -- and if there is no room left,
                ; what there is goes out first as a piece of it
                ld      a, (held_length)
                cp      WORD_ROOM
                jr      c, .keep
                push    bc
                call    word_piece
                pop     bc
                xor     a
.keep:
                ld      e, a
                ld      d, 0
                inc     a
                ld      (held_length), a
                ld      hl, held_word
                add     hl, de
                ld      (hl), c
                ret
.word_over:
                ; The word goes out, and what ended it is held back rather
                ; than printed, because where the line breaks depends on what
                ; comes after it.  See word_print.
                push    bc
                call    word_out                ; which may take the held one
                call    flush_held_sep          ; and if it did not, out it goes
                pop     bc
                ld      a, c
                ld      hl, held_sep
                or      (hl)                    ; keeping the mark, if any
                ld      (hl), a
                ret
.ink_coming:
                ld      (hl), 1                 ; which command, next
                ret
.a_command:
                ; A = 1 for which command it is, 2 and 3 for the two halves
                ; of a hole's number; HL = ink_next, C = the code.  The holes
                ; travel only in a build whose adventure has one, which regac
                ; says with -DHOLES, by the rule the noises go by.
                IFDEF   HOLES
                dec     a
                jr      nz, .a_digit
                ld      a, c
                cp      INK_ZERO + INK_COLOURS
                jr      nc, .a_hole
                ENDIF
                ld      (hl), 0
                ; A change of ink ends a word, and what is held goes out in
                ; the colour it was written in, not in the one that is coming:
                ; a space between two words of different colours keeps the
                ; first, which is what any machine of this kind does.  A hole
                ; ends nothing: what it prints is part of the word it is in.
                push    bc
                call    word_out
                call    put_held_sep
                pop     bc
                ld      a, c
                sub     INK_ZERO
                jp      text_ink
                IFDEF   HOLES
.a_hole:
                ld      (hole_kind), a
                cp      HOLE_TURNS
                jr      z, .turns
                ld      (hl), 2                 ; its number comes next
                xor     a
                ld      (hole_value), a
                ret
.turns:
                ld      (hl), 0
                ld      hl, (vm_counters + TURN_COUNTER_LO)     ; and the high
.a_number:
                ; its digits as letters of the word it is in, and not as a
                ; text of their own, which would end the word at every one
                ld      a, 1
                ld      (digit_within), a
                call    print_number
                xor     a
                ld      (digit_within), a
                ret
.a_digit:
                ld      b, a                    ; 1 the high half, 2 the low
                ld      a, c
                sub     INK_ZERO
                ld      c, a
                ld      a, (hole_value)
                add     a, a
                add     a, a
                add     a, a
                add     a, a
                or      c
                ld      (hole_value), a
                djnz    .filled
                ld      (hl), 3                 ; the low half next
                ret
.filled:
                ld      (hl), 0
                ld      e, a
                ld      d, 0
                ld      a, (hole_kind)
                cp      HOLE_COUNTER
                jr      nz, .an_object
                ld      hl, vm_counters
                add     hl, de
                ld      l, (hl)
                ld      h, d
                jr      .a_number
.an_object:
                ex      de, hl
                jp      print_object_within
                ENDIF

; The word held so far goes out: word_out for one that has ended, word_piece
; for one too long to hold that is still going on.
; Corrupts: everything
word_out:
                xor     a
                jr      word_kept
word_piece:
                ld      a, 1
word_kept:
                push    af
                call    word_print
                pop     af
                ld      (held_going_on), a
                ret

; Print what is held of a word, having first asked whether it fits on what is
; left of the line -- unless it is the rest of a word whose first piece has
; already been asked about.
; Corrupts: everything
word_print:
                ld      a, (held_length)
                or      a
                ret     z
                ld      e, a
                ld      a, (held_going_on)
                or      a
                jr      nz, .print_it
                ; Where the separator held back goes.  The original asks
                ; its question after printing a separator, so the break falls
                ; behind it -- unless another separator came just before, in
                ; which case that earlier one asked first and got the same
                ; answer, and the break falls in front.  So one that ends a
                ; word stays where it is and the word goes down alone, while
                ; one out of a run of them goes down with the word and shows
                ; at the head of the line.  That is what centres text in the
                ; original.
                ld      a, (held_sep)
                add     a, a                    ; carry says one came before
                push    de
                call    nc, put_held_sep        ; so this one ends a word
                pop     de
                ; A word has to end before the last column and not on it, and
                ; one still waiting in front of it takes a column too: the
                ; original leaves that last one empty.  Found by playing
                ; MegaCorp on both at once -- its street in Nyhmir has a
                ; "razas" that ends exactly at the edge, and the original puts
                ; it on the next line while this kept it.
                ld      a, (held_sep)
                add     a, a                    ; zero when none is waiting
                ld      a, (cursor_x)
                jr      z, .no_sep
                inc     a
.no_sep:
                add     a, e
                cp      SCREEN_COLS
                jr      c, .print_it
                ld      a, (cursor_x)
                or      a
                jr      z, .print_it            ; no point breaking at column 0
                push    de
                call    new_line                ; this treads on every register
                pop     de
.print_it:
                push    de
                call    put_held_sep            ; if it is still waiting
                pop     de
                ld      hl, held_word
.each:
                ld      a, (hl)
                inc     hl
                push    hl
                push    de
                call    print_char
                pop     de
                pop     hl
                dec     e
                jr      nz, .each
                xor     a
                ld      (held_length), a
                ld      (held_sep), a           ; what follows a word is alone
                ret

; What ended the last word goes out at last, wherever the line has ended up,
; and nothing happens if there is none waiting.  What it leaves behind is the
; mark on its own, so that the separator that comes next knows one went before
; it, which is what tells a space out of a run from a space that ends a word.
; Corrupts: everything
put_held_sep:
                ld      a, (held_sep)
                and     AFTER_SEP - 1
                ret     z
                ld      hl, held_sep
                ld      (hl), AFTER_SEP
                jp      print_char

; The one held back goes out now, because another separator has come along
; behind it.  What the original asks of it comes to "does anything at all fit
; after me", because it measures the stretch that begins one character further
; on, so from the column before last it takes the line with it.
; Corrupts: everything
flush_held_sep:
                ld      a, (held_sep)
                add     a, a
                ret     z
                call    put_held_sep
                ld      a, (cursor_x)
                cp      SCREEN_COLS - 1
                ret     nz
                jp      new_line

held_word:      ds      WORD_ROOM               ; one word, or a piece of one
held_length:    db      0               ; how much of it is in use
held_sep:       db      0               ; what ended it, not printed yet
held_going_on:  db      0               ; the rest of a word too long to hold
ink_next:       db      0               ; the next code is a command's
hole_kind:      db      0               ; which hole it is
hole_value:     db      0               ; and its number, so far
digit_within:   db      0               ; a digit is a letter of a word
