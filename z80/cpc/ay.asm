; MIT License, Copyright (c) 2025 Cronomantic
;
; The noises of an Amstrad, which are the same noises every
; other machine makes and are made another way.
;
; This machine has no speaker of its own: the only thing here that can make a
; sound is the AY, and getting at it is the dance the keyboard already does --
; the chip is behind the same eight two five five, told what it is being
; handed by two bits of port C.  So where a Spectrum flips a bit of a port
; fast enough to be a note, this asks the chip for the note and waits.
;
; What it plays is effects.asm, the same table read the same way, so an
; adventure that says SOUND 2 gets something refused-sounding here as well.
; A pitch there is how long half a wave lasts in sixteen cycle steps; this
; machine's chip counts a period of sixteen of its own million a second, which
; is the same note at half the number -- a pitch of two hundred is a period of
; a hundred.

                IFNDEF WITH_NOISES
                DEFINE WITH_NOISES 1
                ENDIF

AY_TONE_A       equ 0                   ; the low byte of channel A's period
AY_TONE_A_HIGH  equ 1                   ; and the four bits above it
AY_MIXER        equ 7
AY_VOLUME_A     equ 8
AY_TONE_ONLY    equ %00111110           ; channel A's tone, and nothing else
AY_LOUD         equ 15

                include "../common/effects.asm"

; Put E into the chip's register D.
;
; The dance is the keyboard's: port A outwards, the byte on it, and port C
; told what the byte was for -- $C0 to choose a register, $80 to give it a
; value, and $00 to let go in between.
; Corrupts: AF, BC
ay_write:
                ld      bc, $F782
                out     (c), c                  ; port A outwards
                ld      b, $F4
                out     (c), d                  ; the register number
                ld      bc, $F6C0
                out     (c), c                  ; that was a register
                ld      bc, $F600
                out     (c), c
                ld      b, $F4
                out     (c), e                  ; the value
                ld      bc, $F680
                out     (c), c                  ; and that was its value
                ld      bc, $F600
                out     (c), c
                ret

; Quiet again.
; Corrupts: AF, BC, DE
ay_quiet:
                ld      de, AY_VOLUME_A << 8
                jp      ay_write

; Effect A, counting from one as the one bit engine counts them: the same
; table and the same numbers.  A number the
; build has not got makes no noise rather than reading past the table.
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
                ld      b, (hl)                 ; how many steps it lasts
                inc     hl
                ld      a, (hl)
                ld      (sound_step), a         ; and how the note moves

                ld      de, (AY_MIXER << 8) | AY_TONE_ONLY
                call    ay_write
                ld      de, AY_TONE_A_HIGH << 8 ; the top four bits of the
                call    ay_write                ; period, which stay at nought
                ld      de, (AY_VOLUME_A << 8) | AY_LOUD
                call    ay_write
.each_step:
                push    bc
                ld      a, (sound_pitch)
                srl     a                       ; the chip's period is half
                ld      d, AY_TONE_A
                ld      e, a
                call    ay_write
                ld      a, (sound_pitch)
                call    wait_a_while
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
                djnz    .each_step
                jp      ay_quiet

; Wait as long as one half wave of the one bit engine would take, which is
; what makes the same table last the same time here: a step of that engine is
; this loop's sixteen cycles, counted the same number of times.
; Corrupts: AF, E
wait_a_while:
                ld      e, a
.each:
                dec     e
                jr      nz, .each
                ret

sound_pitch:    db      0
sound_step:     db      0
