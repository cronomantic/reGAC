; MIT License, Copyright (c) 2025 Cronomantic
;
; The clock the waits are counted by: fiftieths of a second, which is the
; frame every other machine counts in -- how long HOLD holds, when a held key
; repeats, when an ink flashes.
;
; The one clock every PC has at the same speed is the timer's first counter,
; which counts down at 1193182 a second whatever the processor is: an XT, a
; turbo clone and a Pentium count the same.  It is left giving the BIOS its
; eighteen ticks a second, as it always does, and only changed from the mode
; the BIOS leaves it in -- which counts down by twos, twice a turn -- to the one
; that counts by ones, once: the same ticks, but a reading that says how long
; since the last.  The difference between two readings is the time between
; them as long as they are less than a turn apart, a eighteenth of a second,
; and every wait reads it far oftener than that.
;
; Put back as it was when the interpreter goes.

PIT_COUNTER0    equ 40h
PIT_CONTROL     equ 43h
PIT_RATE        equ 34h                 ; counter nought, both bytes, mode two
PIT_SQUARE      equ 36h                 ; and mode three, the BIOS's
PIT_LATCH0      equ 00h                 ; hold counter nought's count to read
FRAME_CLOCKS    equ 23864               ; 1193182 / 50

; Corrupts: AX
timer_init:
                mov     al, PIT_RATE
                jmp     timer_mode
timer_done:
                mov     al, PIT_SQUARE
timer_mode:
                cli
                out     PIT_CONTROL, al
                xor     al, al                  ; a count of 65536, as the BIOS
                out     PIT_COUNTER0, al        ; has it: its ticks stay the same
                out     PIT_COUNTER0, al
                sti
                ret

; The counter as it stands, in AX.  It counts down.
; Corrupts: nothing else
timer_read:
                pushf
                cli
                mov     al, PIT_LATCH0
                out     PIT_CONTROL, al
                in      al, PIT_COUNTER0
                mov     ah, al
                in      al, PIT_COUNTER0
                xchg    al, ah
                popf
                ret

; Start counting frames from now.
; Corrupts: AX
frames_start:
                call    timer_read
                mov     [timer_last], ax
                mov     word [timer_owed], 0
                ret

; Whether a frame has gone by since the last one this said so: carry set if
; one has.  A long gap is owed and paid back a frame a call.
; Corrupts: AX
frame_gone:
                push    dx
                call    timer_read
                mov     dx, [timer_last]
                mov     [timer_last], ax
                sub     dx, ax                  ; how far it has counted down
                add     [timer_owed], dx
                jnc     .counted
                mov     word [timer_owed], 0FFFFh       ; as much as it holds
.counted:
                pop     dx
                cmp     word [timer_owed], FRAME_CLOCKS
                jb      .not_yet
                sub     word [timer_owed], FRAME_CLOCKS
                %ifdef SCRIPTED_KEYS
                call    script_frame            ; a test's keys, a frame on
                %endif
                stc
                ret
.not_yet:
                clc
                ret

; Wait AX clocks of the counter, the fine grain the speaker is timed in.
; Corrupts: AX
wait_clocks:
                push    bx
                push    dx
                mov     bx, ax
                call    timer_read
                mov     dx, ax
.waiting:
                call    timer_read
                neg     ax
                add     ax, dx                  ; how far since the start
                cmp     ax, bx
                jb      .waiting
                pop     dx
                pop     bx
                ret

section .data
timer_last:     dw      0
timer_owed:     dw      0
section .text
