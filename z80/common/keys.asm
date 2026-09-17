; MIT License, Copyright (c) 2025 Cronomantic
;
; Which key has just been typed, the way the Spectrum's ROM decides it, on
; every machine.
;
; The original waited for the ROM to say a key was new and read which one it
; was, so what counts as typing a key is the ROM's, and it was measured on the
; original rather than taken on trust: L, O and K typed each before the one
; before it was let go come out as LOK, and a key held for two seconds comes
; out six times over.  What this had before -- wait for the keyboard to come
; clear, then wait for a key -- lost every key pressed before the last one was
; let go, which is only typing quickly.
;
; The rules, which are the ROM's:
;
;   - a key that is not the one last typed is typed at once, whether or not
;     that one is still held;
;   - while two keys that are not shifts are held nothing is decided at all,
;     so the one that stays down is not typed again when the other goes up;
;   - a key let go is forgotten five frames later, so a key that bounces is
;     typed once;
;   - a key held is typed again after thirty five frames, and then every five.
;
; The machine's scan_keyboard gives the key in A, zero for none, and leaves in
; key_count how many keys that are not shifts it saw.  A frame is
; LOOKS_A_FRAME looks at the keyboard, as it is for the wait in HOLD, while
; the last look found nothing, and LOOKS_HELD while it found a key: a look
; that finds one costs more, and counted in the other it made a key held on a
; Spectrum repeat a third late.

KEY_FORGET      equ 5                   ; frames, as the ROM counts them
KEY_DELAY       equ 35
KEY_EVERY       equ 5

; Wait for a key to be typed and give it back in A.
; Corrupts: everything
next_key:
                ld      c, 0                    ; nothing seen yet
.each_frame:
                ld      b, LOOKS_A_FRAME
                inc     c
                dec     c
                jr      z, .look
                ld      b, LOOKS_HELD
.look:
                push    bc
                call    scan_keyboard
                pop     bc
                ld      c, a
                ld      a, (key_count)
                cp      2
                jr      nc, .keep_looking       ; two at once: wait and see
                ld      a, c
                or      a
                jr      z, .keep_looking
                ld      hl, held_key
                cp      (hl)
                jr      z, .still_held
                ld      (hl), a                 ; a new one
                ld      a, KEY_DELAY
                ld      (key_repeat), a
                ld      a, KEY_FORGET
                ld      (key_forget), a
                ld      a, c
                ret
.still_held:
                ld      a, KEY_FORGET
                ld      (key_forget), a
.keep_looking:
                djnz    .look
                ; the frame is over, and what the last look saw decides it
                ld      a, (key_count)
                cp      2
                jr      nc, .each_frame
                ld      a, c
                or      a
                jr      z, .let_go
                ld      hl, key_repeat
                dec     (hl)
                jr      nz, .each_frame
                ld      (hl), KEY_EVERY
                ret                             ; A is the key, held long enough
.let_go:
                ld      hl, key_forget
                ld      a, (hl)
                or      a
                jr      z, .each_frame
                dec     (hl)
                jr      nz, .each_frame
                ld      (held_key), a           ; forgotten: A is nought
                jr      .each_frame

held_key:       db      0
key_forget:     db      0
key_repeat:     db      0
key_count:      db      0
