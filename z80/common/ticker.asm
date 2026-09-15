; MIT License, Copyright (c) 2025 Cronomantic
;
; What an interrupt does, on whichever machine and in whichever mode: put
; everything away, tell the music another one has gone by, and give it all
; back.  The player corrupts everything it can reach, including the other set,
; so everything it can reach is saved; and it wants to be called with the
; interrupts off, which is how it is entered.
;
; INTERRUPT_ACK is the machine's own: whatever it wants doing to be told the
; interrupt has been seen, or nothing at all.
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
                INTERRUPT_ACK
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
