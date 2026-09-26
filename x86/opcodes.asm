; MIT License, Copyright (c) 2025 Cronomantic
;
; The opcodes themselves, and the table that reaches them: z80/common/
; opcodes.asm, one for one.  Why each does what it does, and where on the
; original it was measured, is written there against each of them.

OP_END          equ 3Fh
OP_LAST         equ 44h

; -- small helpers -----------------------------------------------------------

; Flag AL: its byte in BX, its bit as a mask in AH.
; Corrupts: CL
flag_address:
                mov     cl, al
                and     cl, 7
                mov     ah, 1
                shl     ah, cl
                mov     bl, al
                mov     cl, 3
                shr     bl, cl
                xor     bh, bh
                add     bx, vm_flags
                ret

; Counter AL: its address in BX.  Carry set if there is no such counter.
counter_address:
                cmp     al, COUNTERS
                jae     .none
                mov     bl, al
                xor     bh, bh
                add     bx, vm_counters
                clc
                ret
.none:
                stc
                ret

; Print the name of object AL.  No line is ended.
; Corrupts: everything but DS
print_object_name:
                call    obj_record
                jc      .none
                mov     dx, [es:bx + 4]         ; where its name is in the store
                jmp     print_packed
.none:
                ret

; The same, inside another text: the word it is in is not ended, so what
; follows the name goes with it.  For a hole.
; Corrupts: everything but DS
print_object_within:
                call    obj_record
                jc      .none
                mov     dx, [es:bx + 4]
                jmp     unpack_message
.none:
                ret

; The names of the objects that are in room list_room, with a comma between
; them.  With list_quiet set nothing is printed and the walk only answers
; whether there was anything.  Zero flag set when there was nothing.
; Corrupts: everything but DS
list_objects:
                mov     byte [list_found], 0
                mov     byte [list_object], 1   ; object numbers start at one
.each:
                mov     al, [list_object]
                call    obj_location
                jc      .next
                cmp     dx, [list_room]
                jne     .next
                cmp     byte [list_quiet], 0
                jne     .counted
                cmp     byte [list_found], 0
                je      .first                  ; the first one needs no comma
                mov     al, ','
                call    print_char
.first:
                mov     al, [list_object]
                call    print_object_name
.counted:
                mov     byte [list_found], 1
.next:
                inc     byte [list_object]
                jnz     .each                   ; up to 255
                mov     byte [list_quiet], 0    ; quiet lasts for one walk only
                cmp     byte [list_found], 0
                ret

; Describe location AX: its picture, its description, and what is lying in
; it.  In the dark none of that happens.
; Corrupts: everything but DS
describe_location:
                test    byte [vm_flags], MARK_LIT | MARK_LAMP
                jz      .in_the_dark
                mov     [list_room], ax         ; which room, to name its things
                ; a description starts at the left of the line the cursor is
                ; on, unless the text has the screen
                cmp     byte [vm_graphics], 0
                je      .where_it_is
                mov     byte [cursor_x], 0
.where_it_is:
                mov     ax, [list_room]
                call    obj_find_location
                jc      .none
                push    bx
                mov     ax, [es:bx + 2]         ; the picture this room shows
                test    ax, ax
                jz      .without_a_picture      ; a room may have none
                cmp     byte [vm_graphics], 0
                je      .said                   ; and TEXT says to draw none
                call    draw_picture
                jmp     .said
.without_a_picture:
                ; the text takes the whole screen, as their TEXT does
                cmp     byte [vm_graphics], 0
                je      .said
                call    text_window_all
.said:
                pop     bx
                mov     ax, [list_room]         ; the record again, whatever
                call    obj_find_location       ; drawing did to ES
                mov     dx, [es:bx + 4]         ; where the description is
                call    print_packed
                mov     byte [list_quiet], 1
                call    list_objects            ; is there anything here at all
                jz      .nothing_here
                mov     al, MSG_OBJHERE
                call    print_message           ; which has to be said first
                call    list_objects
.nothing_here:
                or      byte [vm_flags], MARK_DESCRIBED
.none:
                ret
