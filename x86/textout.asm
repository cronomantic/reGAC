; MIT License, Copyright (c) 2025 Cronomantic
;
; Printing text, breaking it between words: z80/common/textout.asm, rule for
; rule, and what each rule is and where it was measured is written there.
;
; Text comes in a character at a time, through text_put, and goes out a word at
; a time: a word is held until whatever ends it arrives, because only then is
; it known whether it fits on what is left of the line.
;
; This knows nothing about the screen beyond how wide it is and where the
; cursor sits, which screen.asm says.

INK_CODE        equ 1                   ; the next code says which command
INK_ZERO        equ 48                  ; a colour rides as a character
INK_COLOURS     equ 16
HOLE_TURNS      equ 'T'                 ; and a hole as a letter the colours
HOLE_COUNTER    equ 'C'                 ; do not use: see regac/text.py
HOLE_OBJECT     equ 'O'
WORD_ROOM       equ SCREEN_COLS + 1     ; as much of a word as is held
AFTER_SEP       equ 80h                 ; another separator came just before

; Move to the beginning of the next line, unless nothing has been written on
; this one yet.
; Corrupts: everything but DS
start_a_line:
                cmp     byte [cursor_x], 0
                je      .done
                jmp     new_line
.done:
                ret

; Print CX characters from DS:SI, breaking between words.
; Corrupts: everything but DS
print_text:
                jcxz    text_end
                mov     al, [si]
                inc     si
                dec     cx
                push    si
                push    cx
                call    text_put
                pop     cx
                pop     si
                jmp     print_text

; A text has come to its end: the word it was in the middle of goes out, and
; nothing is left waiting for the text after it.
; Corrupts: everything but DS
text_end:
                mov     byte [ink_next], 0
                call    word_out
                jmp     put_held_sep

; One character of a text, in AL.
; Corrupts: everything but DS
text_put:
                cmp     byte [ink_next], 0
                jne     .a_command
                cmp     al, INK_CODE
                je      .ink_coming
                cmp     al, SPACE_CODE
                je      .word_over
                ; a mark of punctuation ends a word as surely as a space does
                call    word_ends_at
                je      .word_over
                ; a letter of the word, kept -- and if there is no room left,
                ; what there is goes out first as a piece of it
                mov     bl, [held_length]
                cmp     bl, WORD_ROOM
                jb      .keep
                push    ax
                call    word_piece
                pop     ax
                xor     bl, bl
.keep:
                xor     bh, bh
                mov     [held_word + bx], al
                inc     bl
                mov     [held_length], bl
                ret
.word_over:
                ; The word goes out, and what ended it is held back rather
                ; than printed, because where the line breaks depends on what
                ; comes after it.  See word_print.
                push    ax
                call    word_out                ; which may take the held one
                call    flush_held_sep          ; and if it did not, out it goes
                pop     ax
                or      [held_sep], al          ; keeping the mark, if any
                ret
.ink_coming:
                mov     byte [ink_next], 1      ; which command, next
                ret
.a_command:
                ; ink_next is 1 for which command it is, 2 and 3 for the two
                ; halves of a hole's number
                cmp     byte [ink_next], 1
                jne     .a_digit
                cmp     al, INK_ZERO + INK_COLOURS
                jae     .a_hole
                mov     byte [ink_next], 0
                ; a change of ink ends a word, and what is held goes out in
                ; the colour it was written in; a hole ends nothing, because
                ; what it prints is part of the word it is in
                push    ax
                call    word_out
                call    put_held_sep
                pop     ax
                sub     al, INK_ZERO
                jmp     text_ink
.a_hole:
                mov     [hole_kind], al
                cmp     al, HOLE_TURNS
                je      .turns
                mov     byte [ink_next], 2      ; its number comes next
                mov     byte [hole_value], 0
                ret
.turns:
                mov     byte [ink_next], 0
                mov     ax, [vm_counters + TURN_COUNTER_LO]     ; and the high
