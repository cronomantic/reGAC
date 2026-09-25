; MIT License, Copyright (c) 2025 Cronomantic
;
; The turn: z80/common/loop.asm, in the original's order, which is the
; flowchart in its manual and was measured on it.
;
; The conditions of high priority, then the turn counted, then the question;
; the answer made sense of, the ways out of the room tried, then the
; conditions of this room and then the ones that apply anywhere.  If nothing
; at all took the order, it is said.

MSG_ASK         equ 240
MSG_CANTDO      equ 241
MSG_NOTUNDERSTAND equ 242

; Where the condition tables are.
; Corrupts: AX, BX, CX, SI, ES
loop_init:
                mov     al, SECTION_CONDITIONS
                call    db_section
                mov     [cond_seg], es
                mov     [cond_section], si
                ret

; The table of conditions of kind AL (nought high, two low), at offset BX.
; Corrupts: ES
cond_table:
                mov     es, [cond_seg]
                mov     bl, al
                xor     bh, bh
                add     bx, [cond_section]
                mov     bx, [es:bx]
                add     bx, [cond_section]
                ret

; The conditions of the room the player is in, at offset BX.  Carry set if it
; has none.
; Corrupts: AX, ES
local_table:
                mov     ax, [vm_location]
; The table of the list that is keyed AX, at offset BX: a room's, or one DO
; runs, whose key is its number with the top bit set.  Carry set if there is
; none.
; Corrupts: ES
keyed_table:
                mov     es, [cond_seg]
                mov     bx, [cond_section]
                mov     bx, [es:bx + 4]
                add     bx, [cond_section]      ; the list of rooms that have some
.each:
                cmp     word [es:bx], 0
                je      .none                   ; the list ends with room nought
                cmp     ax, [es:bx]
                je      .found
                add     bx, 4
                jmp     .each
.found:
                mov     bx, [es:bx + 2]
                add     bx, [cond_section]
                clc
                ret
.none:
                stc
                ret

; Run one table, having first forgotten what the last one did.
; Corrupts: everything but DS
run_table:
                mov     byte [vm_done], 0
                mov     byte [vm_if_true], 0
                jmp     run_conditions

; Count this turn.  Two counters hold it, the low one rolling into the high.
bump_turn:
                inc     byte [vm_counters + TURN_COUNTER_LO]
                jnz     .done
                cmp     byte [vm_counters + TURN_COUNTER_HI], 255
                je      .full                   ; both full, leave them alone
                inc     byte [vm_counters + TURN_COUNTER_HI]
                ret
.full:
                mov     byte [vm_counters + TURN_COUNTER_LO], 255
.done:
                ret

; Did the player name a way out of this room?  If so, go that way.
; Corrupts: everything but DS
follow_exit:
                mov     al, [vm_verb]
                test    al, al
                jz      .done
                mov     [vm_arg], al
                mov     ax, [vm_location]
                call    obj_find_location
                jc      .done
                mov     cl, [es:bx + 6]         ; how many exits
                xor     ch, ch
                add     bx, 7
                mov     al, [vm_arg]
.each:
                jcxz    .done
                cmp     al, [es:bx]
                je      .found
                add     bx, 3
                dec     cx
                jmp     .each
.found:
                mov     ax, [es:bx + 1]
                mov     [vm_location], ax
                call    describe_location       ; the same code as GOTO
                mov     byte [vm_moved], 1
.done:
                ret

; One turn.  Comes back with the game over flag set when it is time to stop.
; Whoever moves describes, as the original does; this only runs the tables and
; asks.
; Corrupts: everything but DS
play_turn:
                mov     al, 0                   ; the high priority conditions
                call    cond_table
                call    run_table
                cmp     byte [vm_over], 0
                jne     .done
                ; The turn is counted here, after the high priority table:
                ; MegaCorp sets its game up in a condition guarded by the
                ; count still being nought.
                call    bump_turn
                ; ask, and keep asking until something is typed; a line may
                ; hold several orders and they are taken one at a time
.ask:
                cmp     word [line_left], 0
                jne     .take_one
                call    start_a_line
                mov     al, MSG_ASK
                call    print_message
                call    read_line               ; SI = the codes, CX = how many
                jcxz    .ask
                mov     [line_at], si
                mov     [line_left], cx
.take_one:
                call    next_statement
                jcxz    .ask                    ; nothing in that piece
                call    parse_sentence
                mov     al, 0
                adc     al, 0
                mov     [vm_understood], al
                mov     byte [vm_moved], 0
                call    follow_exit
                ; An order that names a way out has been served by the
                ; moving, and the turn ends there.
                cmp     byte [vm_moved], 0
                jne     .done

                ; the conditions of this room
                mov     byte [vm_any_true], 0
                call    local_table
                jc      .low_priority
                call    run_table
                mov     al, [vm_if_true]
                mov     [vm_any_true], al
                cmp     byte [vm_over], 0
                jne     .done
                cmp     byte [vm_done], 0
                jne     .done
.low_priority:
                mov     al, 2
                call    cond_table
                call    run_table
                mov     al, [vm_if_true]
                or      [vm_any_true], al
                cmp     byte [vm_over], 0
                jne     .done
                cmp     byte [vm_done], 0
                jne     .done

                ; nothing took it: "you cannot do that" if it named a word
                ; the adventure knows, and "I do not understand" if not
                cmp     byte [vm_any_true], 0
                jne     .done
                mov     al, [vm_verb]
                or      al, [vm_noun1]
                mov     al, MSG_CANTDO
                jnz     .say
                mov     al, MSG_NOTUNDERSTAND
.say:
                jmp     print_message
.done:
                ret

; What the game was worth and how long it took, unless the adventure has said
; it would rather not.
; Corrupts: everything but DS
tell_the_score:
                test    byte [vm_flags], MARK_NO_SCORE
                jnz     .done
                call    new_line
                mov     al, MSG_SCORE
                call    print_message
                mov     al, [vm_counters]       ; counter nought is the score
                xor     ah, ah
                call    print_number
                mov     al, MSG_TOOK
                call    print_message
                mov     al, [vm_counters + TURN_COUNTER_LO]
                mov     ah, [vm_counters + TURN_COUNTER_HI]
                call    print_number
                mov     al, MSG_TURNS
                call    print_message
                jmp     new_line
.done:
                ret

; Play until the adventure says to stop.  The room a game opens in is
; described before anything else.
; Corrupts: everything but DS
play:
                mov     ax, [vm_location]
                call    describe_location
.each_turn:
                call    play_turn
                cmp     byte [vm_over], 0
                je      .each_turn
                jmp     tell_the_score

section .data
cond_section:   dw      0
vm_understood:  db      0
vm_any_true:    db      0
section .text