.in_the_dark:
                call    gfx_clear
                call    gfx_show
                mov     al, MSG_ITSDARK
                jmp     print_message

; Print AX as a decimal number, without leading zeros.
; Corrupts: everything but DS
print_number:
                mov     si, print_powers
                xor     cl, cl                  ; nothing shown yet
                mov     ch, 5
.each:
                mov     dx, [si]
                add     si, 2
                xor     bl, bl
.subtract:
                cmp     ax, dx
                jb      .digit
                sub     ax, dx
                inc     bl
                jmp     .subtract
.digit:
                test    bl, bl
                jnz     .show                   ; a digit worth showing
                test    cl, cl
                jnz     .show                   ; something came before it
                cmp     ch, 1
                jne     .skip                   ; a leading zero, leave it out
.show:
                push    ax
                push    cx
                push    si
                mov     al, bl
                call    print_digit
                pop     si
                pop     cx
                pop     ax
                mov     cl, 1
.skip:
                dec     ch
                jnz     .each
                ret

; Print the digit in AL, nought to nine, as the adventure's character.
; Corrupts: everything but DS
print_digit:
                add     al, DIGIT_ZERO          ; a code is its own ASCII here
                cmp     byte [digit_within], 0
                jne     text_put                ; in a hole: part of its word
                mov     [digit_char], al
                mov     si, digit_char
                mov     cx, 1
                jmp     print_text

; -- the opcodes -------------------------------------------------------------

op_and:
                call    vm_pop
                mov     dx, ax
                call    vm_pop
                and     ax, dx
                call    vm_push
                jmp     vm_loop

op_or:
                call    vm_pop
                mov     dx, ax
                call    vm_pop
                or      ax, dx
                call    vm_push
                jmp     vm_loop

op_xor:
                call    vm_pop
                mov     dx, ax
                call    vm_pop
                xor     ax, dx
                call    vm_push
                jmp     vm_loop

op_not:
                call    vm_pop
                test    ax, ax
                jz      vm_true
vm_false:
                call    vm_push_false
                jmp     vm_loop
vm_true:
                call    vm_push_true
                jmp     vm_loop

; HOLD n: n fiftieths of a second, or until the player presses something.
op_hold:
                call    vm_pop
                call    wait_or_key
                jmp     vm_loop

; GET: in the hand first, then round the room, and last the weight, and every
; refusal ends the turn.
op_get:
                call    vm_pop
                mov     [vm_arg], ax
                call    obj_location
                jc      .not_here               ; no such object: not here
                cmp     dx, CARRIED
                je      .already
                cmp     dx, [vm_location]
                jne     .not_here
                mov     al, [vm_arg]
                call    obj_weight
                add     al, [vm_weight]         ; what would be carried then
                cmp     al, [vm_max_weight]
                jae     .too_much
                mov     [vm_weight], al
                mov     al, [vm_arg]
                mov     dx, CARRIED
                call    obj_move
                jmp     vm_loop
.already:
                mov     al, MSG_HAVEIT
                jmp     .complain
.not_here:
                mov     al, MSG_CANTSEE
                jmp     .complain
.too_much:
                mov     al, MSG_TOOMUCH
.complain:
                call    print_message
                jmp     end_turn

op_drop:
                call    vm_pop
                mov     [vm_arg], ax
                call    obj_location
                jc      .not_carried
                cmp     dx, CARRIED
                jne     .not_carried
                mov     al, [vm_arg]
                mov     dx, [vm_location]
                call    obj_move
                mov     al, [vm_arg]
                call    obj_weight
                sub     [vm_weight], al
                jmp     vm_loop
.not_carried:
                mov     al, MSG_DONTHAVE
                call    print_message
                jmp     end_turn

; What object AL weighs, in AL; nought if there is no such object.
; Corrupts: BX, ES
obj_weight:
                call    obj_record
                mov     al, 0
                jc      .none
                mov     al, [es:bx + 1]
.none:
                ret

; A refusal ends the line and with it the turn, and so the table it is in.
end_turn:
                call    new_line
                mov     byte [vm_done], 1
                ret

