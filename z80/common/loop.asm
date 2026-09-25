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
                ld      bc, (vm_location)
; The table of the list that is keyed BC, in HL: a room's, or one DO runs,
; whose key is its number with the top bit set.  Carry set if there is none.
; Corrupts: AF, BC, DE
keyed_table:
                ld      hl, (cond_section)
                ld      de, 4
                add     hl, de
                ld      e, (hl)
                inc     hl
                ld      d, (hl)
                ld      hl, (cond_section)
                add     hl, de                  ; the list of rooms that have some
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
                ex      de, hl
                call    describe_location       ; their way out goes through
                ld      a, 1                    ; the same code as GOTO
                ld      (vm_moved), a
                ret

; One turn.  Comes back with the game over flag set when it is time to stop.
; Corrupts: everything
; No description is owed to anybody here: whoever moves describes, which is
; how the original does it, and this only runs the tables and asks.
play_turn:
                xor     a                       ; the high priority conditions
                call    cond_table
                call    run_table
                ld      a, (vm_over)
                or      a
                ret     nz
                ; The turn is counted here.  It matters which side of
                ; the table this falls: MegaCorp sets its whole game up in a
                ; condition guarded by the count still being zero, and with
                ; the turn counted first that condition never runs and the
                ; adventure kills the player on the opening move.  Measured
                ; on the original -- see doc/pendiente.md.
                call    bump_turn
                ld      a, (vm_over)
                or      a
                ret     nz

                ; ask, and keep asking until something is typed; a line
                ; may hold several orders and they are taken one at a time
.ask:
                ld      hl, (line_left)
                ld      a, h
                or      l
                jr      nz, .take_one
                call    start_a_line
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
                xor     a
                ld      (vm_moved), a
                call    follow_exit
                pop     af
                ; An order that names a way out of the room has been served
                ; by the moving, and the turn ends there: the original goes
                ; straight back to the top of its loop without looking at
                ; the table of the room or at the low priority one.  Measured
                ; on it with a message written over its low priority table,
                ; which COGE printed and NORTE did not.
                ld      a, (vm_moved)
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
                ld      a, (vm_done)
                or      a
                ret     nz

                ; nothing took it
                ld      a, (vm_any_true)
                or      a
                ret     nz
                ; The verb or the noun: a word it knows with nothing to do
                ; about it is "you cannot do that", and only a line with
                ; neither is "I do not understand".  Read in the original --
                ; it asks after both -- and then asked of it: JARRO on its own
                ; at MegaCorp answers "No puedo hacer eso", and XYZZY answers
                ; "Perdon?".  This looked at the verb alone.
                ld      a, (vm_verb)
                ld      hl, vm_noun1
                or      (hl)
                ld      a, MSG_CANTDO
                jr      nz, .say
                ld      a, MSG_NOTUNDERSTAND
.say:
                jp      print_message

; What the game was worth and how long it took, unless the adventure has
; said it would rather not: that is what the fourth marker is for.  The two
; counters the turns are kept in are the interpreter's as well.
; Corrupts: everything
tell_the_score:
                ld      a, (vm_flags)
                and     MARK_NO_SCORE
                ret     nz
                call    new_line
                ld      a, MSG_SCORE
                call    print_message
                ld      a, (vm_counters)        ; counter zero is the score
                ld      l, a
                ld      h, 0
                call    print_number
                ld      a, MSG_TOOK
                call    print_message
                ld      a, (vm_counters + TURN_COUNTER_HI)
                ld      h, a
                ld      a, (vm_counters + TURN_COUNTER_LO)
                ld      l, a
                call    print_number
                ld      a, MSG_TURNS
                call    print_message
                jp      new_line

; Play until the adventure says to stop.
play:
                ; The room a game opens in is described before anything else,
                ; which is the last thing the original does when it sets a
                ; game up: it ends in a LOOK and then falls into the loop.
                ld      hl, (vm_location)
                call    describe_location
.each_turn:
                call    play_turn
                ld      a, (vm_over)
                or      a
                jr      z, .each_turn
                jp      tell_the_score

cond_section:   dw      0
vm_understood:  db      0
vm_any_true:    db      0