.a_number:
                ; its digits as letters of the word it is in, and not as a
                ; text of their own, which would end the word at every one
                mov     byte [digit_within], 1
                call    print_number
                mov     byte [digit_within], 0
                ret
.a_digit:
                sub     al, INK_ZERO
                mov     cl, 4
                shl     byte [hole_value], cl
                or      [hole_value], al
                cmp     byte [ink_next], 2
                jne     .filled
                mov     byte [ink_next], 3      ; the low half next
                ret
.filled:
                mov     byte [ink_next], 0
                mov     al, [hole_value]
                xor     ah, ah
                cmp     byte [hole_kind], HOLE_COUNTER
                jne     .an_object
                mov     bx, ax
                mov     al, [vm_counters + bx]
                jmp     .a_number
.an_object:
                jmp     print_object_within

; The word held so far goes out: word_out for one that has ended, word_piece
; for one too long to hold that is still going on.
; Corrupts: everything but DS
word_out:
                mov     al, 0
                jmp     word_kept
word_piece:
                mov     al, 1
word_kept:
                push    ax
                call    word_print
                pop     ax
                mov     [held_going_on], al
                ret

; Print what is held of a word, having first asked whether it fits on what is
; left of the line -- unless it is the rest of a word whose first piece has
; already been asked about.
; Corrupts: everything but DS
word_print:
                mov     cl, [held_length]
                test    cl, cl
                jz      .done
                cmp     byte [held_going_on], 0
                jne     .print_it
                ; Where the separator held back goes: one that ends a word
                ; stays where it is and the word goes down alone, while one
                ; out of a run of them goes down with the word.
                test    byte [held_sep], AFTER_SEP
                jnz     .one_came_before
                call    put_held_sep            ; so this one ends a word
.one_came_before:
                ; A word has to end before the last column and not on it, and
                ; one still waiting in front of it takes a column too.
                mov     al, [cursor_x]
                test    byte [held_sep], 7Fh
                jz      .no_sep
                inc     al
.no_sep:
                add     al, [held_length]
                cmp     al, SCREEN_COLS
                jb      .print_it
                cmp     byte [cursor_x], 0
                je      .print_it               ; no point breaking at column 0
                call    new_line
.print_it:
                call    put_held_sep            ; if it is still waiting
                xor     bx, bx
.each:
                push    bx
                mov     al, [held_word + bx]
                call    print_char
                pop     bx
                inc     bx
                cmp     bl, [held_length]
                jb      .each
                mov     byte [held_length], 0
                mov     byte [held_sep], 0      ; what follows a word is alone
.done:
                ret

; What ended the last word goes out at last, wherever the line has ended up,
; and nothing happens if there is none waiting.  What it leaves behind is the
; mark on its own, so that the separator that comes next knows one went before
; it.
; Corrupts: everything but DS
put_held_sep:
                mov     al, [held_sep]
                and     al, AFTER_SEP - 1
                jz      .none
                mov     byte [held_sep], AFTER_SEP
                jmp     print_char
.none:
                ret

; The one held back goes out now, because another separator has come along
; behind it; from the column before last it takes the line with it.
; Corrupts: everything but DS
flush_held_sep:
                mov     al, [held_sep]
                shl     al, 1
                jz      .none
                call    put_held_sep
                cmp     byte [cursor_x], SCREEN_COLS - 1
                jne     .none
                jmp     new_line
.none:
                ret

section .data
held_word:      times WORD_ROOM db 0    ; one word, or a piece of one
held_length:    db      0               ; how much of it is in use
held_sep:       db      0               ; what ended it, not printed yet
held_going_on:  db      0               ; the rest of a word too long to hold
ink_next:       db      0               ; the next code is a command's
hole_kind:      db      0               ; which hole it is
hole_value:     db      0               ; and its number, so far
digit_within:   db      0               ; a digit is a letter of a word
section .text