; Each of the two goes where the other was.
op_swap:
                call    vm_pop
                mov     [vm_arg], ax            ; the second object
                call    vm_pop
                mov     [vm_arg2], ax
                mov     al, [vm_arg]
                call    obj_location
                jc      .done
                push    dx                      ; where the first one is
                mov     al, [vm_arg2]
                call    obj_location            ; DX = where the second one is
                jc      .no_second
                mov     al, [vm_arg]
                call    obj_move                ; the first goes there
                pop     dx                      ; and the second where it was
                mov     al, [vm_arg2]
                call    obj_move
                jmp     vm_loop
.no_second:
                pop     dx
.done:
                jmp     vm_loop

op_to:
                call    vm_pop
                mov     dx, ax                  ; where to
                call    vm_pop                  ; which object
                call    obj_move
                jmp     vm_loop

op_obj:
                call    vm_pop
                call    print_object_name
                jmp     vm_loop

op_set:
                call    vm_pop
                call    flag_address
                or      [bx], ah
                jmp     vm_loop

op_reset:
                call    vm_pop
                call    flag_address
                not     ah
                and     [bx], ah
                jmp     vm_loop

op_set_q:
                call    vm_pop
                call    flag_address
                test    [bx], ah
                jz      vm_false
                jmp     vm_true

op_reset_q:
                call    vm_pop
                call    flag_address
                test    [bx], ah
                jz      vm_true
                jmp     vm_false

op_cset:
                call    vm_pop                  ; which counter
                mov     dx, ax
                call    vm_pop                  ; the value
                xchg    ax, dx
                call    counter_address
                jc      .none
                mov     [bx], dl
.none:
                jmp     vm_loop

op_ctr:
                call    vm_pop
                call    counter_address
                jc      vm_false
                mov     al, [bx]
                xor     ah, ah
                call    vm_push
                jmp     vm_loop

op_decr:
                call    vm_pop
                call    counter_address
                jc      .done
                cmp     byte [bx], 0
                je      .done                   ; it stops at nought
                dec     byte [bx]
.done:
                jmp     vm_loop

op_incr:
                call    vm_pop
                call    counter_address
                jc      .done
                cmp     byte [bx], 255
                je      .done                   ; and at 255
                inc     byte [bx]
.done:
                jmp     vm_loop

op_equ_q:
                call    vm_pop                  ; which counter
                call    counter_address
                jc      .no
                mov     dl, [bx]
                xor     dh, dh
                call    vm_pop                  ; the value to compare
                cmp     ax, dx
                jne     vm_false
                jmp     vm_true
.no:
                call    vm_pop
                jmp     vm_false

op_desc:
                call    vm_pop
                call    describe_location
                jmp     vm_loop

op_look:
                mov     ax, [vm_location]
                call    describe_location
                jmp     vm_loop

op_mess:
                call    vm_pop
                call    print_message
                jmp     vm_loop

op_prin:
                call    vm_pop
                call    print_number
                jmp     vm_loop

op_rand:
                call    vm_pop
                mov     [vm_arg], ax            ; the limit
                call    next_random
                mov     cl, [vm_arg]
                test    cl, cl
                jz      vm_false
.reduce:
                cmp     al, cl
                jb      .done
                sub     al, cl
                jmp     .reduce
.done:
                xor     ah, ah
                call    vm_push
                jmp     vm_loop

; Less and greater take the sign of the difference, which is what the
; original looks at.
op_less:
                call    vm_pop
                mov     dx, ax                  ; the right hand side
                call    vm_pop
                sub     ax, dx
                js      vm_true
                jmp     vm_false

op_greater:
                call    vm_pop
                mov     dx, ax
                call    vm_pop
                sub     dx, ax
                js      vm_true
                jmp     vm_false

op_equal:
                call    vm_pop
                mov     dx, ax
                call    vm_pop
                cmp     ax, dx
                je      vm_true
                jmp     vm_false

; SAVE and LOAD: the game, not the adventure.  A load does not describe
; anything; the adventure's own LOOK does, after it.
op_save:
                mov     si, vm_state
                mov     cx, VM_STATE_BYTES
                call    tape_save
                jmp     vm_loop
