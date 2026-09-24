; MIT License, Copyright (c) 2025 Cronomantic
;
; Reading the keyboard on a PC, by the Spectrum ROM's rules as every machine
; does: z80/common/keys.asm, and z80/cpc/keyboard.asm for the rest.
;
; Those rules need to know which keys are down, all of them and at every
; moment, and a PC's BIOS only hands over characters, with a repeat of its
; own.  So the keyboard's interrupt is taken: every key that goes down or up
; is noted, and then the BIOS's own handler is called as it always was, which
; is what turns a key into a character -- with the shifts, and with whatever
; layout DOS was given, KEYB SP or any other.  The character it made is taken
; out of its buffer at once and kept against the key.  So which key is down is
; ours, and what it says is the PC's.
;
; Letters come back in capitals, because the vocabulary is kept that way, and
; only what an adventure can print is kept: from the space to the tilde, and
; the enter and the delete.
;
; Put back as it was when the interpreter goes.

KEY_ENTER       equ 13
KEY_DELETE      equ 8
INPUT_MAX       equ 64                  ; as much of a line as is kept
KEYBOARD_DATA   equ 60h
KEY_RELEASED    equ 80h
KEY_PREFIX      equ 0E0h                ; the grey keys say this first
KEY_PAUSE       equ 0E1h                ; and pause this, and two more
BIOS_SEGMENT    equ 40h
BIOS_BUFFER_HEAD equ 1Ah
BIOS_BUFFER_TAIL equ 1Ch
BIOS_BUFFER_START equ 80h
BIOS_BUFFER_END equ 82h
OLD_BUFFER_START equ 1Eh
OLD_BUFFER_END  equ 3Eh
ENTER_KEY       equ 1Ch                 ; the codes of the white enter
SLASH_KEY       equ 35h                 ; and slash
DOS_SET_VECTOR  equ 25h
DOS_GET_VECTOR  equ 35h

KEY_FORGET      equ 5                   ; frames, as the ROM counts them
KEY_DELAY       equ 35
KEY_EVERY       equ 5

; Take the keyboard's interrupt, and tell DOS that neither a break nor a disk
; that will not answer may end the program behind our back: either would
; leave the interrupt pointing into memory that is no longer ours.
; Corrupts: AX, BX, DX, ES
keyboard_init:
                mov     [cs:isr_data], ds
                %ifndef SCRIPTED_KEYS                   ; a test's keys: see
                mov     ax, (DOS_GET_VECTOR << 8) | 09h ; script.asm
                int     21h
                mov     [old_int9], bx
                mov     [old_int9 + 2], es
                %endif
                push    ds
                push    cs
                pop     ds
                %ifndef SCRIPTED_KEYS
                mov     dx, keyboard_isr
                mov     ax, (DOS_SET_VECTOR << 8) | 09h
                int     21h
                %endif
                mov     dx, ignore_break
                mov     ax, (DOS_SET_VECTOR << 8) | 23h
                int     21h
                mov     dx, fail_the_call
                mov     ax, (DOS_SET_VECTOR << 8) | 24h
                int     21h
                pop     ds
                ret

; And give it back.  DOS puts back the other two itself.
; Corrupts: AX, DX
keyboard_done:
                %ifndef SCRIPTED_KEYS
                push    ds
                lds     dx, [old_int9]
                mov     ax, (DOS_SET_VECTOR << 8) | 09h
                int     21h
                pop     ds
                %endif
                ret

; A break is not ours to act on.
ignore_break:
                iret

; A disk that does not answer fails the call, which the save and the load
; then say nothing about, as the tape does.
fail_the_call:
                mov     al, 3
                iret

; The keyboard's interrupt.
;
; A key that goes down is marked down, and pressed as well: pressed stays
; until the next look at the keyboard has seen it, so that a key pressed and
; let go while nobody was looking -- the interpreter drawing, or clicking for
; the key before -- is still typed once.  A person can type a key that short;
; DOSBox-X's AUTOTYPE does, every time, and that is how it was found.
;
; What the key says is taken out of the BIOS's buffer, where each entry is the
; key's code in its high byte and the character in its low one, so each goes
; to its own key.  It used to go to "the key last pressed", and the BIOS's
; handler lets interrupts in before it ends: a second key coming in there
; took the first one's character, and a typed N came out as the letter of
; the key behind it.
keyboard_isr:
                push    ax
                push    bx
                push    si
                push    ds
                push    es
                mov     ds, [cs:isr_data]
                in      al, KEYBOARD_DATA
                %ifdef TRANSCRIPT
                inc     word [codes_seen]       ; for a test: see game.asm
                %endif
                cmp     byte [pause_left], 0
                je      .not_pause
                dec     byte [pause_left]       ; the rest of pause says nothing
                jmp     .bios
