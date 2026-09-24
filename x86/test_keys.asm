; MIT License, Copyright (c) 2025 Cronomantic
;
; A test build for what is timed on a PC: the keyboard's rules, HOLD, and the
; speaker's noises.  tests/test_keyboard_pc.py and tests/test_sound_pc.py
; build it, run it, and read what it wrote.
;
; The keyboard is not the machine's here but a script's: DOSBox-X can only
; press a key and let it go at once, and the rules are about keys that are
; held and keys pressed over each other.  So the interrupt is not taken, and
; what is down is set a frame at a time from KEYS.BIN -- four bytes an event:
; the frame it happens on, the key, and the character it says, nought for
; letting it go -- underneath next_key, wait_or_key and scan_keyboard, which
; are the interpreter's own and do not know the difference.
;
;   -DSCRIPTED_KEYS -DKEYS_TEST   every key next_key gives, and on what frame,
;                                 to KEYS.OUT, three bytes a key
;   -DSCRIPTED_KEYS -DHOLD_TEST   how long wait_or_key waits for HOLD_FRAMES
;                                 fiftieths with nothing pressed, to HOLD.OUT
;   -DSCRIPTED_KEYS -DSOUND_TEST  how long the click and each noise last, to
;                                 SOUND.OUT
;
; A time is four bytes: the timer's clocks, 1193182 a second.

bits 16
cpu 8086

MOST_KEYS       equ 256
BIOS_SEGMENT    equ 40h
BIOS_TICKS      equ 6Ch

section .text start=0
section .data follows=.text align=16 vstart=0
data_start:
section .text

start:
                mov     ax, cs
                add     ax, DATA_PARAGRAPH
                mov     ds, ax
                cld
                call    timer_init
                %ifdef KEYS_TEST
                call    read_script
.each_key:
                call    next_key                ; script_frame ends it all
                mov     bx, [keys_at]
                cmp     bx, MOST_KEYS * 3
                jae     .each_key
                mov     [keys_out + bx], al
                mov     ax, [frame_now]
                mov     [keys_out + bx + 1], ax
                add     word [keys_at], 3
                jmp     .each_key
                %endif
                %ifdef HOLD_TEST
                call    clock_now
                mov     ax, HOLD_FRAMES
                call    wait_or_key
                call    clock_since
                mov     dx, hold_name
                mov     si, clock_out
                mov     cx, 4
                call    write_file
                jmp     finish
                %endif
                %ifdef SOUND_TEST
                call    clock_now
                call    beep_click
                call    clock_since
                call    keep_clock
                mov     byte [effect], 1
.each_effect:
                mov     al, [effect]
                cmp     al, BEEP_SOUNDS
                ja      .effects_done
                call    clock_now
                mov     al, [effect]
                call    beep_sound
                call    clock_since
                call    keep_clock
                inc     byte [effect]
                jmp     .each_effect
.effects_done:
                mov     dx, sound_name
                mov     si, keys_out
                mov     cx, [keys_at]
                call    write_file
                jmp     finish
                %endif

finish:
                call    timer_done
                mov     ax, 4C00h
                int     21h

; What the interpreter's waits call and this build has nothing for.
flash_frame:
                ret

; -- the script ---------------------------------------------------------------

; A frame has gone by: the script's events of this frame happen, and once it
; has been over a while the keys given so far are written and the program
; ends.  See script.asm.
; Corrupts: nothing but AX
script_frame:
                call    script_step
                jnc     .going
                %ifdef KEYS_TEST
                mov     dx, keys_name
                mov     si, keys_out
                mov     cx, [keys_at]
                call    write_file
                jmp     finish
                %endif
.going:
                ret

; -- timing -------------------------------------------------------------------

; The time now, in clock_then, as the BIOS's ticks and the timer's count.
clock_now:
                call    clock_read
                mov     [clock_then], ax
                mov     [clock_then + 2], dx
                ret

; The ticks in DX and the count in AX, read so that the two agree.
clock_read:
                push    es
                mov     ax, BIOS_SEGMENT
                mov     es, ax
.again:
                sti
                mov     dx, [es:BIOS_TICKS]
                call    timer_read
                cmp     dx, [es:BIOS_TICKS]
                jne     .again
                pop     es
                ret

; The clocks since clock_now, in clock_out.
clock_since:
                call    clock_read
                mov     bx, [clock_then]        ; the count then, less now,
                sub     bx, ax                  ; since it counts down
                mov     ax, 0
                sbb     ax, 0                   ; less one if that borrowed
                mov     cx, dx
                sub     cx, [clock_then + 2]    ; and a turn for every tick
                add     cx, ax
                mov     [clock_out], bx
                mov     [clock_out + 2], cx
                ret

; Keep clock_out in the list.
keep_clock:
                mov     bx, [keys_at]
                mov     ax, [clock_out]
                mov     [keys_out + bx], ax
                mov     ax, [clock_out + 2]
                mov     [keys_out + bx + 2], ax
                add     word [keys_at], 4
                ret

; CX bytes from DS:SI into the file named at DS:DX.
write_file:
                push    cx
                push    si
                mov     ah, 3Ch
                xor     cx, cx
                int     21h
                pop     dx
                pop     cx
                jc      .failed
                mov     bx, ax
                mov     ah, 40h
                int     21h
                mov     ah, 3Eh
                int     21h
.failed:
                ret

section .data
keys_name:      db      "KEYS.OUT", 0
hold_name:      db      "HOLD.OUT", 0
sound_name:     db      "SOUND.OUT", 0
keys_at:        dw      0
effect:         db      0
clock_then:     dd      0
clock_out:      dd      0
keys_out:       times MOST_KEYS * 4 db 0
section .text

; What the waits and the noises need of the interpreter, and no more.
SPACE_CODE      equ 32
NO_CHARACTER    equ 0FFh
ascii_to_code:
                ret
print_char:
new_line:
backspace:
                ret
%include "script.asm"
%include "timer.asm"
%include "keyboard.asm"
%include "sound.asm"

section .text
code_end:
section .data
data_end:
section .text
DATA_PARAGRAPH  equ (code_end - start + 15) >> 4
