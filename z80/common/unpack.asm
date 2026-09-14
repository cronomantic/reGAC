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
; the interpreter print message 137 and only that one.

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

; Unpack message DE into text_buffer.  Its length comes back in BC.
; Corrupts: AF, DE, HL
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
                ld      de, text_buffer
.next:
                ld      a, b
                or      c
                jr      z, .done
                dec     bc
                ld      a, (hl)
                inc     hl
                push    hl
                push    bc
                call    expand_code
                pop     bc
                pop     hl
                jr      .next
.done:
                ld      hl, text_buffer
                ex      de, hl
                or      a
                sbc     hl, de                  ; HL = characters written
                ld      b, h
                ld      c, l
                ret

; Expand one code.  A is the code, DE points at the output and is advanced.
; Calls itself for the left half of a pair, which is what gives the stack.
; Corrupts: AF, BC, HL
expand_code:
                ld      hl, first_pair
                cp      (hl)
                jr      nc, .pair
                ld      (de), a                 ; a character: write it out
                inc     de
                ret
.pair:
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
text_buffer:    ds      256


; The place in the store of message number A, in DE.  Carry set if there is no
; such message.
; Corrupts: AF, HL
message_index:
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
