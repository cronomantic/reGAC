; MIT License, Copyright (c) 2025 Cronomantic
;
; Noises out of a PC's speaker: the click a key makes and the effects an
; adventure asks for with SOUND.
;
; The speaker is one bit, as the Spectrum 48's is, so this is that machine's
; engine, z80/common/beep.asm, with the same table and the same lengths: flip
; the speaker, wait half a wave, flip it back, as many times as the note
; lasts, the pitch walking as it goes.  What is not the Spectrum's is how long
; a wait is.  There it is counted in the processor's cycles, and a PC's
; processor may be any speed at all; so here it is counted on the timer, which
; is the same on every one (see timer.asm), and a pitch lasts what it lasted on
; a Spectrum: sixteen of its cycles at 3.5 MHz a step, which is sixty
; elevenths of the timer's.
;
; The speaker is port 61h's bit one, with bit nought, which would give it to
; the timer's third counter, left off.  The fourth byte of an effect -- tone,
; noise or both -- is read past, as on the Spectrum: a speaker of one bit has
; the one thing it can do.

SPEAKER_PORT    equ 61h
SPEAKER_BITS    equ 03h                 ; the bit it is moved by, and the gate
SPEAKER_MOVE    equ 02h
CLICK_PITCH     equ 200
CLICK_FLIPS     equ 20

OUT_OF_TONE     equ 0
OUT_OF_NOISE    equ 1
OUT_OF_BOTH     equ 2

; The timer's clocks half a wave of pitch AL lasts: AL times sixty elevenths.
; Corrupts: AX, DX
half_wave:
                push    bx
                mov     ah, 60
                mul     ah
                xor     dx, dx
                mov     bx, 11
                div     bx
                pop     bx
                ret

; Play a note: AL the pitch, CL how many times the speaker moves.
; Corrupts: everything but DS
beep_note:
                mov     ch, 0
                call    half_wave
                mov     bx, ax
                in      al, SPEAKER_PORT
                and     al, ~SPEAKER_BITS
                mov     [speaker_rest], al      ; the port, speaker at rest
                call    beat_start
                xor     ax, ax
                mov     [flip_at], ax           ; when the next flip is due
                mov     [flip_at + 2], ax
.each_flip:
                jcxz    .done
                mov     al, [speaker_rest]
                xor     al, SPEAKER_MOVE
                mov     [speaker_rest], al
                out     SPEAKER_PORT, al
                add     [flip_at], bx
                adc     word [flip_at + 2], 0
                mov     ax, [flip_at]
                mov     dx, [flip_at + 2]
                call    beat_until
                dec     cx
                jmp     .each_flip
.done:
                mov     al, [speaker_rest]      ; and leave it where it was
                and     al, ~SPEAKER_BITS
                out     SPEAKER_PORT, al
                ret

; The click a key makes, which the original asked the ROM for at every one.
; Corrupts: everything but DS
beep_click:
                mov     al, CLICK_PITCH
                mov     cl, CLICK_FLIPS
                jmp     beep_note

; Effect AL, counting from one.  A number the build has not got makes no
; noise rather than reading past the table.  The pitch walks by the third
; byte every flip, and stops at the ends rather than going round.
; Corrupts: everything but DS
beep_sound:
                test    al, al
                jz      .none
                dec     al
                cmp     al, BEEP_SOUNDS
                jae     .none
                xor     ah, ah
                mov     si, ax
                shl     si, 1
                shl     si, 1                   ; four bytes to the effect
                add     si, beep_effects
                mov     bl, [si]                ; the pitch as it stands
                mov     cl, [si + 1]            ; how long
                xor     ch, ch
                mov     bh, [si + 2]            ; and how it moves
                in      al, SPEAKER_PORT
                and     al, ~SPEAKER_BITS
                mov     [speaker_rest], al
                call    beat_start
                xor     ax, ax
                mov     [flip_at], ax
                mov     [flip_at + 2], ax
.each_flip:
                jcxz    .done
                mov     al, [speaker_rest]
                xor     al, SPEAKER_MOVE
                mov     [speaker_rest], al
                out     SPEAKER_PORT, al
                mov     al, bl
                test    al, al
                jnz     .some
                inc     al                      ; never nothing at all
.some:
                call    half_wave               ; AX, the clocks it lasts
                add     [flip_at], ax
                adc     word [flip_at + 2], 0
                mov     ax, [flip_at]
                mov     dx, [flip_at + 2]
                call    beat_until
                mov     al, bh
                test    al, al
                jns     .rising
                add     al, bl
                jc      .walked                 ; no borrow, so still in range
                mov     al, 1
                jmp     .walked
.rising:
                add     al, bl
                jnc     .walked
                mov     al, 255
.walked:
                mov     bl, al
                dec     cx
                jmp     .each_flip
.done:
                mov     al, [speaker_rest]
                and     al, ~SPEAKER_BITS
                out     SPEAKER_PORT, al
.none:
                ret

section .data
speaker_rest:   db      0               ; what port 61h holds, speaker and all
flip_at:        dd      0               ; the clocks from the note's start
; The noises an adventure can ask for: see z80/common/effects.asm, whose
; table this is.  An adventure may say what noises it wants, and then regac
; writes them into a file of their own that comes in here instead.
beep_effects:
                %ifdef WITH_OWN_NOISES
                %include NOISES_FILE
                %else
                db      200, 150, -1, OUT_OF_TONE   ; 1: taken, rising
                db      60, 150, 1, OUT_OF_TONE     ; 2: refused, falling
                db      250, 100, 0, OUT_OF_BOTH    ; 3: a door: wood and air
                db      30, 110, 2, OUT_OF_NOISE    ; 4: a fall, high to low
                db      60, 200, 0, OUT_OF_BOTH     ; 5: alarm, harsh
                %endif
BEEP_SOUNDS     equ ($ - beep_effects) / 4
section .text