op_load:
                mov     si, vm_state
                mov     cx, VM_STATE_BYTES
                call    tape_load
                jmp     vm_loop

op_here:
                call    vm_pop
                call    obj_location
                jc      vm_false
                cmp     dx, [vm_location]
                je      vm_true
                jmp     vm_false

op_carr:
                call    vm_pop
                call    obj_location
                jc      vm_false
                cmp     dx, CARRIED
                je      vm_true
                jmp     vm_false

op_avai:
                call    vm_pop
                call    obj_location
                jc      vm_false
                cmp     dx, CARRIED
                je      vm_true
                cmp     dx, [vm_location]
                je      vm_true
                jmp     vm_false

op_add:
                call    vm_pop
                mov     dx, ax
                call    vm_pop
                add     ax, dx
                call    vm_push
                jmp     vm_loop

op_sub:
                call    vm_pop
                mov     dx, ax
                call    vm_pop
                sub     ax, dx
                call    vm_push
                jmp     vm_loop

op_turn:
                mov     al, [vm_counters + TURN_COUNTER_LO]
                mov     ah, [vm_counters + TURN_COUNTER_HI]
                call    vm_push
                jmp     vm_loop

op_at:
                call    vm_pop
                cmp     ax, [vm_location]
                je      vm_true
                jmp     vm_false

; BRIN fetches something to where the player is, and says so when it cannot.
op_brin:
                call    vm_pop
                mov     [vm_arg], ax
                call    obj_location
                jc      .done
                cmp     dx, CARRIED
                je      .already
                test    dx, dx
                jz      .nowhere
                mov     al, [vm_arg]
                mov     dx, [vm_location]
                call    obj_move
.done:
                jmp     vm_loop
.already:
                mov     al, MSG_HAVEIT
                jmp     .complain
.nowhere:
                mov     al, MSG_CANTFIND
.complain:
                call    print_message
                jmp     end_turn

; FIND goes to where the thing is and describes the room on arriving.
op_find:
                call    vm_pop
                call    obj_location
                jc      .done
                cmp     dx, CARRIED
                je      .done                   ; already with you
                test    dx, dx
                jz      .nowhere
                mov     [vm_location], dx
                jmp     op_look
.done:
                jmp     vm_loop
.nowhere:
                mov     al, MSG_CANTFIND
                call    print_message
                jmp     end_turn

op_in:
                call    vm_pop
                mov     [vm_arg2], ax           ; the room
                call    vm_pop
                call    obj_location
                jc      vm_false
                cmp     dx, [vm_arg2]
                je      vm_true
                jmp     vm_false

op_nop:
                jmp     vm_loop

; Both end the turn, and with it the table they are in: a return goes back to
; whoever called the table, which is what the end of a table does too.
op_okay:
                mov     al, MSG_OKAY
                call    print_message
                mov     byte [vm_done], 1
                ret

op_wait:
                mov     byte [vm_done], 1
                ret

; QUIT asks first, and reads one key: N calls it off and anything else goes
; ahead.  EXIT just stops.
op_quit:
                mov     al, MSG_YOUSURE
                call    print_message
                call    read_key
                and     al, 0DFh                ; as their own code does
                cmp     al, 'N'
                jne     op_exit
                jmp     vm_loop
op_exit:
                mov     byte [vm_over], 1
                mov     byte [vm_done], 1
                jmp     vm_loop

op_room:
                mov     ax, [vm_location]
                call    vm_push
                jmp     vm_loop

; NOUN n answers for either of the two nouns a line can name.
op_noun:
                call    vm_pop
                cmp     al, [vm_noun1]
                je      vm_true
                cmp     al, [vm_noun2]
                je      vm_true
                jmp     vm_false

op_verb:
                call    vm_pop
                cmp     al, [vm_verb]
                je      vm_true
                jmp     vm_false

op_adve:
                call    vm_pop
                cmp     al, [vm_adverb]
                je      vm_true
                jmp     vm_false

; GOTO is their LOOK with a room put in first.
op_goto:
                call    vm_pop
                mov     [vm_location], ax
                jmp     op_look

