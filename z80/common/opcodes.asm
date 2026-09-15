; MIT License, Copyright (c) 2025 Cronomantic
;
; The opcodes themselves, and the table that reaches them.  The numbering is
; the original's, kept because it was compact and there was no reason to
; change it; regac/opcodes.py is the same list on the other side.

OP_END          equ $3F

; -- small helpers -----------------------------------------------------------

; Flag L: its byte in HL, its bit as a mask in A.
; Corrupts: BC, DE
flag_address:
                ld      a, l
                and     7
                ld      b, a
                inc     b
                ld      a, 1
.shift:
                dec     b
                jr      z, .ready
                add     a, a
                jr      .shift
.ready:
                ld      c, a
                ld      a, l
                rrca
                rrca
                rrca
                and     $1F
                ld      l, a
                ld      h, 0
                ld      de, vm_flags
                add     hl, de
                ld      a, c
                ret

; Counter L: its address in HL.  Carry set if there is no such counter.
counter_address:
                ld      a, l
                cp      COUNTERS
                ccf
                ret     c
                ld      h, 0
                ld      de, vm_counters
                add     hl, de
                or      a
                ret

; Print the name of object L.
; Corrupts: everything
print_object_name:
                call    obj_record
                ret     c
                ld      de, 4
                add     hl, de
                ld      e, (hl)
                inc     hl
                ld      d, (hl)                 ; where its name is in the store
                call    unpack_message
                ld      hl, text_buffer
                call    print_text
                jp      new_line

; Describe location HL.
; Corrupts: everything
describe_location:
                call    obj_find_location
                ret     c
                push    hl
                inc     hl
                inc     hl
                ld      e, (hl)
                inc     hl
                ld      d, (hl)                 ; the picture this room shows
                ld      a, d
                or      e
                jr      z, .no_picture          ; a room may have none
                ex      de, hl
                call    draw_picture
.no_picture:
                pop     hl
                ld      de, 4
                add     hl, de
                ld      e, (hl)
                inc     hl
                ld      d, (hl)                 ; where the description is
                call    unpack_message
                ld      hl, text_buffer
                call    print_text
                jp      new_line

; Print HL as a decimal number, without leading zeros.
; Corrupts: everything
print_number:
                ld      ix, print_powers
                ld      c, 0                    ; nothing shown yet
                ld      b, 5
.each:
                ld      e, (ix+0)
                ld      d, (ix+1)
                inc     ix
                inc     ix
                ld      a, 0
.subtract:
                or      a
                sbc     hl, de
                jr      c, .undo
                inc     a
                jr      .subtract
.undo:
                add     hl, de
                or      a
                jr      nz, .show               ; a digit worth showing
                ld      a, c
                or      a
                jr      nz, .show_zero          ; something came before it
                ld      a, b
                dec     a
                jr      nz, .skip               ; a leading zero, leave it out
.show_zero:
                xor     a
.show:
                push    bc
                push    hl
                push    ix
                call    print_digit
                pop     ix
                pop     hl
                pop     bc
                ld      c, 1
.skip:
                djnz    .each
                ret

print_powers:   dw      10000, 1000, 100, 10, 1

; Print the digit in A, zero to nine, through the adventure's character set.
; Corrupts: everything
print_digit:
                add     a, DIGIT_ZERO           ; a code is its own ASCII here
                ld      (digit_char), a
                ld      hl, digit_char
                ld      bc, 1
                jp      print_text

digit_char:     db      0

; -- the opcodes -------------------------------------------------------------

op_and:
                call    vm_pop
                ld      d, h
                ld      e, l
                call    vm_pop
                ld      a, l
                and     e
                ld      l, a
                ld      a, h
                and     d
                ld      h, a
                call    vm_push
                jp      vm_loop

op_or:
                call    vm_pop
                ld      d, h
                ld      e, l
                call    vm_pop
                ld      a, l
                or      e
                ld      l, a
                ld      a, h
                or      d
                ld      h, a
                call    vm_push
                jp      vm_loop

op_xor:
                call    vm_pop
                ld      d, h
                ld      e, l
                call    vm_pop
                ld      a, l
                xor     e
                ld      l, a
                ld      a, h
                xor     d
                ld      h, a
                call    vm_push
                jp      vm_loop

op_not:
                call    vm_pop
                ld      a, h
                or      l
                jp      z, .was_zero
                call    vm_push_false
                jp      vm_loop
