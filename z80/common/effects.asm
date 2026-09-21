; MIT License, Copyright (c) 2025 Cronomantic
;
; The noises an adventure can ask for, and how long and how high each one is.
;
; They are here on their own because two machines make them in two ways.  Most
; of them have a speaker of one bit and flip it (beep.asm); the Amstrad has no
; speaker at all and its sound chip makes the same notes a different way
; (cpc/ay.asm).  Same numbers, same names, same lengths: an adventure that
; says SOUND 2 gets something refused-sounding wherever it is played.
;
; A pitch is how long half a wave lasts, in the sixteen cycle steps the one
; bit engine counts; the chip turns that into a period of its own.  A bigger
; pitch is a lower note.
;
; Each noise is four bytes: the pitch it starts at, how many waves it lasts,
; what to add to the pitch every wave -- a byte with a sign, so a blip rises
; or falls -- and **what it comes out of**.  A door, a fall and a stab of
; alarm are not notes, and a chip has a noise generator that says so; a
; speaker of one bit has only the one thing it can do, so there the fourth
; byte is read and the tone played.  Same table, same lengths, better where
; there is better to be had.
OUT_OF_TONE     equ 0
OUT_OF_NOISE    equ 1
OUT_OF_BOTH     equ 2

; The click: about a fiftieth of a second at something near five hundred
; hertz, which is the nearest this engine comes to the pip the original asked
; the ROM for.
CLICK_PITCH     equ 200
CLICK_FLIPS     equ 20

; An adventure may say what noises it wants, in a section of its own, and
; then regac build writes them here and this file takes them in.  One that
; says nothing gets the five below, which is as many as an adventure of the
; original's kind ever wanted: something taken, something refused, a door, a
; fall and a stab of alarm.
;
; A bigger pitch is a lower note, so a step that takes it down takes the note
; up.  All five are between a twentieth and a tenth of a second.
; The table itself is only in a build that has SOUND to play, which on the
; Amstrad is a build that asked for it: see common/ay.asm.  The click above is
; in every build, because the original clicked in every one.
                IFDEF WITH_NOISES
beep_effects:
                IFDEF WITH_OWN_NOISES
                include "../../music/noises.asm"
                ELSE
                db      200, 150, -1, OUT_OF_TONE   ; 1: taken, rising
                db      60, 150, 1, OUT_OF_TONE     ; 2: refused, falling
                db      250, 100, 0, OUT_OF_BOTH    ; 3: a door: wood and air
                db      30, 110, 2, OUT_OF_NOISE    ; 4: a fall, high to low
                db      60, 200, 0, OUT_OF_BOTH     ; 5: alarm, harsh
                ENDIF
BEEP_SOUNDS     equ ($ - beep_effects) / 4
                ENDIF
