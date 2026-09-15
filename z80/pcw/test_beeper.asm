; MIT License, Copyright (c) 2025 Cronomantic
;
; A build that goes looking for this machine's beeper, because nothing we have
; says where it is.
;
; The PCW has no sound chip and its own noise is a buzzer, but the system port
; at $F8 does not take bits: it takes numbered orders -- nine is the disc
; motor on and ten is it off -- and which of them is the buzzer is not in any
; paper here.  So this asks the machine.
;
; What it does is make a square wave out of whichever pair of numbers it is
; told: write one, wait, write the other, wait, over and over.  A test pokes a
; pair in, records what the emulator plays, and looks for a pair that is not
; silence.  It can be pointed at another port as well, in case the buzzer is
; a bit somewhere rather than an order here.

                DEVICE  NOSLOT64K

                ORG     $0100
start:
                di
                ld      sp, $F000
                ld      a, 1
                ld      (ready_flag), a
.again:
                ld      a, (spins)
                inc     a
                ld      (spins), a
                ld      a, (port)
                ld      c, a
                ld      b, 0
                ld      a, (one)
                out     (c), a
                call    wait
                ld      a, (port)
                ld      c, a
                ld      b, 0
                ld      a, (other)
                out     (c), a
                call    wait
                jr      .again

; Half a wave, at something an ear would call a note.
wait:
                ld      de, (half)
.count:
                dec     de
                ld      a, d
                or      e
                jr      nz, .count
                ret

ready_flag:     db      0
spins:          db      0
port:           db      $F8             ; what the test pokes: the port,
one:            db      0               ; and the two values to go out of it
other:          db      0
half:           dw      40              ; how long half a wave lasts

last:
                SAVEBIN "beeper.bin", start, last - start
