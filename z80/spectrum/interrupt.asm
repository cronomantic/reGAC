; MIT License, Copyright (c) 2025 Cronomantic
;
; The fifty interrupts a second the music is played from, on a Spectrum.
;
; The interpreter runs with them off -- every machine here does -- so this is
; the only thing that turns them on, and it does it in mode two rather than
; mode one for a reason that is worth saying: mode one goes to $0038, and what
; is at $0038 is the ROM's own handler, which scans the keyboard, counts frames
; and wants the system variables in the state BASIC left them.  Mode two goes
; where we say.
;
; Where we say has to be memory that is always there, so both the table and the
; routine live above the interpreter and below the window at $C000, in the page
; that never moves.  The table is 257 bytes of the same byte -- the extra one
; because the byte the machine puts on the bus is not to be relied upon, so the
; vector may be the last entry and the address is read from two bytes -- and
; that byte is chosen so that the routine's address is a pair of it.

IM2_TABLE       equ $BE00               ; 257 bytes of IM2_FILLER
IM2_FILLER      equ $BD
IM2_HANDLER     equ IM2_FILLER * 257    ; which is $BDBD

; Put the machine in mode two and let them in.
; Corrupts: AF, BC, DE, HL
interrupt_init:
                di
                ld      hl, IM2_TABLE
                ld      de, IM2_TABLE + 1
                ld      (hl), IM2_FILLER
                ld      bc, 256
                ldir
                ld      a, IM2_TABLE >> 8
                ld      i, a
                im      2
                ei
                ret

; And the routine itself, at the address that table points at.  The player
; corrupts everything it can reach, including the other set, so everything it
; can reach is put away first; and it is called with the interrupts off, which
; is what it asks for.
                ORG     IM2_HANDLER
interrupt_handler:
                push    af
                push    bc
                push    de
                push    hl
                push    ix
                push    iy
                ex      af, af'
                exx
                push    af
                push    bc
                push    de
                push    hl
                call    music_tick
                pop     hl
                pop     de
                pop     bc
                pop     af
                exx
                ex      af, af'
                pop     iy
                pop     ix
                pop     hl
                pop     de
                pop     bc
                pop     af
                ei
                reti
                ASSERT  $ <= IM2_TABLE  ; or it would run into its own table