.not_pause:
                cmp     al, KEY_PAUSE
                jne     .not_pause_key
                mov     byte [pause_left], 2
                jmp     .bios
.not_pause_key:
                cmp     al, KEY_PREFIX
                je      .bios                   ; the key comes next
                mov     bl, al
                and     bx, 7Fh
                test    al, KEY_RELEASED
                jz      .down
                mov     byte [key_down + bx], 0
                jmp     .bios
.down:
                mov     byte [key_down + bx], 1
                mov     byte [key_pressed + bx], 1
.bios:
                pushf
                call    far [old_int9]
                ; whatever the BIOS made of it, out of its buffer, with nothing
                ; let in while the head moves
                cli
                mov     ax, BIOS_SEGMENT
                mov     es, ax
.drain:
                mov     si, [es:BIOS_BUFFER_HEAD]
                cmp     si, [es:BIOS_BUFFER_TAIL]
                je      .drained
                mov     ax, [es:si]             ; the key's code, the character
                add     si, 2
                ; Where the buffer ends and starts again.  A BIOS from before
                ; the AT keeps it at 1Eh to 3Eh and does not say so: the two
                ; words that say it are nought there.
                mov     bx, [es:BIOS_BUFFER_END]
                test    bx, bx
                jnz     .told
                mov     bx, OLD_BUFFER_END
.told:
                cmp     si, bx
                jb      .in_range
                mov     si, [es:BIOS_BUFFER_START]
                test    si, si
                jnz     .in_range
                mov     si, OLD_BUFFER_START
.in_range:
                mov     [es:BIOS_BUFFER_HEAD], si
                ; The grey enter and the grey slash come as E0 with their
                ; character; they are the same keys to us as the white ones.
                cmp     ah, KEY_PREFIX
                jne     .own_code
                mov     ah, ENTER_KEY
                cmp     al, KEY_ENTER
                je      .own_code
                mov     ah, SLASH_KEY
.own_code:
                mov     bl, ah
                and     bx, 7Fh
                jz      .drain                  ; no key: typed at the keypad
                call    worth_keeping
                mov     [key_char + bx], al
                jmp     .drain
.drained:
                pop     es
                pop     ds
                pop     si
                pop     bx
                pop     ax
                iret

; What a character the BIOS made is to this interpreter, in AL: itself in
; capitals, or nought for nothing worth having.
worth_keeping:
                cmp     al, KEY_ENTER
                je      .keep
                cmp     al, KEY_DELETE
                je      .keep
                cmp     al, SPACE_CODE
                jb      .nothing
                cmp     al, '~'
                ja      .nothing
                cmp     al, 'a'
                jb      .keep
                cmp     al, 'z'
                ja      .keep
                sub     al, 'a' - 'A'
.keep:
                ret
.nothing:
                xor     al, al
                ret

; Look once at the whole keyboard.  The character comes back in AL, nought
; for none; key_count is how many keys that say something are down, and
; key_found which key the last of them is.  A shift says nothing, and neither
; does a cursor or a function key, as on the Amstrad.
; Corrupts: BX
scan_keyboard:
                push    cx
                xor     al, al
                mov     [key_count], al
                mov     [key_found], al
                xor     bx, bx
                mov     cx, 128
                cli                             ; down and pressed, as one
.each:
                mov     ah, [key_down + bx]
                or      ah, [key_pressed + bx]  ; pressed since the last look
                mov     [key_pressed + bx], al  ; which this is
                jz      .next
                cmp     byte [key_char + bx], 0
                je      .next
                inc     byte [key_count]
                mov     [key_found], bl
.next:
                inc     bx
                loop    .each
                sti
                mov     bl, [key_found]
                test    bl, bl
                jz      .none
                mov     al, [key_char + bx]
.none:
                pop     cx
                ret

