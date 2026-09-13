; MIT License, Copyright (c) 2025 Cronomantic
;
; The condition machine: the 61 opcodes an adventure is written in.
;
; It is a stack machine.  A byte with the top bit set is a constant and takes
; the byte after it, giving fifteen bits; anything else is an opcode; a zero
; ends the table.  IF pops a value and, when it is zero, everything up to the
; matching END is passed over, which is why the skipping still has to know
; that a constant is two bytes long.
;
; Everything here is the same on every machine.  What differs is printing and
; drawing, which the machine layer provides.

VM_STACK_DEPTH  equ 32
FLAG_BYTES      equ 32                  ; 256 flags, a bit each
COUNTERS        equ 128
CARRIED         equ 255                 ; the location an object carried is in
NOWHERE         equ 0

; The messages the interpreter itself prints
MSG_PRESSKEY    equ 243
MSG_YOUSURE     equ 244
MSG_DONTHAVE    equ 246
MSG_CANTSEE     equ 247
MSG_TOOMUCH     equ 248
MSG_OKAY        equ 254

TURN_COUNTER_LO equ 126
TURN_COUNTER_HI equ 127

; Set the machine up for a new game: no flags, no counters, objects where the
; adventure says they start.
; Corrupts: AF, BC, DE, HL
vm_init:
                ld      hl, vm_flags
                ld      de, vm_flags + 1
                ld      bc, FLAG_BYTES + COUNTERS - 1
                ld      (hl), 0
                ldir
                ld      hl, obj_entry
                ld      de, obj_entry + 1
                ld      bc, 512 + 512 - 1
                ld      (hl), 0
                ldir
                xor     a
                ld      (vm_skip), a
                ld      (vm_done), a
                ld      (vm_over), a
                ld      (vm_new_room), a
                ld      a, 1
                ld      (vm_graphics), a
                ; walk the object table, noting where each one lives
                ld      a, SECTION_OBJECTS
                call    db_section
                ld      b, (hl)                 ; how many objects
                inc     hl
                ld      a, b
                or      a
                jr      z, .no_objects
.each_object:
                push    bc
                ld      a, (hl)                 ; its number
                ld      c, a
                ld      b, 0
                push    hl
                ; remember where its record is
                ld      hl, obj_entry
                add     hl, bc
                add     hl, bc
                pop     de                      ; DE = the record
                ld      (hl), e
                inc     hl
                ld      (hl), d
                ; and where it starts out
                ex      de, hl
                inc     hl
                inc     hl                      ; step over number and weight
                ld      e, (hl)
                inc     hl
                ld      d, (hl)
                inc     hl
                inc     hl
                inc     hl                      ; on to the next record
                push    hl
                ld      hl, obj_loc
                add     hl, bc
                add     hl, bc
                ld      (hl), e
                inc     hl
                ld      (hl), d
                pop     hl
                pop     bc
                djnz    .each_object
.no_objects:
                ret

; -- the operand stack -------------------------------------------------------

vm_reset_stack:
                ld      hl, vm_stack
                ld      (vm_sp), hl
                ret

; Push HL.  Corrupts: DE
vm_push:
                push    de
                ld      de, (vm_sp)
                ex      de, hl
                ld      (hl), e
                inc     hl
                ld      (hl), d
                inc     hl
                ld      (vm_sp), hl
                ex      de, hl
                pop     de
                ret

; Pop into HL.  Corrupts: DE
vm_pop:
                push    de
                ld      hl, (vm_sp)
                ld      de, vm_stack
                or      a
                sbc     hl, de
                jr      z, .empty               ; nothing there: give back zero
                add     hl, de
                dec     hl
                ld      d, (hl)
                dec     hl
                ld      e, (hl)
                ld      (vm_sp), hl
                ex      de, hl
                pop     de
                ret
.empty:
                ld      hl, 0
                pop     de
                ret

; Push zero or one, from the zero flag: used by every test.
; Corrupts: DE, HL
vm_push_false:
                ld      hl, 0
                jr      vm_push
vm_push_true:
                ld      hl, 1
                jr      vm_push

; -- running -----------------------------------------------------------------

; Run the condition table at HL.
; Corrupts: everything
run_conditions:
                ld      (vm_code), hl
                call    vm_reset_stack
                xor     a
                ld      (vm_skip), a
vm_loop:
                ld      hl, (vm_code)
                ld      a, (hl)
                inc     hl
                ld      (vm_code), hl
                or      a
                ret     z                       ; a zero byte ends the table
                bit     7, a
                jr      nz, vm_constant
                ; an opcode: is it being passed over?
                ld      c, a
                ld      a, (vm_skip)
                or      a
                jr      z, .obey
                ld      a, c
                cp      OP_END
                jr      nz, vm_loop             ; only END gets through
