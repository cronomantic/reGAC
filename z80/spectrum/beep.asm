; MIT License, Copyright (c) 2025 Cronomantic
;
; The speaker of a Spectrum, which is bit four of the port the border is on.
; The port cannot be read back, so the border we last set is kept in
; gfx_border -- screen.asm holds it and draw.asm writes it -- and every flip of
; the speaker goes out with it, or a click would turn the border black.
;
; A Next is a Spectrum here, at the same port and the same bit.

BEEP_BIT        equ %00010000

                MACRO   BEEP_BASE
                ld      a, (gfx_border)
                ENDM

                MACRO   BEEP_OUT
                out     ($FE), a
                ENDM

                include "../common/beep.asm"