.was_zero:
                call    vm_push_true
                jp      vm_loop

; HOLD n: hold everything for n fiftieths of a second, or until the player
; presses something, whichever comes first.
op_hold:
                call    vm_pop
                call    wait_or_key
                jp      vm_loop

op_get:
                call    vm_pop
                ld      (vm_arg), hl
                call    obj_location            ; DE = where it is
                jp      c, vm_loop
                ld      hl, (vm_location)
                or      a
                sbc     hl, de
                jr      nz, .not_here
                ld      hl, (vm_arg)
                ld      de, CARRIED
                call    obj_move
                jp      vm_loop
.not_here:
                ld      a, MSG_CANTSEE
                call    print_message
                jp      vm_loop

op_drop:
                call    vm_pop
                ld      (vm_arg), hl
                call    obj_location
                jp      c, vm_loop
                ld      hl, CARRIED
                or      a
                sbc     hl, de
                jr      nz, .not_carried
                ld      hl, (vm_arg)
                ld      de, (vm_location)
                call    obj_move
                jp      vm_loop
.not_carried:
                ld      a, MSG_DONTHAVE
                call    print_message
                jp      vm_loop

op_swap:
                call    vm_pop
                ld      (vm_arg), hl            ; the second object
                call    vm_pop
                ld      (vm_arg2), hl
                ld      hl, (vm_arg)
                call    obj_location
                jp      c, vm_loop
                push    de
                ld      hl, (vm_arg2)
                call    obj_location
                pop     bc
                jp      c, vm_loop
                push    de
                ld      hl, (vm_arg)
                ld      d, b
                ld      e, c
                call    obj_move
                pop     de
                ld      hl, (vm_arg2)
                call    obj_move
                jp      vm_loop

op_to:
                call    vm_pop
                ex      de, hl                  ; DE = where to
                call    vm_pop                  ; HL = which object
                call    obj_move
                jp      vm_loop

op_obj:
                call    vm_pop
                call    print_object_name
                jp      vm_loop

op_set:
                call    vm_pop
                call    flag_address
                or      (hl)
                ld      (hl), a
                jp      vm_loop

op_reset:
                call    vm_pop
                call    flag_address
                cpl
                and     (hl)
                ld      (hl), a
                jp      vm_loop

op_set_q:
                call    vm_pop
                call    flag_address
                and     (hl)
                jr      z, .clear
                call    vm_push_true
                jp      vm_loop
.clear:
                call    vm_push_false
                jp      vm_loop

op_reset_q:
                call    vm_pop
                call    flag_address
                and     (hl)
                jr      z, .clear
                call    vm_push_false
                jp      vm_loop
.clear:
                call    vm_push_true
                jp      vm_loop

op_cset:
                call    vm_pop                  ; which counter
                push    hl
                call    vm_pop                  ; the value
                ld      a, l
                pop     hl
                push    af
                call    counter_address
                pop     af
                jp      c, vm_loop
                ld      (hl), a
                jp      vm_loop

op_ctr:
                call    vm_pop
                call    counter_address
                jr      c, .none
                ld      l, (hl)
                ld      h, 0
                call    vm_push
                jp      vm_loop
.none:
                call    vm_push_false
                jp      vm_loop

op_decr:
                call    vm_pop
                call    counter_address
                jp      c, vm_loop
                ld      a, (hl)
                or      a
                jp      z, vm_loop              ; it stops at zero
                dec     (hl)
                jp      vm_loop

op_incr:
                call    vm_pop
                call    counter_address
                jp      c, vm_loop
                ld      a, (hl)
                inc     a
                jp      z, vm_loop              ; and at 255
                ld      (hl), a
                jp      vm_loop

op_equ_q:
                call    vm_pop                  ; which counter
                call    counter_address
                jr      c, .no
                ld      e, (hl)
                ld      d, 0
                call    vm_pop                  ; the value to compare
                or      a
                sbc     hl, de
                jr      nz, .no
                call    vm_push_true
                jp      vm_loop
.no:
                call    vm_pop
                call    vm_push_false
                jp      vm_loop

op_desc:
                call    vm_pop
                call    describe_location
                jp      vm_loop

op_look:
                ld      hl, (vm_location)
                call    describe_location
                jp      vm_loop

op_mess:
                call    vm_pop
                ld      a, l
                call    print_message
                jp      vm_loop

op_prin:
                call    vm_pop
                call    print_number
                jp      vm_loop

