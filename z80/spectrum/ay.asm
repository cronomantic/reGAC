; MIT License, Copyright (c) 2025 Cronomantic
;
; The sound chip of a Spectrum 128, a +3 and a Next, which are the same chip
; at the same two ports: $FFFD chooses a register and $BFFD takes its value.
; Both are write only here, which is all this needs.
;
; A Next has three of these and this asks for one, because one is what a blip
; wants.  Nothing else in the interpreter touches the chip, so whichever is
; selected when we arrive is the one that sounds, and it stays selected.
;
; A 48 has no chip at all and keeps beep.asm; which of the two a build takes
; is decided in keyboard.asm, by WITH_AY.

; Register seven is the mixer and nothing else on this machine, so there is
; nothing of it to keep.
AY_MIXER_KEEP   equ 0

; Every build of these machines has room for the table and the player, so
; SOUND always works here: it is the Amstrad, and only the Amstrad, that asks
; to leave them out.
                DEFINE  AY_SOUNDS 1

; Put E into register D.
; Corrupts: AF, BC
ay_write:
                ld      bc, $FFFD
                out     (c), d
                ld      b, $BF
                out     (c), e
                ret

                include "../common/ay.asm"
