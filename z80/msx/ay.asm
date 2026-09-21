; MIT License, Copyright (c) 2025 Cronomantic
;
; The sound chip of an MSX, which every one of them has: $A0 chooses a
; register and $A1 takes its value.  There is a third port, $A2, for reading
; one back, and nothing here needs it.
;
; The chip is not only sound on this machine.  Its two eight bit ports are the
; joysticks and a handful of outputs -- the kana lamp among them -- and **the
; top two bits of register seven say which way those ports face**, not
; anything about the mixer.  The machine comes up with port A an input and
; port B an output, which is bit seven set and bit six clear, and writing the
; mixer without keeping bit seven would turn the joystick lines round.  So it
; is kept, and AY_MIXER_KEEP is what keeps it.

PSG_SELECT      equ $A0
PSG_WRITE       equ $A1

AY_MIXER_KEEP   equ %10000000           ; port B stays an output

                DEFINE  AY_SOUNDS 1

; Put E into register D.
; Corrupts: AF, BC
ay_write:
                ld      a, d
                out     (PSG_SELECT), a
                ld      a, e
                out     (PSG_WRITE), a
                ret

                include "../common/ay.asm"
