; MIT License, Copyright (c) 2025 Cronomantic
;
; Starting, stopping and feeding a tune.  The playing itself is Arkos
; Tracker's, in z80/arkos/, which is what a tune composed in that tracker
; expects to be played by; this is the little that is ours: which tune, and
; when.
;
; Which tune is the other part, and it is a list.  A build says what tunes it
; has with MUSIC_TUNE, one line each, between the labels music_tunes and
; music_tunes_end:
;
;       music_tunes:
;               MUSIC_TUNE  menu, 0
;               MUSIC_TUNE  menu, 1
;               MUSIC_TUNE  cave, 0
;       music_tunes_end:
;
; -- a tune being an address and which subsong of it to play, because one
; export of the tracker may hold several and they share their instruments,
; which is much the cheapest way to have more than one.  Two separate exports
; work as well; they only cost more.  From here on a tune is the number of its
; line, counting from nought.
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

MUSIC_ENTRY     equ 3                   ; two bytes of address, one of subsong

; One line of that list.
                MACRO   MUSIC_TUNE where, subsong
                dw      where
                db      subsong
                ENDM

; Get ready to play, with nothing playing yet.
; Corrupts: AF, HL
music_init:
                xor     a
                ld      (music_playing), a
                dec     a
                ld      (music_tune), a         ; none of them
                ld      hl, MUSIC_RATE
                ld      (music_rate), hl
                ld      hl, 0
                ld      (music_clock), hl
                ret

; Start tune A, counting from nought.  Asking for one the build has not got
; does nothing at all, rather than playing whatever is at the address that is
; not there: an adventure may well name a tune it has lost.
;
; The interrupts go off while it is set up, or one could arrive half way
; through and play a tune that is not there yet, and come back on after: in a
; build with music they are on from the start and stay on.
; Corrupts: everything
music_start:
                cp      music_count
                ret     nc
                ld      (music_tune), a
                ld      l, a
                ld      h, 0
                ld      d, h
                ld      e, l
                add     hl, hl
                add     hl, de                  ; three bytes to the line
                ld      de, music_tunes
                add     hl, de
                ld      e, (hl)
                inc     hl
                ld      d, (hl)
                inc     hl
                ld      a, (hl)                 ; which subsong of it
                ex      de, hl
                di
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
                dec     a
                ld      (music_tune), a
                call    PLY_AKM_Stop
                ei
                ret

; Quiet for a moment, and back again.  The tape is the reason: its timing is
; counted in clock cycles and an interrupt in the middle of a byte is a byte
; lost, so saving and loading turn the music off and on again around
; themselves.  What comes back starts the tune over -- the player has no way
; to say where it was -- which is a small thing to hear after a save and a
; great deal simpler than keeping its state.
; Corrupts: everything
music_hush:
                ld      a, (music_playing)
                ld      (music_hushed), a
                or      a
                ret     z
                ld      a, (music_tune)
                ld      (music_hushed_tune), a
                jp      music_stop

music_back:
                ld      a, (music_hushed)
                or      a
                ret     z
                ld      a, (music_hushed_tune)
                jp      music_start

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
music_tune:     db      $FF             ; which one, or none
music_hushed:   db      0               ; whether it was playing when hushed
music_hushed_tune: db   0
music_rate:     dw      MUSIC_RATE
music_clock:    dw      0

; How many the build has, which is the length of its list.  It is worked out
; here and not said by the build, so that there is one place to add a tune.
music_count     equ (music_tunes_end - music_tunes) / MUSIC_ENTRY

; Sound effects, in a build that asks for them.  They are the tracker's as
; well: an effect is a little instrument of its own, exported from a song of
; nothing but effects, and what playing one does is tell the player to lay it
; over one of the three channels the next time it runs.  So an effect costs
; nothing until the interrupt comes round, and the tune goes on underneath
; with a channel missing for as long as the effect lasts.
;
; Which channel is the last one, because the tunes these machines carry put
; the melody on the first and the bass on the second more often than not.  A
; build may say otherwise.
                IFDEF PLY_AKM_MANAGE_SOUND_EFFECTS

                IFNDEF SOUND_CHANNEL
                DEFINE SOUND_CHANNEL 2  ; counting from nought
                ENDIF

; The bank of effects at HL, which has to be said before any of them is asked
; for and may be said whether a tune is playing or not.
; Corrupts: AF, HL
sound_init:
                jp      PLY_AKM_InitSoundEffects

; Play effect A, counting from one, at its own volume.  The interrupts go off
; while it is asked for: it is five bytes of the player's state, and one
; arriving half way through would find half an address.
; Corrupts: everything
sound_play:
                di
                ld      c, SOUND_CHANNEL
                ld      b, 0                    ; as loud as it was made
                call    PLY_AKM_PlaySoundEffect
                ei
                ret

; And quiet again before it has finished, which nothing needs yet but the
; player offers.
; Corrupts: everything
sound_quiet:
                di
                ld      a, SOUND_CHANNEL
                call    PLY_AKM_StopSoundEffectFromChannel
                ei
                ret

                ENDIF
