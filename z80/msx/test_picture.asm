; MIT License, Copyright (c) 2025 Cronomantic
;
; A build that draws one picture on an MSX and stops, so the tests can compare
; what reached the video chip against what the reference renderer says.
;
; The code goes above $8000, where a cassette would put it, and the database
; travels behind it and is moved down under the BIOS -- which means taking the
; whole machine for ourselves first.  That is the same thing the real loader
; will do, because a database and an interpreter do not fit in the thirty two
; kilobytes a BLOAD can reach.

                DEVICE  NOSLOT64K

PPI_SLOTS       equ $A8                 ; two bits a page: which slot it sees
STACK_AT        equ $EF00               ; clear of the code, the copy and the
                                        ; screen's shadow
database        equ $0000               ; where it ends up, once we own the RAM

                ORG     $8000
start:
                di
                ; The stack goes above everything that travels.  It used to be
                ; at $BF00, which is inside the database's copy: the return
                ; address of the very call that moves it landed in the bytes
                ; being moved, and two bytes of a picture came out as $8007.
                ld      sp, STACK_AT
                call    take_the_machine
                call    db_init
                call    config_init
                call    text_init
                call    screen_init
                call    picture_init
                ; fall through

; Drawing again is asked for with go_flag: a test writes the picture's number,
; clears done_flag and sets go_flag, and the loop the build parks in sees it
; and comes back here.  It used to be asked for by writing this label into the
; program counter while the processor ran, and that is not safe: the emulator
; takes its orders on a thread of its own, and a program counter changed
; between an instruction's first byte and the rest of it finishes the
; instruction with bytes from here.  In the parking loop that instruction can
; be a CALL, whose address then comes out of the LD SP in front of this -- a
; call into the database, which fits what the Next's test caught now and then:
; the processor and the stack both down in the database, and code trampled.
; Asked with this byte instead, ten rounds of that test in a row came out
; clean, and none of them needed asking twice.  A byte of memory has nothing
; in the middle to be caught in.
redraw:
                ld      sp, STACK_AT
                xor     a
                ld      (go_flag), a
                ld      hl, (picture_wanted)
                call    draw_picture
                ld      a, $FF
                ld      (done_flag), a
.stop:
                ld      a, (go_flag)
                or      a
                jr      z, .stop
                jr      redraw

done_flag:      db      0
go_flag:        db      0
picture_wanted: dw      1

; Put RAM in all four pages and move the database into the two that were the
; BIOS.  Which slot the RAM is in is not assumed: it is the one pages two and
; three are already showing, because that is where a machine of this size
; keeps it.
; Corrupts: everything
take_the_machine:
                in      a, (PPI_SLOTS)
                and     %00110000               ; the slot page two is in
                rrca
                rrca
                rrca
                rrca
                ld      c, a
                add     a, a
                add     a, a
                or      c                       ; the same in pages nought and one
                ld      c, a
                in      a, (PPI_SLOTS)
                and     %11110000
                or      c
                out     (PPI_SLOTS), a
                ld      hl, db_source
                ld      de, database
                ld      bc, db_length
                ldir
                ret

                include "../common/database.asm"
                include "../common/config.asm"
                include "../common/unpack.asm"
                include "screen.asm"
                include "../common/textout.asm"
                include "draw.asm"
                include "../common/shapes.asm"
                include "fill.asm"
                include "../common/picture.asm"

last_code:
                ASSERT  last_code < SHADOW      ; or it would draw over itself

; The database travels above the code and is copied out of the way before
; anything is drawn, so it may sit where the copy of the screen will be.
db_source:
                INCBIN  "picture.rgac"
db_length       equ     $ - db_source
last:

                SAVEBIN "picture.bin", start, last - start