.obey:
                ld      a, c
                ld      l, a
                ld      h, 0
                add     hl, hl
                ld      de, vm_table - 2        ; the table starts at opcode 1
                add     hl, de
                ld      a, (hl)
                inc     hl
                ld      h, (hl)
                ld      l, a
                jp      (hl)

vm_constant:
                ; fifteen bits, spread over the two bytes
                and     $7F
                ld      d, a
                ld      hl, (vm_code)
                ld      e, (hl)
                inc     hl
                ld      (vm_code), hl
                ld      a, (vm_skip)
                or      a
                jr      nz, vm_loop             ; passed over, but still two bytes
                ex      de, hl
                call    vm_push
                jr      vm_loop

; -- helpers -----------------------------------------------------------------

; Where object L lives, in DE.  Carry set if there is no such object.
; Corrupts: AF, HL
obj_location:
                ld      h, 0
                add     hl, hl
                ld      de, obj_entry
                add     hl, de
                ld      a, (hl)
                inc     hl
                or      (hl)
                scf
                ret     z                       ; no record, no object
                ld      hl, (vm_arg)
                ld      h, 0
                add     hl, hl
                ld      de, obj_loc
                add     hl, de
                ld      e, (hl)
                inc     hl
                ld      d, (hl)
                or      a
                ret

; Put object L in room DE.
; Corrupts: AF, HL
obj_move:
                ld      h, 0
                add     hl, hl
                push    de
                ld      de, obj_loc
                add     hl, de
                pop     de
                ld      (hl), e
                inc     hl
                ld      (hl), d
                ret

; The record of object L, in HL.  Carry set if there is none.
obj_record:
                ld      h, 0
                add     hl, hl
                ld      de, obj_entry
                add     hl, de
                ld      e, (hl)
                inc     hl
                ld      d, (hl)
                ld      a, d
                or      e
                scf
                ret     z
                ex      de, hl
                or      a
                ret

; Print message number A, then a new line.
; Corrupts: everything
print_message:
                call    message_index           ; DE = where it is in the store
                ret     c
                call    unpack_message          ; BC = how long
                ld      hl, text_buffer
                call    print_text
                jp      new_line

; Find location HL in the table; its record comes back in HL.
; Carry set if there is no such location.
obj_find_location:
                ld      (find_id), hl
                ld      a, SECTION_LOCATIONS
                call    db_section              ; this treads on DE
                ld      c, (hl)
                inc     hl
                ld      b, (hl)                 ; how many
                inc     hl
                ld      de, (find_id)
.each:
                ld      a, b
                or      c
                scf
                ret     z
                dec     bc
                ld      a, (hl)
                cp      e
                jr      nz, .skip
                inc     hl
                ld      a, (hl)
                dec     hl
                cp      d
                jr      z, .found
.skip:
                ; step over this record: 7 bytes plus three an exit
                push    bc
                ld      bc, 6
                add     hl, bc
                ld      c, (hl)                 ; how many exits
                inc     hl
                ld      b, 0
                jr      .skip_exits_check
.skip_exits:
                inc     hl
                inc     hl
                inc     hl
                dec     c
.skip_exits_check:
                ld      a, c
                or      a
                jr      nz, .skip_exits
                pop     bc
                jr      .each
.found:
                or      a
                ret

; -- state -------------------------------------------------------------------

vm_code:        dw      0
vm_sp:          dw      0
vm_arg:         dw      0
find_id:        dw      0
vm_skip:        db      0
vm_if_true:     db      0                       ; some IF came out true
vm_done:        db      0                       ; the turn is over
vm_over:        db      0                       ; the game is over
vm_new_room:    db      0                       ; the room wants describing
vm_graphics:    db      1
vm_verb:        db      0
vm_noun1:       db      0
vm_noun2:       db      0
vm_adverb:      db      0
vm_max_weight:  db      0
; Everything from here to vm_state_end is what a game amounts to, so it is
; what SAVE writes out and LOAD reads back.  The adventure itself never
; changes, which is why only this much has to travel.
vm_state:
vm_location:    dw      0
vm_seed:        dw      $A55A
vm_stack:       ds      VM_STACK_DEPTH * 2
vm_flags:       ds      FLAG_BYTES
vm_counters:    ds      COUNTERS
obj_entry:      ds      512                     ; where each object's record is
obj_loc:        ds      512                     ; and where it is now
vm_state_end:
