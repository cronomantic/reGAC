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

; The click: about a fiftieth of a second at something near five hundred
; hertz, which is the nearest this engine comes to the pip the original asked
; the ROM for.
CLICK_PITCH     equ 200
CLICK_FLIPS     equ 20

; Five of them, which is as many as an adventure of the original's kind ever
; wanted: something taken, something refused, a door, a fall and a stab of
; alarm.  An author with a sound chip writes their own in the tracker and gets
; these only where there is no chip playing.
;
; A bigger pitch is a lower note, so a step that takes it down takes the note
; up.  All five are between a twentieth and a tenth of a second.
beep_effects:
                db      200, 150, -1            ; 1: taken, rising
                db      60, 150, 1              ; 2: refused, falling
                db      250, 100, 0             ; 3: a door, flat and low
                db      30, 110, 2              ; 4: a fall, high to low
                db      60, 200, 0              ; 5: alarm, high and hard
BEEP_SOUNDS     equ ($ - beep_effects) / 3