op_rand:
                call    vm_pop
                ld      b, l                    ; the limit
                push    bc
                call    next_random
                pop     bc
                ld      a, b
                or      a
                jr      z, .zero
                ld      a, l
.reduce:
                cp      b
                jr      c, .done
                sub     b
                jr      .reduce
.done:
                ld      l, a
                ld      h, 0
                call    vm_push
                jp      vm_loop
.zero:
                call    vm_push_false
                jp      vm_loop

op_less:
                call    vm_pop
                ld      d, h
                ld      e, l                    ; the right hand side
                call    vm_pop
                or      a
                sbc     hl, de
                jr      c, .yes
                call    vm_push_false
                jp      vm_loop
.yes:
                call    vm_push_true
                jp      vm_loop

op_greater:
                call    vm_pop
                ld      d, h
                ld      e, l
                call    vm_pop
                ex      de, hl
                or      a
                sbc     hl, de
                jr      c, .yes
                call    vm_push_false
                jp      vm_loop
.yes:
                call    vm_push_true
                jp      vm_loop

op_equal:
                call    vm_pop
                ld      d, h
                ld      e, l
                call    vm_pop
                or      a
                sbc     hl, de
                jr      z, .yes
                call    vm_push_false
                jp      vm_loop
.yes:
                call    vm_push_true
                jp      vm_loop

; SAVE and LOAD: the game, not the adventure, on one block of tape.  A load
; that goes wrong leaves what was there alone, because the ROM only writes
; what it reads and the player can try again.
op_save:
                ld      ix, vm_state
                ld      de, vm_state_end - vm_state
                call    tape_save
                jp      vm_loop
op_load:
                ld      ix, vm_state
                ld      de, vm_state_end - vm_state
                call    tape_load
                ld      a, 1
                ld      (vm_new_room), a        ; wherever we are now, say so
                jp      vm_loop

op_here:
                call    vm_pop
                ld      (vm_arg), hl
                call    obj_location
                jr      c, .no
                ld      hl, (vm_location)
                or      a
                sbc     hl, de
                jr      nz, .no
                call    vm_push_true
                jp      vm_loop
.no:
                call    vm_push_false
                jp      vm_loop

op_carr:
                call    vm_pop
                ld      (vm_arg), hl
                call    obj_location
                jr      c, .no
                ld      hl, CARRIED
                or      a
                sbc     hl, de
                jr      nz, .no
                call    vm_push_true
                jp      vm_loop
.no:
                call    vm_push_false
                jp      vm_loop

op_avai:
                call    vm_pop
                ld      (vm_arg), hl
                call    obj_location
                jr      c, .no
                ld      hl, CARRIED
                or      a
                sbc     hl, de
                jr      z, .yes
                ld      hl, (vm_location)
                or      a
                sbc     hl, de
                jr      z, .yes
.no:
                call    vm_push_false
                jp      vm_loop
.yes:
                call    vm_push_true
                jp      vm_loop

op_add:
                call    vm_pop
                ld      d, h
                ld      e, l
                call    vm_pop
                add     hl, de
                call    vm_push
                jp      vm_loop

op_sub:
                call    vm_pop
                ld      d, h
                ld      e, l
                call    vm_pop
                or      a
                sbc     hl, de
                call    vm_push
                jp      vm_loop

op_turn:
                ld      a, (vm_counters + TURN_COUNTER_HI)
                ld      h, a
                ld      a, (vm_counters + TURN_COUNTER_LO)
                ld      l, a
                call    vm_push
                jp      vm_loop

op_at:
                call    vm_pop
                ld      de, (vm_location)
                or      a
                sbc     hl, de
                jr      z, .yes
                call    vm_push_false
                jp      vm_loop
.yes:
                call    vm_push_true
                jp      vm_loop

op_brin:
                call    vm_pop
                ld      de, (vm_location)
                call    obj_move
                jp      vm_loop

op_find:
                call    vm_pop
                ld      (vm_arg), hl
                call    obj_location
                jp      c, vm_loop
                ld      a, d
                or      e
                jp      z, vm_loop              ; nowhere to go
                ld      hl, CARRIED
                or      a
                sbc     hl, de
                jp      z, vm_loop              ; already with you
                ld      (vm_location), de
                ld      a, 1
                ld      (vm_new_room), a
                jp      vm_loop

