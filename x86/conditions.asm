; MIT License, Copyright (c) 2025 Cronomantic
;
; The condition machine: the opcodes an adventure is written in.  It is
; z80/common/conditions.asm, and what each piece is for and where it was
; measured is written there.
;
; A stack machine.  A byte with the top bit set is a constant and takes the
; byte after it, giving fifteen bits; anything else is an opcode; a nought
; ends the table.  IF pops a value and, when it is nought, everything up to
; the matching END is passed over.
;
; The tables are read through ES, which printing takes for the screen, so the
; walk loads it again for every byte.

VM_STACK_DEPTH  equ 32
FLAG_BYTES      equ 32                  ; 256 flags, a bit each
COUNTERS        equ 128
CARRIED         equ 255                 ; the location an object carried is in
NOWHERE         equ 0

MSG_SCORE       equ 249
MSG_TOOK        equ 250
MSG_PRESSKEY    equ 243
MSG_YOUSURE     equ 244
MSG_HAVEIT      equ 245
MSG_DONTHAVE    equ 246
MSG_CANTSEE     equ 247
MSG_TOOMUCH     equ 248
MSG_ITSDARK     equ 251
MSG_CANTFIND    equ 252
MSG_OBJHERE     equ 253
MSG_OKAY        equ 254
MSG_TURNS       equ 255

MARK_DESCRIBED  equ 00000001b           ; a room has just been described
MARK_LIT        equ 00000010b           ; this place has light of its own
MARK_LAMP       equ 00000100b           ; the player carries something alight
MARK_NO_SCORE   equ 00001000b           ; do not tell the score at the end

TURN_COUNTER_LO equ 126
TURN_COUNTER_HI equ 127

; Set the machine up for a new game: no counters, no markers but the one that
; says there is light, and every object where the adventure says it starts.
; Corrupts: everything but DS
vm_init:
                push    ds
                pop     es
                cld
                xor     ax, ax
                mov     di, vm_flags
                mov     cx, FLAG_BYTES + COUNTERS
                rep     stosb
                mov     di, obj_entry
                mov     cx, 256
                rep     stosw
                mov     di, obj_loc
                mov     cx, 256
                rep     stosw
                mov     [vm_skip], al
                mov     [vm_done], al
                mov     [vm_over], al
                mov     [vm_moved], al
                mov     [vm_weight], al
                mov     byte [vm_flags], MARK_LIT       ; a game starts lit
                mov     byte [vm_graphics], 1
                mov     byte [vm_max_weight], 250
                ; walk the object table, noting where each one lives
                mov     al, SECTION_OBJECTS
                call    db_section
                mov     [obj_seg], es
                mov     cl, [es:si]             ; how many objects
                xor     ch, ch
                inc     si
.each_object:
                jcxz    .done
                mov     bl, [es:si]             ; its number
                xor     bh, bh
                shl     bx, 1
                mov     [obj_entry + bx], si    ; where its record is
                mov     ax, [es:si + 2]
                mov     [obj_loc + bx], ax      ; and where it starts out
                add     si, 6
                dec     cx
                jmp     .each_object
.done:
                ret

; -- the operand stack -------------------------------------------------------

; Empty is down to the base, which is the foot of the stack except while DO
; runs a table: then it is where the stack stood, so that what the table that
; ran it had there is left alone.
; Corrupts: nothing
vm_reset_stack:
                push    ax
                mov     ax, [vm_stack_base]
                mov     [vm_sp], ax
                pop     ax
                ret

; Push AX.
; Corrupts: nothing else
vm_push:
                push    bx
                mov     bx, [vm_sp]
                cmp     bx, vm_stack + VM_STACK_DEPTH * 2
                jae     .full                   ; no room: it goes nowhere
                mov     [bx], ax
                add     word [vm_sp], 2
.full:
                pop     bx
                ret

; Pop into AX; nought when there is nothing there.
; Corrupts: nothing else
vm_pop:
                push    bx
                mov     bx, [vm_sp]
                cmp     bx, [vm_stack_base]
                je      .empty
                sub     bx, 2
                mov     [vm_sp], bx
                mov     ax, [bx]
                pop     bx
                ret
.empty:
                xor     ax, ax
                pop     bx
                ret

vm_push_false:
                xor     ax, ax
                jmp     vm_push
vm_push_true:
                mov     ax, 1
                jmp     vm_push

; -- running -----------------------------------------------------------------

; Run the condition table at offset BX of the conditions' segment.
; Corrupts: everything but DS
run_conditions:
                mov     [vm_code], bx
                call    vm_reset_stack
                mov     byte [vm_skip], 0
vm_loop:
                mov     es, [cond_seg]
                mov     bx, [vm_code]
                mov     al, [es:bx]
                inc     bx
                mov     [vm_code], bx
                test    al, al
                jz      .ended                  ; a nought ends the table
                test    al, 80h
                jnz     vm_constant
                ; an opcode: is it being passed over?
                cmp     byte [vm_skip], 0
                je      .obey
                cmp     al, OP_END
                jne     vm_loop                 ; only END gets through
.obey:
                cmp     al, OP_LAST
                ja      vm_loop                 ; not one there is
                xor     ah, ah
                mov     bx, ax
                shl     bx, 1
                jmp     [vm_table - 2 + bx]     ; the table starts at opcode 1
.ended:
                ret

vm_constant:
                ; fifteen bits, spread over the two bytes
                and     al, 7Fh
                mov     ah, al
                mov     al, [es:bx]
                inc     word [vm_code]
                cmp     byte [vm_skip], 0
                jne     vm_loop                 ; passed over, but still two bytes
                call    vm_push
                jmp     vm_loop

; -- helpers -----------------------------------------------------------------

; Where object AL lives, in DX.  Carry set if there is no such object.
; Corrupts: BX
obj_location:
                mov     bl, al
                xor     bh, bh
                shl     bx, 1
                cmp     word [obj_entry + bx], 0
                je      .none                   ; no record, no object
                mov     dx, [obj_loc + bx]
                clc
                ret
.none:
                stc
                ret

; Put object AL in room DX.
; Corrupts: BX
obj_move:
                mov     bl, al
                xor     bh, bh
                shl     bx, 1
                mov     [obj_loc + bx], dx
                ret

; The record of object AL, at ES:BX.  Carry set if there is none.
obj_record:
                mov     bl, al
                xor     bh, bh
                shl     bx, 1
                mov     bx, [obj_entry + bx]
                test    bx, bx
                jz      .none
                mov     es, [obj_seg]
                clc
                ret
.none:
                stc
                ret

; Print message number AL.  Nothing follows it: the adventures say LF when
; they want a line ended.
; Corrupts: everything but DS
print_message:
                call    message_index           ; DX = where it is in the store
                jc      .none
                jmp     print_packed
.none:
                ret

; Find location AX in the table; its record comes back at ES:BX.  Carry set if
; there is no such location.
; Corrupts: CX, DX, SI
obj_find_location:
                mov     dx, ax
                push    ax
                mov     al, SECTION_LOCATIONS
                call    db_section
                pop     ax
                mov     cx, [es:si]             ; how many
                lea     bx, [si + 2]
.each:
                jcxz    .none
                dec     cx
                cmp     dx, [es:bx]
                je      .found
                ; step over this record: seven bytes and three an exit
                mov     al, [es:bx + 6]
                xor     ah, ah
                add     bx, ax
                add     bx, ax
                add     bx, ax
                add     bx, 7
                jmp     .each
.none:
                stc
                ret
.found:
                clc
                ret

section .data
vm_code:        dw      0
vm_sp:          dw      0
vm_stack_base:  dw      vm_stack
vm_depth:       db      0                       ; how many DO deep
vm_arg:         dw      0
vm_arg2:        dw      0
obj_seg:        dw      0
cond_seg:       dw      0
vm_skip:        db      0
vm_if_true:     db      0                       ; some IF came out true
vm_done:        db      0                       ; the turn is over
vm_over:        db      0                       ; the game is over
vm_moved:       db      0                       ; a way out was followed
vm_graphics:    db      1
vm_verb:        db      0
vm_noun1:       db      0
vm_noun2:       db      0
vm_adverb:      db      0
; Where each object's record is: an offset in the objects' segment, nought
; for no object.  Outside the saved game on purpose -- see
; z80/common/conditions.asm, where it cost a game its objects.
obj_entry:      times 256 dw 0

; Everything from here to vm_state_end is what a game amounts to, so it is
; what SAVE writes out and LOAD reads back, and in the same order as on every
; other machine: a game begins with the room the player is in.
vm_state:
vm_location:    dw      0
vm_max_weight:  db      250
vm_weight:      db      0
vm_seed:        dw      0A55Ah
vm_music:       db      0                       ; nothing writes it now
vm_stack:       times VM_STACK_DEPTH dw 0
vm_flags:       times FLAG_BYTES db 0
vm_counters:    times COUNTERS db 0
obj_loc:        times 256 dw 0                  ; where every object is now
vm_state_end:
VM_STATE_BYTES  equ vm_state_end - vm_state
section .text
