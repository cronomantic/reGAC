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

; A code that is not a letter but a command to whoever is printing: the one
; there is says the ink changes, and the code after it says to what.  See
; doc/textos.md.
INK_CODE        equ 1
INK_ZERO        equ 48                  ; the colour rides as a character

; How much of a word is held.  One more than the line is wide is enough for
; any word at all: one that long does not fit on a line wherever it starts, so
; what happens to it is decided on its first piece exactly as it would be on
; the whole of it -- a new line, unless the cursor is at the start of one --
; and the rest of it only has to be printed.
WORD_ROOM       equ SCREEN_COLS + 1

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
                jr      word_out

; One character of a text, in A.
; Corrupts: everything
text_put:
                ld      c, a
                ld      hl, ink_next
                ld      a, (hl)
                or      a
                jr      nz, .an_ink
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
                ; the word goes out, and then what ended it, printed where it
                ; falls without asking whether it fits
                push    bc
                call    word_out
                pop     bc
                ld      a, c
                jp      print_char
.ink_coming:
                ; a command ends a word too, and its colour is the code after
                call    word_out
                ld      a, 1
                ld      (ink_next), a
                ret
.an_ink:
                ld      (hl), 0
                ld      a, c
                sub     INK_ZERO
                jp      text_ink

; The word held so far goes out: word_out for one that has ended, word_piece
; for one too long to hold that is still going on.
; Corrupts: everything
word_out:
                call    word_print
                xor     a
                ld      (held_going_on), a
                ret

word_piece:
                call    word_print
                ld      a, 1
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
                ld      a, (cursor_x)
                add     a, e
                cp      SCREEN_COLS + 1
                jr      c, .print_it
                ld      a, (cursor_x)
                or      a
                jr      z, .print_it            ; no point breaking at column 0
                push    de
                call    new_line                ; this treads on every register
                pop     de
.print_it:
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
                ret

held_word:      ds      WORD_ROOM               ; one word, or a piece of one
held_length:    db      0               ; how much of it is in use
held_going_on:  db      0               ; the rest of a word too long to hold
ink_next:       db      0               ; the next code is a colour