op_in:
                call    vm_pop
                push    hl                      ; the room
                call    vm_pop
                ld      (vm_arg), hl
                call    obj_location
                pop     hl
                jr      c, .no
                or      a
                sbc     hl, de
                jr      nz, .no
                call    vm_push_true
                jp      vm_loop
.no:
                call    vm_push_false
                jp      vm_loop

op_nop:
                jp      vm_loop

op_okay:
                ld      a, MSG_OKAY
                call    print_message
                ld      a, 1
                ld      (vm_done), a
                jp      vm_loop

op_wait:
                ld      a, 1
                ld      (vm_done), a
                jp      vm_loop

; QUIT asks first and only stops if the answer is yes; EXIT just stops.
op_quit:
                ld      a, MSG_YOUSURE
                call    print_message
                call    read_line               ; HL = the codes, BC = how many
                call    said_yes
                jp      nc, vm_loop
op_exit:
                ld      a, 1
                ld      (vm_over), a
                ld      (vm_done), a
                jp      vm_loop

; Whether the line at HL, BC characters of it, says yes.  The words are kept
; in plain letters and turned into this adventure's own codes as they are
; compared, because that is what was typed into the buffer.
; Carry set when it does.
; Corrupts: everything
said_yes:
                ld      a, b
                or      a
                ret     nz                      ; nothing that long is a yes
                ld      a, c
                or      a
                ret     z
                ld      (yes_length), a
                ld      (yes_line), hl
                ld      ix, yes_words
.each_word:
                ld      a, (ix+0)
                or      a
                ret     z                       ; none of them matched
                ld      c, a
                ld      a, (yes_length)
                cp      c
                jr      nz, .next
                push    ix
                ld      de, (yes_line)
                ld      b, c
                inc     ix
.each_letter:
                ld      a, (ix+0)
                call    ascii_to_code
                ld      c, a
                ld      a, (de)
                cp      c
                jr      nz, .no_match
                inc     ix
                inc     de
                djnz    .each_letter
                pop     ix
                scf
                ret
.no_match:
                pop     ix
.next:
                ld      c, (ix+0)
                ld      b, 0
                inc     ix
                add     ix, bc                  ; on past this one
                jr      .each_word

yes_words:      db      1, "S"
                db      2, "SI"
                db      1, "Y"
                db      3, "YES"
                db      0
yes_length:     db      0
yes_line:       dw      0

op_room:
                ld      hl, (vm_location)
                call    vm_push
                jp      vm_loop

op_noun:
                call    vm_pop
                ld      a, (vm_noun1)
                cp      l
                jr      z, .yes
                call    vm_push_false
                jp      vm_loop
.yes:
                call    vm_push_true
                jp      vm_loop

op_verb:
                call    vm_pop
                ld      a, (vm_verb)
                cp      l
                jr      z, .yes
                call    vm_push_false
                jp      vm_loop
.yes:
                call    vm_push_true
                jp      vm_loop

op_adve:
                call    vm_pop
                ld      a, (vm_adverb)
                cp      l
                jr      z, .yes
                call    vm_push_false
                jp      vm_loop
.yes:
                call    vm_push_true
                jp      vm_loop

op_goto:
                call    vm_pop
                ld      (vm_location), hl
                ld      a, 1
                ld      (vm_new_room), a
                jp      vm_loop

op_no1:
                ld      a, (vm_noun1)
                ld      l, a
                ld      h, 0
                call    vm_push
                jp      vm_loop

op_no2:
                ld      a, (vm_noun2)
                ld      l, a
                ld      h, 0
                call    vm_push
                jp      vm_loop

op_vbno:
                ld      a, (vm_verb)
                ld      l, a
                ld      h, 0
                call    vm_push
                jp      vm_loop

op_list:
                call    vm_pop
                ld      (vm_arg2), hl           ; the room to list
                ld      b, 255
                ld      c, 1                    ; object numbers start at one
.each:
                push    bc
                ld      l, c
                ld      (vm_arg), hl
                call    obj_location
                jr      c, .next
                ld      hl, (vm_arg2)
                or      a
                sbc     hl, de
                jr      nz, .next
                ld      hl, (vm_arg)
                call    print_object_name
.next:
                pop     bc
                inc     c
                djnz    .each
                jp      vm_loop

op_pict:
                ld      a, 1
                ld      (vm_graphics), a
                jp      vm_loop

op_text:
                xor     a
                ld      (vm_graphics), a
                jp      vm_loop

