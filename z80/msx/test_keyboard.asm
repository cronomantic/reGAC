; MIT License, Copyright (c) 2025 Cronomantic
;
; A build that does nothing but look at the keyboard, so a test can hold a key
; down and see what the scanning makes of it.
;
; last_seen holds whatever the last look found, and seen_count counts how many
; times a key was seen arriving after the keyboard had come clear, which is
; what a line of typing is made of.
;
; It takes the whole machine as the real one will, because the font it prints
; with comes out of the database and the database goes under the BIOS.

                DEVICE  NOSLOT64K

PPI_SLOTS       equ $A8                 ; two bits a page: which slot it sees
STACK_AT        equ $EF00               ; clear of everything that travels
database        equ $0000

                ORG     $8000
start:
                di
                ld      sp, STACK_AT
                call    take_the_machine
                call    keyboard_init
                call    db_init
                call    config_init
                call    text_init
                call    screen_init
                ld      a, 1
                ld      (ready_flag), a
                xor     a
                ld      (was_clear), a
.look:
                ld      a, 2                    ; the row A and B sit on
                call    read_row
                ld      (raw_row), a
                call    scan_keyboard
                ld      (scan_result), a
                or      a
                jr      z, .nothing
                ld      (last_seen), a
                ld      a, (was_clear)
                or      a
                jr      z, .look                ; still the same press
                ld      hl, seen_count
                inc     (hl)
                xor     a
                ld      (was_clear), a
                jr      .look
.nothing:
                ld      a, 1                    ; the keyboard came clear
                ld      (was_clear), a
                jr      .look

; A test can point the processor here instead, and then type a whole line at
; it: this is the path the runtime really uses, rubbing out and all.
read_a_line:
                ld      sp, STACK_AT
                call    read_line
                ld      (line_seen), bc
                ld      a, $FF
                ld      (line_done), a
.stop:
                jr      .stop

; Or here, to wait the way HOLD does, for HOLD_FRAMES fiftieths of a second
; with nothing pressed: a test counts the processor's cycles until it is over.
HOLD_FRAMES     equ 100
hold_a_while:
                ld      sp, STACK_AT
                ld      hl, HOLD_FRAMES
                call    wait_or_key
                ld      a, $FF
                ld      (line_done), a
.stop:
                jr      .stop

line_done:      db      0
line_seen:      dw      0
ready_flag:     db      0
last_seen:      db      0
raw_row:        db      0
scan_result:    db      0
was_clear:      db      0
seen_count:     db      0

; Put RAM in all four pages and move the database into the two that were the
; BIOS, which is what the loader will do off the cassette.
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
                include "keyboard.asm"

last_code:
                ASSERT  last_code < SHADOW

db_source:
                INCBIN  "text.rgac"
db_length       equ     $ - db_source
last:

                SAVEBIN "keys.bin", start, last - start