; Wait for a key to be typed and give it back in AL, by the ROM's rules: a key
; that is not the one last typed is typed at once; while two are held nothing
; is decided; a key let go is forgotten five frames later; a key held is typed
; again after thirty five frames and then every five.  See z80/common/keys.asm,
; where each was measured on the original.
; Corrupts: everything but DS
next_key:
                call    frames_start
                xor     dl, dl                  ; what the last look found
.look:
                call    scan_keyboard
                mov     dl, al
                cmp     byte [key_count], 2
                jae     .keep_looking           ; two at once: wait and see
                test    al, al
                jz      .keep_looking
                ; which key it is decides, not what it says
                mov     ah, [key_found]
                cmp     ah, [held_key]
                je      .still_held
                mov     [held_key], ah          ; a new one
                mov     byte [key_repeat], KEY_DELAY
                mov     byte [key_forget], KEY_FORGET
                ret
.still_held:
                mov     byte [key_forget], KEY_FORGET
.keep_looking:
                call    frame_gone
                jnc     .look
                call    flash_frame
                ; the frame is over, and what the last look saw decides it
                cmp     byte [key_count], 2
                jae     .look
                test    dl, dl
                jz      .let_go
                dec     byte [key_repeat]
                jnz     .look
                mov     byte [key_repeat], KEY_EVERY
                mov     al, dl
                ret                             ; held long enough
.let_go:
                cmp     byte [key_forget], 0
                je      .look
                dec     byte [key_forget]
                jnz     .look
                mov     byte [held_key], 0      ; forgotten
                jmp     .look

; Wait for a key to be typed and give it back in AL, with the click the
; original made at every one.
; Corrupts: everything but DS
read_key:
                call    next_key
                push    ax
                call    beep_click
                pop     ax
                ret

; Wait for a key, or for AX fiftieths of a second, whichever comes first.
; What is already held when the wait starts does not count, or the enter that
; ended the order would end the wait as well.
; Corrupts: everything but DS
wait_or_key:
                mov     dx, ax
                call    frames_start
                xor     cl, cl                  ; nothing let go yet
.each:
                test    dx, dx
                jz      .done                   ; the time went
                call    scan_keyboard
                test    al, al
                jnz     .something
                mov     cl, 1                   ; the keyboard came clear
                jmp     .keep_looking
.something:
                test    cl, cl
                jnz     .done                   ; a key, after it came clear
.keep_looking:
                call    frame_gone
                jnc     .each
                call    flash_frame
                dec     dx
                jmp     .each
.done:
                ret

; Read a line into input_buffer, as this adventure's codes: DS:SI at them and
; how many in CX.  What is typed is shown as it goes.
; Corrupts: everything but DS
read_line:
                %ifdef TRANSCRIPT
                call    transcript_screen       ; for a test, what was shown
                %endif
                mov     byte [line_length], 0
.next_key:
                call    read_key
                cmp     al, KEY_ENTER
                je      .finished
                cmp     al, KEY_DELETE
                je      .rub_out
                cmp     al, SPACE_CODE
                jb      .next_key               ; nothing else is worth having
                cmp     byte [line_length], INPUT_MAX
                jae     .next_key               ; the line is full
                call    store_key
                jmp     .next_key
.rub_out:
                cmp     byte [line_length], 0
                je      .next_key
                dec     byte [line_length]
                call    backspace
                jmp     .next_key
.finished:
                call    new_line
                mov     cl, [line_length]
                xor     ch, ch
                mov     si, input_buffer
                ret

; Put the character in AL into the line and show it.
; Corrupts: everything but DS
store_key:
                call    ascii_to_code
                cmp     al, NO_CHARACTER
                je      .none                   ; not a character this one has
                mov     bl, [line_length]
                xor     bh, bh
                mov     [input_buffer + bx], al
                inc     byte [line_length]
                jmp     print_char
.none:
                ret

; Where the interrupt finds the interpreter's data: written in the code, which
; is the one thing it can reach before it has any.
isr_data:       dw      0

section .data
old_int9:       dd      0
key_down:       times 128 db 0          ; which keys are down
key_pressed:    times 128 db 0          ; which went down since the last look
key_char:       times 128 db 0          ; and what each says
pause_left:     db      0
                %ifdef TRANSCRIPT
codes_seen:     dw      0               ; every code the keyboard sent
                %endif
key_found:      db      0
key_count:      db      0
held_key:       db      0
key_forget:     db      0
key_repeat:     db      0
line_length:    db      0
input_buffer:   times INPUT_MAX db 0
section .text
