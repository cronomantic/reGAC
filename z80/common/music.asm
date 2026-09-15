; MIT License, Copyright (c) 2025 Cronomantic
;
; Starting, stopping and feeding a tune.  The playing itself is Arkos
; Tracker's, in z80/arkos/, which is what a tune composed in that tracker
; expects to be played by; this is the little that is ours: which tune, and
; when.
;
; The when is the only part with a rule to it.  The player runs from the
; interrupt, and an interrupt can arrive at any moment -- including while the
; interpreter has a bank of the database in its window.  So the tune must live
; where the window never reaches, and it does: it is assembled with the
; interpreter.  That is why paging does not have to turn the interrupts off,
; and why the music does not stutter when a room changes.
;
; A tune wants playing fifty times a second and no machine here interrupts
; fifty times a second except the Spectrum.  The Amstrad does it three hundred
; times; an MSX does it as often as its television refreshes, which is fifty
; in Europe and sixty in Japan and America, and the machine only knows which
; when it is running.  So rather than counting interrupts, this keeps a clock:
; every interrupt puts fifty on it, and when it has as much on it as the
; machine has interrupts in a second, that much comes off and the tune is
; played.  Fifty over fifty plays every time, fifty over three hundred plays
; one in six, and fifty over sixty plays five in every six, spread as evenly
; as whole interrupts allow.  One rule, and the rate can be a thing the
; machine works out when it starts rather than something the build has to
; know.

MUSIC_HERTZ     equ 50                  ; how often a tune wants to be played

                IFNDEF MUSIC_RATE
                DEFINE MUSIC_RATE 50    ; and how often this machine wakes up
                ENDIF

; Get ready to play, with nothing playing yet.
; Corrupts: AF, HL
music_init:
                xor     a
                ld      (music_playing), a
                ld      hl, MUSIC_RATE
                ld      (music_rate), hl
                ld      hl, 0
                ld      (music_clock), hl
                ret

; Start the tune at HL, from its first subsong.
;
; The interrupts go off while it is set up, or one could arrive half way
; through and play a tune that is not there yet, and come back on after: in a
; build with music they are on from the start and stay on.
; Corrupts: everything
music_start:
                di
                xor     a                       ; subsong nought
                call    PLY_AKM_Init
                ld      a, 1
                ld      (music_playing), a
                ei
                ret

; Stop it, and leave the chip quiet.
; Corrupts: everything
music_stop:
                di
                xor     a
                ld      (music_playing), a
                call    PLY_AKM_Stop
                ei
                ret

; One interrupt: fifty more on the clock, and the tune played if that is
; enough.  On a machine that interrupts oftener than the music wants, this is
; where the extra ones go.
; Corrupts: everything
music_tick:
                ld      hl, (music_clock)
                ld      de, MUSIC_HERTZ
                add     hl, de
                ld      de, (music_rate)
                or      a
                sbc     hl, de
                jr      nc, .due
                add     hl, de                  ; not yet: the borrow back
                ld      (music_clock), hl
                ret
.due:
                ld      (music_clock), hl
                ld      a, (music_playing)
                or      a
                ret     z
                jp      PLY_AKM_Play

music_playing:  db      0
music_rate:     dw      MUSIC_RATE
music_clock:    dw      0