op_no1:
                mov     al, [vm_noun1]
                jmp     push_byte
op_no2:
                mov     al, [vm_noun2]
                jmp     push_byte
op_vbno:
                mov     al, [vm_verb]
push_byte:
                xor     ah, ah
                call    vm_push
                jmp     vm_loop

; The word an adventure gives for having nothing at all.
; Corrupts: everything but DS
print_nothing_word:
                mov     dx, [nothing_at]
                jmp     print_packed

op_list:
                call    vm_pop
                mov     [list_room], ax         ; the room to list
                call    list_objects
                jnz     .done
                call    print_nothing_word      ; LIST always writes something
.done:
                jmp     vm_loop

; TEXT gives the text the whole screen and stops the pictures; PICT only lets
; them be drawn again.
op_pict:
                mov     byte [vm_graphics], 1
                jmp     vm_loop

op_text:
                mov     byte [vm_graphics], 0
                call    text_window_all
                jmp     vm_loop

op_conn:
                call    vm_pop
                mov     [vm_arg], ax            ; which way
                mov     ax, [vm_location]
                call    obj_find_location
                jc      vm_false
                mov     cl, [es:bx + 6]         ; how many exits
                xor     ch, ch
                add     bx, 7
                mov     al, [vm_arg]
.each:
                jcxz    .none
                cmp     al, [es:bx]
                je      .found
                add     bx, 3
                dec     cx
                jmp     .each
.found:
                mov     ax, [es:bx + 1]
                call    vm_push
                jmp     vm_loop
.none:
                jmp     vm_false

op_weig:
                call    vm_pop
                call    obj_record
                jc      vm_false
                mov     al, [es:bx + 1]
                jmp     push_byte

op_with:
                mov     ax, CARRIED
                call    vm_push
                jmp     vm_loop

op_stre:
                call    vm_pop
                mov     [vm_max_weight], al
                jmp     vm_loop

op_lf:
                call    new_line
                jmp     vm_loop

; SOUND: which noise of the adventure's own table to make.  QUIET: nothing is
; left ringing by an engine that returns when the noise is over.
op_sound:
                call    vm_pop
                call    beep_sound
                jmp     vm_loop

op_quiet:
                jmp     vm_loop

; DO n: the table /PROC n, run as if it were written here -- see
; z80/common/opcodes.asm, which is the same step for step.  What ends the turn
; in it ends this table too; what this table had on the stack is kept under
; the base the other one starts from.  A table there is not, or DO more than
; PROC_DEPTH deep, does nothing.  Always here: a PC does not count bytes the
; way a 464 does.
PROC_DEPTH      equ 8

op_do:
                call    vm_pop
                cmp     byte [vm_depth], PROC_DEPTH
                jae     .nothing                ; too deep
                or      ah, 80h                 ; how the list keys it
                call    keyed_table
                jc      .nothing                ; no such table
                inc     byte [vm_depth]
                push    word [vm_code]          ; where this table was
                push    word [vm_stack_base]
                mov     ax, [vm_sp]
                mov     [vm_stack_base], ax     ; what is there stays there
                call    run_conditions
                mov     ax, [vm_stack_base]
                mov     [vm_sp], ax             ; the stack as DO found it
                pop     word [vm_stack_base]
                pop     word [vm_code]
                dec     byte [vm_depth]
                mov     byte [vm_skip], 0       ; DO is only ever obeyed
                cmp     byte [vm_done], 0
                jne     .over
.nothing:
                jmp     vm_loop
.over:
                ret                             ; it ended the turn: so does this

; DRAW n: picture n, where the room's goes and the way the room's goes --
; see z80/common/opcodes.asm.  Nought is no picture and gives the text the
; whole screen, and under TEXT nothing is drawn.  Always here, as DO is.
op_draw:
                call    vm_pop
                cmp     byte [vm_graphics], 0
                je      .done                   ; TEXT says to draw none
                test    ax, ax
                jz      .without_a_picture
                call    draw_picture
                jmp     vm_loop
.without_a_picture:
                call    text_window_all
.done:
                jmp     vm_loop

