; MIT License, Copyright (c) 2025 Cronomantic
;
; First slice of the Amstrad interpreter: find the database, unpack messages
; out of it and print them in the text window.
;
; The same shape as the Spectrum's, and on purpose: everything above the
; screen layer is the same code, so if this prints what that prints then the
; layer underneath is doing its job.

                DEVICE  AMSTRADCPC6128

TEST_MESSAGES   equ 6                   ; how many to print

                ; above the lower ROM, which covers anything under $4000
                ORG     $4000
start:
                di
                ld      sp, $BF00
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
