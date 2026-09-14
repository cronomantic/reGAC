; MIT License, Copyright (c) 2025 Cronomantic
;
; A build that does nothing but look at the keyboard, so a test can hold a key
; down and see what the scanning makes of it.
;
; last_seen holds whatever the last look found, and seen_count counts how many
; times a key was seen arriving after the keyboard had come clear, which is
; what a line of typing is made of.

                DEVICE  NOSLOT64K

LOCK            equ $F4
UNLOCKED        equ 0

                ORG     $0100
start:
                di
                ld      sp, $FC00
                ld      a, UNLOCKED
                out     (LOCK), a
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
                ld      a, 8                    ; the row the letters sit on
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
                ld      sp, $FC00
                call    read_line
                ld      (line_seen), bc
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

                include "../common/database.asm"
                include "../common/config.asm"
                include "../common/unpack.asm"
                include "screen.asm"
                include "../common/textout.asm"
                include "keyboard.asm"

                ALIGN   256
database:
                INCBIN  "text.rgac"
last:

                SAVEBIN "keys.bin", start, last - start