op_conn:
                call    vm_pop
                ld      a, l
                ld      (vm_arg), a             ; which way
                ld      hl, (vm_location)
                call    obj_find_location
                jr      c, .none
                ld      de, 6
                add     hl, de
                ld      b, (hl)                 ; how many exits
                inc     hl
                ld      a, b
                or      a
                jr      z, .none
.each:
                ld      a, (vm_arg)
                cp      (hl)
                jr      z, .found
                inc     hl
                inc     hl
                inc     hl
                djnz    .each
                jr      .none
.found:
                inc     hl
                ld      e, (hl)
                inc     hl
                ld      d, (hl)
                ex      de, hl
                call    vm_push
                jp      vm_loop
.none:
                call    vm_push_false
                jp      vm_loop

op_weig:
                call    vm_pop
                call    obj_record
                jr      c, .none
                inc     hl
                ld      l, (hl)
                ld      h, 0
                call    vm_push
                jp      vm_loop
.none:
                call    vm_push_false
                jp      vm_loop

op_with:
                ld      hl, CARRIED
                call    vm_push
                jp      vm_loop

op_stre:
                call    vm_pop
                ld      a, l
                ld      (vm_max_weight), a
                jp      vm_loop

op_lf:
                call    new_line
                jp      vm_loop

op_if:
                call    vm_pop
                ld      a, h
                or      l
                jr      nz, .true
                ld      a, 1
                ld      (vm_skip), a
                jp      vm_loop
.true:
                ld      a, 1
                ld      (vm_if_true), a         ; something took the order
                jp      vm_loop

op_end:
                xor     a
                ld      (vm_skip), a
                call    vm_reset_stack
                jp      vm_loop

; A number nobody will call it random, but good enough to pick a message.
next_random:
                ld      hl, (vm_seed)
                ld      a, h
                rra
                ld      a, l
                rra
                xor     h
                ld      h, a
                ld      a, l
                rra
                ld      a, h
                rra
                xor     l
                ld      l, a
                xor     h
                ld      h, a
                ld      (vm_seed), hl
                ret

vm_arg2:        dw      0

; -- where each opcode lives -------------------------------------------------

vm_table:
                dw      op_and          ; $01
                dw      op_or           ; $02
                dw      op_not          ; $03
                dw      op_xor          ; $04
                dw      op_hold         ; $05
                dw      op_get          ; $06
                dw      op_drop         ; $07
                dw      op_swap         ; $08
                dw      op_to           ; $09
                dw      op_obj          ; $0A
                dw      op_set          ; $0B
                dw      op_reset        ; $0C
                dw      op_set_q        ; $0D
                dw      op_reset_q      ; $0E
                dw      op_cset         ; $0F
                dw      op_ctr          ; $10
                dw      op_decr         ; $11
                dw      op_incr         ; $12
                dw      op_equ_q        ; $13
                dw      op_desc         ; $14
                dw      op_look         ; $15
                dw      op_mess         ; $16
                dw      op_prin         ; $17
                dw      op_rand         ; $18
                dw      op_less         ; $19
                dw      op_greater      ; $1A
                dw      op_equal        ; $1B
                dw      op_save         ; $1C
                dw      op_load         ; $1D
                dw      op_here         ; $1E
                dw      op_carr         ; $1F
                dw      op_avai         ; $20
                dw      op_add          ; $21
                dw      op_sub          ; $22
                dw      op_turn         ; $23
                dw      op_at           ; $24
                dw      op_brin         ; $25
                dw      op_find         ; $26
                dw      op_in           ; $27
                dw      op_nop          ; $28
                dw      op_nop          ; $29
                dw      op_okay         ; $2A
                dw      op_wait         ; $2B
                dw      op_quit         ; $2C
                dw      op_exit         ; $2D
                dw      op_room         ; $2E
                dw      op_noun         ; $2F
                dw      op_verb         ; $30
                dw      op_adve         ; $31
                dw      op_goto         ; $32
                dw      op_no1          ; $33
                dw      op_no2          ; $34
                dw      op_vbno         ; $35
                dw      op_list         ; $36
                dw      op_pict         ; $37
                dw      op_text         ; $38
                dw      op_conn         ; $39
                dw      op_weig         ; $3A
                dw      op_with         ; $3B
                dw      op_stre         ; $3C
                dw      op_lf           ; $3D
                dw      op_if           ; $3E
                dw      op_end          ; $3F
