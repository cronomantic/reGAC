; MIT License, Copyright (c) 2025 Cronomantic
;
; First slice of the PCW interpreter: find the database, unpack messages out
; of it and print them in the text window.
;
; The same shape as the Spectrum's and the Amstrad's, and on purpose:
; everything above the screen layer is the same code, so if this prints what
; those print then the layer underneath is doing its job.  Here it prints
; enough of them to run off the bottom, because a window that scrolls is the
; one part of this machine's screen that a picture never exercises.

                DEVICE  NOSLOT64K

TEST_MESSAGES   equ 20                  ; how many to print
LOCK            equ $F4
UNLOCKED        equ 0

                ORG     $0100
start:
                di
                ld      sp, $FD00
                ld      a, UNLOCKED             ; the banks are ours to move
                out     (LOCK), a
                call    db_init
                call    config_init
                call    text_init
                call    screen_init

                ld      de, 0
.next_message:
                push    de
                call    unpack_message  ; BC = how many characters
                ld      hl, text_buffer
                call    print_text
                call    new_line
                pop     de
                inc     de
                ld      hl, TEST_MESSAGES
                or      a
                sbc     hl, de
                jr      nz, .next_message

                ; tell the test it got here, and stop
                ld      a, $FF
                ld      (done_flag), a
.stop:
                jr      .stop

done_flag:      db      0

                include "../common/database.asm"
                include "../common/config.asm"
                include "../common/unpack.asm"
                include "screen.asm"
                include "../common/textout.asm"

                ALIGN   256
database:
                INCBIN  "text.rgac"
last:

                SAVEBIN "text.bin", start, last - start
