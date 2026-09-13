; MIT License, Copyright (c) 2025 Cronomantic
;
; The turn.
;
; Describe the room if it is new, count the turn, run the conditions that come
; before the player speaks, ask, make sense of the answer, try the exits of
; the room, then the conditions of this room, then the ones that apply
; anywhere.  If nothing at all took the order, say so.
;
; The order matters and is the original's, from the flowchart in the manual.

MSG_ASK         equ 240
MSG_CANTDO      equ 241
MSG_NOTUNDERSTAND equ 242

; Where each condition table lives, worked out once.
; Corrupts: AF, BC, DE, HL
loop_init:
                ld      a, SECTION_CONDITIONS
                call    db_section
                ld      (cond_section), hl
                ret

; The table of conditions of kind A (0 high, 2 low), in HL.
cond_table:
                ld      hl, (cond_section)
                ld      e, a
                ld      d, 0
                add     hl, de
                ld      e, (hl)
                inc     hl
                ld      d, (hl)
                ld      hl, (cond_section)
                add     hl, de
                ret

; The conditions of the room the player is in, in HL.  Carry set if it has none.
; Corrupts: AF, BC, DE
local_table:
                ld      hl, (cond_section)
                ld      de, 4
                add     hl, de
                ld      e, (hl)
                inc     hl
                ld      d, (hl)
                ld      hl, (cond_section)
                add     hl, de                  ; the list of rooms that have some
                ld      bc, (vm_location)
.each:
                ld      e, (hl)
                inc     hl
                ld      d, (hl)
                inc     hl
                ld      a, d
                or      e
                scf
                ret     z                       ; the list ends with room zero
                ld      a, e
                cp      c
                jr      nz, .skip
                ld      a, d
                cp      b
                jr      z, .found
.skip:
                inc     hl
                inc     hl
                jr      .each
.found:
                ld      e, (hl)
                inc     hl
                ld      d, (hl)
                ld      hl, (cond_section)
                add     hl, de
                or      a
                ret

; Run one table, having first forgotten what the last one did.
; Corrupts: everything
run_table:
                xor     a
                ld      (vm_done), a
                ld      (vm_if_true), a
                jp      run_conditions

; Count this turn.  Two counters hold it, the low one rolling into the high.
; Corrupts: AF, HL
bump_turn:
                ld      hl, vm_counters + TURN_COUNTER_LO
                ld      a, (hl)
                inc     a
                jr      z, .roll_over
                ld      (hl), a
                ret
.roll_over:
                ld      hl, vm_counters + TURN_COUNTER_HI
                ld      a, (hl)
                inc     a
                ret     z                       ; both full, leave them alone
                ld      (hl), a
                xor     a
                ld      (vm_counters + TURN_COUNTER_LO), a
                ret

; Did the player name a way out of this room?  If so, go that way.
; Corrupts: everything
follow_exit:
                ld      a, (vm_verb)
                or      a
                ret     z
                ld      (vm_arg), a
                ld      hl, (vm_location)
                call    obj_find_location
                ret     c
                ld      de, 6
                add     hl, de
                ld      b, (hl)
                inc     hl
                ld      a, b
                or      a
                ret     z
.each:
                ld      a, (vm_arg)
                cp      (hl)
                jr      z, .found
                inc     hl
                inc     hl
                inc     hl
                djnz    .each
                ret
.found:
                inc     hl
                ld      e, (hl)
                inc     hl
                ld      d, (hl)
                ld      (vm_location), de
                ld      a, 1
                ld      (vm_new_room), a
                ret

; One turn.  Comes back with the game over flag set when it is time to stop.
; Corrupts: everything
play_turn:
                ld      a, (vm_new_room)
                or      a
                jr      z, .no_description
                ld      hl, (vm_location)
                call    describe_location
                xor     a
                ld      (vm_new_room), a
.no_description:
                call    bump_turn

                xor     a                       ; the high priority conditions
                call    cond_table
                call    run_table
                ld      a, (vm_over)
                or      a
                ret     nz
                ld      a, (vm_new_room)
                or      a
                ret     nz

                ; ask, and keep asking until something is typed; a line
                ; may hold several orders and they are taken one at a time
.ask:
                ld      hl, (line_left)
                ld      a, h
                or      l
                jr      nz, .take_one
                call    new_line
                ld      a, MSG_ASK
                call    print_message
                call    read_line               ; HL = the codes, BC = how many
                ld      a, b
                or      c
                jr      z, .ask
                ld      (line_at), hl
                ld      (line_left), bc
.take_one:
                call    next_statement
                ld      a, b
                or      c
                jr      z, .ask                 ; nothing in that piece
                call    parse_sentence
                ld      (vm_understood), a
                push    af
                call    follow_exit
                pop     af
                ld      a, (vm_new_room)
                or      a
                ret     nz

                ; the conditions of this room
                xor     a
                ld      (vm_any_true), a
                call    local_table
                jr      c, .low_priority
                call    run_table
                ld      a, (vm_if_true)
                ld      (vm_any_true), a
                ld      a, (vm_over)
                or      a
                ret     nz
                ld      a, (vm_new_room)
                or      a
                ret     nz
                ld      a, (vm_done)
                or      a
                ret     nz
.low_priority:
                ld      a, 2
                call    cond_table
                call    run_table
                ld      a, (vm_if_true)
                ld      hl, vm_any_true
                or      (hl)
                ld      (hl), a
                ld      a, (vm_over)
                or      a
                ret     nz
                ld      a, (vm_new_room)
                or      a
                ret     nz
                ld      a, (vm_done)
                or      a
                ret     nz

                ; nothing took it
                ld      a, (vm_any_true)
                or      a
                ret     nz
                ld      a, (vm_verb)
                or      a
                ld      a, MSG_CANTDO
                jr      nz, .say
                ld      a, MSG_NOTUNDERSTAND
.say:
                jp      print_message

; Play until the adventure says to stop.
play:
                call    play_turn
                ld      a, (vm_over)
                or      a
                jr      z, play
                ret

cond_section:   dw      0
vm_understood:  db      0
vm_any_true:    db      0
