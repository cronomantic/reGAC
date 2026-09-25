; MIT License, Copyright (c) 2025 Cronomantic
;
; Unpacking a message.  See doc/textos.md.
;
; A code below the first pair is a character; anything else stands for two
; codes, and those may stand for two more.  Walking that needs a stack, so the
; machine's own is used by letting the routine call itself: the deepest any of
; the eight adventures went was ten levels, which is forty bytes.
;
; A message unpacks on its own, touching nothing before it, which is what lets
; the interpreter print message 137 and only that one.  And it is printed as it
; unpacks: every character goes to the printer the moment it comes out, and the
; printer holds a word at most, so nothing the length of a message is ever kept
; in memory.  See textout.asm for why that matters.

; Read the text section header and remember where its parts are.
; Corrupts: AF, BC, DE, HL
text_init:
                ld      a, SECTION_TEXT
                call    db_section              ; HL = section start
                ld      a, (hl)
                ld      (first_pair), a
                inc     hl
                ld      a, (hl)
                ld      (pair_count), a
                inc     hl
                ld      (pair_table), hl
                ; the message count sits after the pair table
                ld      e, a
                ld      d, 0
                sla     e
                rl      d                       ; two bytes a pair
                add     hl, de
                ld      (message_lookup), hl    ; message number -> its place
                ld      de, 256
                add     hl, de
                ld      e, (hl)
                inc     hl
                ld      d, (hl)
                inc     hl
                ld      (message_count), de
                ld      (offset_table), hl
                ; then the offsets, then the length of the packed bytes
                ex      de, hl
                add     hl, hl                  ; two bytes a message
                ex      de, hl
                add     hl, de
                ld      e, (hl)
                inc     hl
                ld      d, (hl)
                inc     hl
                ld      (data_size), de
                ld      (message_data), hl
                ret

; Where message DE starts, in HL.  Reading one past the last message gives the
; length of the packed bytes, which is what makes the end of a message easy.
; Corrupts: AF, DE
message_offset:
                ld      hl, (message_count)
                or      a
                sbc     hl, de
                jr      nz, .from_table
                ld      hl, (data_size)         ; one past the last
                ret
.from_table:
                ld      hl, (offset_table)
                sla     e
                rl      d
                add     hl, de
                ld      e, (hl)
                inc     hl
                ld      d, (hl)
                ex      de, hl
                ret

; Print message DE, unpacking it as it goes.
;
; **A change of ink lasts to the end of the message it is in**, and that is
; what the last two lines of this do.  It used to last until the next one,
; which meant for ever: a message that turned the text red and did not turn
; it back left the description of the next room red, and the prompt, and what
; the parser says when it does not understand -- damage that shows up a long
; way from the line that caused it, and that the author cannot see while
; writing that line.  What is given up is painting across several messages,
; which in GAC is worth little: the unit an author writes is the message.
; Corrupts: everything
print_packed:
                call    unpack_message
                call    text_end                ; the last word goes out
                ld      a, (text_ink_start)     ; and the ink goes back
                jp      text_ink

; Unpack message DE into the printer, and nothing else: the word it ends in
; is left open and the ink as it is.  That is what a hole needs that prints
; an object's name inside another text: "\obj 3." is one word.
; Corrupts: everything
unpack_message:
                ld      a, SECTION_TEXT         ; where the machine keeps it,
                call    db_bank_in              ; which may be a bank
                push    de
                call    message_offset
                push    hl                      ; where it starts
                pop     bc
                pop     de
                inc     de
                push    bc
                call    message_offset          ; where the next one starts
                pop     bc
                or      a
                sbc     hl, bc                  ; HL = how many packed bytes
                ld      d, h
                ld      e, l
                ld      hl, (message_data)
                add     hl, bc                  ; HL = the packed bytes
                ld      b, d
                ld      c, e                    ; BC = how many
.next:
                ld      a, b
                or      c
                jr      z, .ended
                dec     bc
                ld      a, (hl)
                inc     hl
                push    hl
                push    bc
                call    expand_code
                pop     bc
                pop     hl
                jr      .next
.ended:
                ret

; Expand one code, A, and print what it stands for.  Calls itself for the left
; half of a pair, which is what gives the stack, and nothing it keeps across
; the call is anything the printer could tread on.
; Corrupts: everything
expand_code:
                ld      hl, first_pair
                cp      (hl)
                jp      c, text_put             ; a character: print it
                sub     (hl)                    ; which pair
                ld      l, a
                ld      h, 0
                add     hl, hl                  ; two bytes an entry
                ld      bc, (pair_table)
                add     hl, bc
                ld      a, (hl)                 ; the left half
                inc     hl
                ld      b, (hl)                 ; the right half
                push    bc
                call    expand_code             ; left first, so order holds
                pop     bc
                ld      a, b
                jr      expand_code             ; then right, as a tail call

pair_table:     dw      0
message_lookup: dw      0
offset_table:   dw      0
message_data:   dw      0
message_count:  dw      0
data_size:      dw      0
first_pair:     db      0
pair_count:     db      0


; The place in the store of message number A, in DE.  Carry set if there is no
; such message.
;
; The lookup it reads lives in the text, which on a machine with banks is one
; of them, so the bank goes in first.  It used to trust whoever had gone
; before -- which was the room's description, and worked only because that
; always came first.  The day the high priority conditions moved ahead of the
; description, the opening message of a banked adventure came out of whatever
; bank happened to be in the window: Bangkok, which says who wrote it before
; anything else, said a line about a waiter instead.
; Corrupts: AF, HL
message_index:
                push    de
                ld      d, a                    ; the message, while paging
                ld      a, SECTION_TEXT
                call    db_bank_in
                ld      a, d
                pop     de
                ld      hl, (message_lookup)
                ld      e, a
                ld      d, 0
                add     hl, de
                ld      a, (hl)
                cp      NO_MESSAGE
                scf
                ret     z
                ld      e, a
                ld      d, 0
                or      a
                ret
