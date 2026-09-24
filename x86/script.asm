; MIT License, Copyright (c) 2025 Cronomantic
;
; Keys from a script instead of from the keyboard, for the tests.
;
; A build with SCRIPTED_KEYS does not take the keyboard's interrupt: what is
; down is set a frame at a time from KEYS.BIN, underneath the interpreter's
; own next_key, wait_or_key and scan_keyboard, which do not know the
; difference.  Four bytes an event: the frame it happens on, the key, and the
; character it says, nought for letting it go.  The script ends at a frame of
; 0FFFFh.
;
; Frames are counted only while the interpreter waits for a key or holds --
; that is where frame_gone is called -- so a script's frames are the time the
; game spends asking, and what it does in between, drawing or printing, takes
; none of them: a key comes when the game is waiting for one, every time.
;
; Two builds use it: x86/test_keys.asm, for the keyboard's rules, and the game
; built for tests/pc_game.py, so that a game played by the tests is played the
; same way every time.  DOSBox-X's own typing, AUTOTYPE, drives the machine's
; keyboard from a thread of its own with nothing to keep it in step, and now
; and then stops sending keys at all: see doc/pendiente.md.

SCRIPT_EVENTS   equ 512
SCRIPT_TAIL     equ 100                 ; frames after the last, to be over

; Read KEYS.BIN.
; Corrupts: AX, BX, CX, DX
read_script:
                mov     ax, 3D00h
                mov     dx, script_name
                int     21h
                jc      .none
                mov     bx, ax
                mov     ah, 3Fh
                mov     cx, SCRIPT_EVENTS * 4
                mov     dx, script
                int     21h
                mov     ah, 3Eh
                int     21h
.none:
                ret

; A frame has gone by: every event of this frame happens.  Carry set when the
; script has been over for SCRIPT_TAIL frames.
; Corrupts: nothing but AX
script_step:
                push    bx
                push    si
                inc     word [frame_now]
                mov     si, [script_at]
.each:
                mov     ax, [script + si]
                cmp     ax, 0FFFFh
                je      .ended
                cmp     ax, [frame_now]
                ja      .going
                mov     bl, [script + si + 2]   ; the key
                and     bx, 7Fh
                mov     al, [script + si + 3]   ; what it says, or let go
                test    al, al
                jz      .up
                mov     byte [key_down + bx], 1
                mov     [key_char + bx], al
                jmp     .next
.up:
                mov     byte [key_down + bx], 0
.next:
                add     si, 4
                mov     [script_at], si
                jmp     .each
.ended:
                xor     ax, ax
                test    si, si
                jz      .no_events
                mov     ax, [script + si - 4]   ; the last event's frame
.no_events:
                neg     ax
                add     ax, [frame_now]
                cmp     ax, SCRIPT_TAIL
                jb      .going
                stc
                jmp     .done
.going:
                clc
.done:
                pop     si
                pop     bx
                ret

section .data
script_name:    db      "KEYS.BIN", 0
frame_now:      dw      0
script_at:      dw      0
script:         times SCRIPT_EVENTS * 4 db 0
                dw      0FFFFh
section .text
