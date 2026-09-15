; MIT License, Copyright (c) 2025 Cronomantic
;
; Starting, stopping and feeding a tune.  The playing itself is Arkos
; Tracker's, in z80/arkos/, which is where a tune composed in that tracker
; expects to be played by; this is the little that is ours: which tune, and
; when.
;
; The when is the only part with a rule to it.  The player runs from the
; interrupt, fifty times a second, and an interrupt can arrive at any moment --
; including while the interpreter has a bank of the database in its window.
; So the tune must live where the window never reaches, and it does: it is
; assembled with the interpreter.  That is why paging does not have to turn the
; interrupts off, and why the music does not stutter when a room changes.
;
; Not every machine interrupts fifty times a second.  The Amstrad does it three
; hundred times and an MSX built for a sixty hertz television does it sixty, so
; each machine says how many of its own interrupts make one of ours, and the
; ones that are already fifty say one.

                IFNDEF MUSIC_TICKS
                DEFINE MUSIC_TICKS 1
                ENDIF

; Get ready to play, with nothing playing yet.
; Corrupts: AF
music_init:
                xor     a
                ld      (music_playing), a
                ld      a, MUSIC_TICKS
                ld      (music_countdown), a
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

; One interrupt.  Most of them do nothing at all: on a machine that interrupts
; oftener than the music wants, this is where the extra ones go.
; Corrupts: everything
music_tick:
                ld      hl, music_countdown
                dec     (hl)
                ret     nz
                ld      (hl), MUSIC_TICKS
                ld      a, (music_playing)
                or      a
                ret     z
                jp      PLY_AKM_Play

music_playing:  db      0
music_countdown: db     1
