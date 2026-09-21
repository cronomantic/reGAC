; MIT License, Copyright (c) 2025 Cronomantic
;
; The sound chip of an Amstrad, which is the only thing here that can make a
; noise: this machine has no speaker of one bit, so where a Spectrum can flip
; a port fast enough to be a note, this has to ask the chip.
;
; Getting at it is the dance the keyboard already does.  The chip is behind
; the same eight two five five, told what it is being handed by two bits of
; port C: $C0 to choose a register, $80 to give it a value, and $00 to let go
; in between.  Nothing may interrupt it, for the reason keyboard.asm gives,
; and nothing does -- the interpreter runs with the interrupts off.
;
; Register seven is the mixer and nothing else *that is ours*: bit six says
; which way the chip's own port A faces, and it has to stay an input because
; that port is the keyboard row.  AY_TONE_ONLY has it clear already, so there
; is nothing extra to keep.
AY_MIXER_KEEP   equ 0

; And here is the one place this machine differs from the others: the table
; of effects and the player that walks a pitch travel only in a build that
; asked for them, which is what -DNOISES says.  The click is not part of that
; -- it is in every build, as it was in the original.  Measured on the eight
; adventures of 1986: the chip access is forty bytes and the player a hundred
; and four, on a machine where megacorp2 has fourteen to spare.
                IFDEF NOISES
                DEFINE  AY_SOUNDS 1
                ENDIF

; Put E into the chip's register D.
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

                include "../common/ay.asm"