op_if:
                call    vm_pop
                test    ax, ax
                jnz     .true
                mov     byte [vm_skip], 1
                jmp     vm_loop
.true:
                mov     byte [vm_if_true], 1    ; something took the order
                jmp     vm_loop

op_end:
                mov     byte [vm_skip], 0
                call    vm_reset_stack
                jmp     vm_loop

; A number nobody will call random, but good enough to pick a message: the
; Z80's own shuffle of the two bytes, step for step.
; Corrupts: AX, BX
next_random:
                mov     bx, [vm_seed]           ; BH is its H, BL its L
                mov     al, bh
                rcr     al, 1                   ; the carry is bit nought of H
                mov     al, bl
                rcr     al, 1
                xor     al, bh
                mov     bh, al
                mov     al, bl
                rcr     al, 1                   ; the carry is bit nought of L
                mov     al, bh
                rcr     al, 1
                xor     al, bl
                mov     bl, al
                xor     al, bh
                mov     bh, al
                mov     [vm_seed], bx
                mov     al, bl                  ; the low byte is the number
                ret

section .data
list_room:      dw      0                       ; whose objects are being named
list_quiet:     db      0                       ; count them, do not name them
list_found:     db      0                       ; whether there was any
list_object:    db      0
digit_char:     db      0
print_powers:   dw      10000, 1000, 100, 10, 1

; -- where each opcode lives -------------------------------------------------
vm_table:
                dw      op_and          ; 01h
                dw      op_or           ; 02h
                dw      op_not          ; 03h
                dw      op_xor          ; 04h
                dw      op_hold         ; 05h
                dw      op_get          ; 06h
                dw      op_drop         ; 07h
                dw      op_swap         ; 08h
                dw      op_to           ; 09h
                dw      op_obj          ; 0Ah
                dw      op_set          ; 0Bh
                dw      op_reset        ; 0Ch
                dw      op_set_q        ; 0Dh
                dw      op_reset_q      ; 0Eh
                dw      op_cset         ; 0Fh
                dw      op_ctr          ; 10h
                dw      op_decr         ; 11h
                dw      op_incr         ; 12h
                dw      op_equ_q        ; 13h
                dw      op_desc         ; 14h
                dw      op_look         ; 15h
                dw      op_mess         ; 16h
                dw      op_prin         ; 17h
                dw      op_rand         ; 18h
                dw      op_less         ; 19h
                dw      op_greater      ; 1Ah
                dw      op_equal        ; 1Bh
                dw      op_save         ; 1Ch
                dw      op_load         ; 1Dh
                dw      op_here         ; 1Eh
                dw      op_avai         ; 1Fh
                dw      op_carr         ; 20h
                dw      op_add          ; 21h
                dw      op_sub          ; 22h
                dw      op_turn         ; 23h
                dw      op_at           ; 24h
                dw      op_brin         ; 25h
                dw      op_find         ; 26h
                dw      op_in           ; 27h
                dw      op_nop          ; 28h
                dw      op_nop          ; 29h
                dw      op_okay         ; 2Ah
                dw      op_wait         ; 2Bh
                dw      op_quit         ; 2Ch
                dw      op_exit         ; 2Dh
                dw      op_room         ; 2Eh
                dw      op_noun         ; 2Fh
                dw      op_verb         ; 30h
                dw      op_adve         ; 31h
                dw      op_goto         ; 32h
                dw      op_no1          ; 33h
                dw      op_no2          ; 34h
                dw      op_vbno         ; 35h
                dw      op_list         ; 36h
                dw      op_pict         ; 37h
                dw      op_text         ; 38h
                dw      op_conn         ; 39h
                dw      op_weig         ; 3Ah
                dw      op_with         ; 3Bh
                dw      op_stre         ; 3Ch
                dw      op_lf           ; 3Dh
                dw      op_if           ; 3Eh
                dw      op_end          ; 3Fh
                dw      op_nop          ; 40h, which MUSIC was
                dw      op_sound        ; 41h
                dw      op_quiet        ; 42h
                dw      op_do           ; 43h
                dw      op_draw         ; 44h
section .text
