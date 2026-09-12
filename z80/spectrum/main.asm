; MIT License, Copyright (c) 2025 Cronomantic
;
; First slice of the Spectrum interpreter: find the database, unpack messages
; out of it and print them in the text window.
;
; This is the part of the runtime most likely to disagree with the builder, so
; it comes first and the tests read the screen back to check it.

                DEVICE  ZXSPECTRUM48

TEST_MESSAGES   equ 6                   ; how many to print

                ORG     $8000
start:
                di
                ld      sp, $7FF0
                xor     a
                out     ($FE), a        ; black border
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
                include "../common/conditions.asm"
                include "../common/opcodes.asm"

                ALIGN   256
database:
                INCBIN  "game.rgac"

                SAVESNA "out.sna", start
