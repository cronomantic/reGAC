; MIT License, Copyright (c) 2025 Cronomantic
;
; Noises out of a sound chip: the click a key makes and the effects an
; adventure asks for, on every machine that has an AY.
;
; This is the other half of beep.asm.  A speaker of one bit makes a note by
; being flipped fast enough; a chip is told the period and makes it itself.
; What comes out is the same table read the same way -- effects.asm, whose
; numbers are the adventure's and not the machine's -- so an adventure that
; says SOUND 2 gets something refused-sounding wherever it is played.
;
; A pitch there is how long half a wave lasts, in sixteen cycle steps.  These
; chips count a period of sixteen of their own million a second, which is the
; same note at half the number: a pitch of two hundred is a period of a
; hundred.  So the same table lasts the same time and sounds the same note,
; and the waiting is counted the same way at the bottom of this file.
;
; Each machine says how its chip is reached, because that is all that differs:
;
;   ay_write        a routine putting E into register D, corrupting AF and BC
;   AY_MIXER_KEEP   the bits of register seven that are that machine's and
;                   must go out as they were: nought where the mixer is the
;                   whole byte, and on an MSX the top bit, which is not the
;                   mixer at all but which way round the chip's own ports face
;   AY_SOUNDS       whether SOUND is to work in this build
;
; That last one is the only place these two engines differ in what they carry.
; A speaker of one bit costs nothing to have, so beep.asm always brings the
; effects with it; a chip is reached through a routine, and the Amstrad -- the
; machine that counts bytes one by one -- would rather not carry a table and a
; player for an adventure that never says SOUND.  **The click is not part of
; that bargain**: GAC clicked on every key pressed, so ay_note and the click
; travel in every build, and what AY_SOUNDS buys is the table and the walk.
;
; WITH_NOISES is what the rest of the interpreter reads, and effects.asm keeps
; its table behind the same word.

                IFDEF AY_SOUNDS
                IFNDEF WITH_NOISES
                DEFINE WITH_NOISES 1
                ENDIF
                ENDIF


AY_TONE_A       equ 0                   ; the low byte of channel A's period
AY_TONE_A_HIGH  equ 1                   ; and the four bits above it
AY_MIXER        equ 7
AY_VOLUME_A     equ 8
AY_TONE_ONLY    equ %00111110 | AY_MIXER_KEEP   ; channel A's tone, nothing else
AY_LOUD         equ 15

                include "effects.asm"

; The chip made ready to sound one note: channel A's tone and nothing else,
; the top four bits of the period at nought, and the volume up.
; Corrupts: AF, BC, DE
ay_start:
                ld      de, (AY_MIXER << 8) | AY_TONE_ONLY
                call    ay_write
                ld      de, AY_TONE_A_HIGH << 8
                call    ay_write
                ld      de, (AY_VOLUME_A << 8) | AY_LOUD
                jp      ay_write

; Quiet again.  Only the volume is put back, and not the mixer: what the mixer
; had before this is the machine's own business -- a keyboard row on an
; Amstrad, a joystick on an MSX -- and ay_start left those bits alone.
; Corrupts: AF, BC, DE
ay_quiet:
                ld      de, AY_VOLUME_A << 8
                jp      ay_write

; A note that stays where it is: A the pitch, B how many half waves it lasts.
; The period goes out once and then it is only waiting, which is what makes
; this short enough to travel in every build -- the key click is a note like
; this one, and a machine clicks whether or not its adventure asks for noises.
; Corrupts: everything
ay_note:
                ld      c, a                    ; the pitch, kept
                push    bc
                call    ay_start
                pop     bc
                push    bc                      ; ay_write corrupts it too
                ld      a, c
                srl     a                       ; the chip's period is half
                ld      d, AY_TONE_A
                ld      e, a
                call    ay_write
                pop     bc
.each_wave:
                ld      a, c
                call    ay_wait
                djnz    .each_wave
                jp      ay_quiet

; The click a key makes.
; Corrupts: everything
beep_click:
                ld      a, CLICK_PITCH
                ld      b, CLICK_FLIPS
                jr      ay_note

                IFDEF WITH_NOISES
; Effect A, counting from one as the one bit engine counts them: the same
; table and the same numbers.  A number the build has not got makes no noise
; rather than reading past the table.
;
; Each is three bytes: the pitch it starts at, how many half waves it lasts,
; and what to add to the pitch every one -- which is what makes a blip rise or
; fall, and is a byte with a sign.  A walking pitch means the period goes out
; again every wave, which is why this is not ay_note with an argument.
; Corrupts: everything
beep_sound:
                or      a
                ret     z
                dec     a
                cp      BEEP_SOUNDS
                ret     nc
                ld      l, a
                ld      h, 0
                ld      d, h
                ld      e, l
                add     hl, hl
                add     hl, de                  ; three bytes to the effect
                ld      de, beep_effects
                add     hl, de
                ld      a, (hl)
                ld      (sound_pitch), a        ; where the note starts
                inc     hl
                ld      b, (hl)                 ; how many waves it lasts
                inc     hl
                ld      a, (hl)
                ld      (sound_step), a         ; and how the note moves
                ; B is how long it lasts and ay_start corrupts BC, so it is
                ; kept across the call.  **It was not, until this was read
                ; again**, and on the Amstrad -- the one machine this engine
                ; served -- every effect ran for however many steps the chip
                ; access happened to leave in B, which is $F6, instead of the
                ; number the table gives.  Nothing failed: a noise came out
                ; and the machine came back, which is all the test asked.  So
                ; the promise that the same table lasts the same time
                ; everywhere was not true there, and now it is.
                push    bc
                call    ay_start
                pop     bc
.each_wave:
                push    bc
                ld      a, (sound_pitch)
                srl     a
                ld      d, AY_TONE_A
                ld      e, a
                call    ay_write
                ld      a, (sound_pitch)
                call    ay_wait
                ; The note walks, and stops at the ends rather than going
                ; round: one that fell off the bottom would come back as the
                ; lowest growl there is.
                ld      a, (sound_step)
                or      a
                jr      z, .walked
                ld      hl, sound_pitch
                jp      m, .falling
                add     a, (hl)
                jr      nc, .keep
                ld      a, 255
                jr      .keep
.falling:
                add     a, (hl)
                jr      c, .keep                ; no borrow, so still in range
                ld      a, 1
.keep:
                ld      (sound_pitch), a
.walked:
                pop     bc
                djnz    .each_wave
                jp      ay_quiet

sound_pitch:    db      0
sound_step:     db      0
                ENDIF

; Wait as long as one half wave of the one bit engine would take, which is
; what makes the same table last the same time here: a step of that engine is
; this loop's sixteen cycles, counted the same number of times.  A pitch of
; nought would not wait at all, so it waits once.
; Corrupts: AF, E
ay_wait:
                or      a
                jr      nz, .go
                inc     a
.go:
                ld      e, a
.each:
                dec     e
                jr      nz, .each
                ret
