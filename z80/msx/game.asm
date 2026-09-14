; MIT License, Copyright (c) 2025 Cronomantic
;
; The MSX interpreter: everything put together and playing.
;
; The machine is taken whole -- RAM in all four pages, the BIOS out of the way
; -- because an interpreter and a database do not fit in the thirty two
; kilobytes a BLOAD can reach.  From then on the map is:
;
;   $0000  the database, which the loader put there before this ran
;   $8000  the interpreter
;   $C000  the copy of the picture the video chip is sent
;   $E000  the buffers and the stack
;
; There are no banks: with the whole machine there is no need of them, which
; makes this the simplest build of the lot after the 48K Spectrum's.
;
; The BIOS comes back for as long as a save takes, because it is the only
; thing here that can talk to a cassette; tape.asm does that, and the two slot
; values it needs are worked out below.

                DEVICE  NOSLOT64K

STACK_AT        equ $EF00               ; above everything that travels
database        equ $0000

                ORG     $8000
; What the cassette starts, and what the file on it says to start: the whole
; of it, with the database read in first.  Off a tape it is the interpreter
; that has to fetch the database, because nothing else on this machine can
; reach under the BIOS -- which is why this comes before anything else here,
; where the medium can find it without being told an address.
from_tape:
                di
                ld      sp, STACK_AT
                call    take_the_machine
                call    load_database
                jr      begin

; And what a test starts, which is the same without the tape: the database is
; written in from outside while this waits, because nothing outside the
; machine can reach under the BIOS until the switch below.
start:
                di
                ld      sp, STACK_AT
                call    take_the_machine
.wait_for_it:
                ld      a, (database_ready)
                or      a
                jr      z, .wait_for_it

begin:

                call    keyboard_init
                call    db_init
                call    config_init
                call    text_init
                call    screen_init
                call    picture_init
                call    vm_init
                call    vocab_init
                call    loop_init
                ; the player starts where the adventure says
                ld      a, SECTION_CONFIG
                call    db_section
                ld      e, (hl)
                inc     hl
                ld      d, (hl)
                ld      (vm_location), de
                ld      a, 1
                ld      (vm_new_room), a
                call    play
                ld      a, $FF
                ld      (done_flag), a
.stop:
                jr      .stop

done_flag:      db      0
database_ready: db      1               ; a cassette has it there already

                include "slots.asm"
                include "../common/database.asm"
                include "../common/config.asm"
                include "../common/unpack.asm"
                include "screen.asm"
                include "../common/textout.asm"
                include "keyboard.asm"
                include "tape.asm"
                include "loader.asm"
                include "draw.asm"
                include "../common/shapes.asm"
                include "fill.asm"
                include "../common/conditions.asm"
                include "../common/opcodes.asm"
                include "../common/parser.asm"
                include "../common/loop.asm"
                include "../common/picture.asm"

last:
                ASSERT  last < SHADOW           ; or it would draw over itself

                SAVEBIN "game.bin", from_tape, last - from_tape
