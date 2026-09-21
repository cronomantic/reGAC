; MIT License, Copyright (c) 2025 Cronomantic
;
; Noises out of a one bit speaker: the click a key makes and a handful of
; effects for machines with no sound chip, or with one that nothing is playing.
;
; The original did this too, and it is worth saying where that was found,
; because the manual never mentions sound at all.  Every GAC snapshot of the
; four we have holds exactly one call to the ROM's beeper, at $820B, and what
; is around it is the line editor: it loads the duration from PIP -- the system
; variable the ROM's own key click uses, which GAC sets to seventy five -- asks
; for a pitch of $00FF, and beeps.  So GAC clicked on every key pressed, and so
; does this.
;
; A speaker of one bit makes a note the same way everywhere: flip it, wait,
; flip it back, wait, as many times as the note is to last.  What differs is
; which bit of which port, and what else is in that port that must not be
; disturbed -- the border on a Spectrum, the keyboard row and the cassette
; motor on an MSX -- so each machine says:
;
;   BEEP_BIT        the bit that moves the speaker
;   BEEP_BASE       a macro putting the rest of that port in A, speaker clear
;   BEEP_OUT        a macro writing A to it
;
; This file says WITH_NOISES, which is how the rest of the interpreter knows
; there is something here that can make one -- a machine whose only speaker is
; its sound chip says the same thing from cpc/ay.asm.
;
; The pitch is how long a half wave lasts and the length is how many of them
; there are, so a note of a given number of flips is shorter the higher it is,
; which is what an ear expects of a blip.

                IFNDEF WITH_NOISES
                DEFINE WITH_NOISES 1
                ENDIF

; What the noises are is in effects.asm, which the Amstrad's own engine
; reads too: the numbers are the adventure's and not the machine's.
                include "effects.asm"

; Play a note: A the pitch, B how many times the speaker moves.  A pitch of
; nought would be the longest wave and not the shortest, so it is not one.
; Corrupts: everything
beep_note:
                ld      c, a
                BEEP_BASE
                ld      d, a                    ; the port, speaker clear
.each_flip:
                ld      a, d
                xor     BEEP_BIT
                ld      d, a
                BEEP_OUT
                ld      e, c
.wait:
                dec     e
                jr      nz, .wait
                djnz    .each_flip
                BEEP_BASE                       ; and leave it where it was
                BEEP_OUT
                ret

; The click a key makes.
; Corrupts: everything
beep_click:
                ld      a, CLICK_PITCH
                ld      b, CLICK_FLIPS
                jr      beep_note

; Effect A, counting from one.  A number the
; build has not got makes no noise rather than reading past the table.
;
; Each is three bytes: the pitch it starts at, how many flips it lasts, and
; what to add to the pitch every flip -- which is what makes a blip rise or
; fall, and is a byte with a sign.
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
                ld      a, (hl)                 ; the pitch
                inc     hl
                ld      b, (hl)                 ; how long
                inc     hl
                ld      c, (hl)                 ; and how it moves
                ld      e, a                    ; E is the pitch as it stands
                ; and then the note, with the pitch walking as it goes
                BEEP_BASE
                ld      d, a
.each_flip:
                ld      a, d
                xor     BEEP_BIT
                ld      d, a
                BEEP_OUT
                ld      a, e
                or      a
                jr      nz, .wait
                inc     a                       ; never nothing at all
.wait:
                dec     a
                jr      nz, .wait
                ; The pitch walks, and stops at the ends rather than going
                ; round: a blip that falls off the bottom comes back as the
                ; lowest growl there is, which is not what was wanted.
                ld      a, c
                or      a
                jp      p, .rising
                add     a, e
                jr      c, .walked              ; no borrow, so still in range
                ld      a, 1
                jr      .walked
.rising:
                add     a, e
                jr      nc, .walked
                ld      a, 255
.walked:
                ld      e, a
                djnz    .each_flip
                BEEP_BASE
                BEEP_OUT
                ret
