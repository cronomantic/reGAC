; MIT License, Copyright (c) 2025 Cronomantic
;
; A build that runs the high priority conditions of whatever database is
; alongside it and then stops, so the tests can read the flags, the counters
; and where the player ended up.

                DEVICE  ZXSPECTRUM48

                ORG     $8000
start:
                di
                ld      sp, $7FF0
                xor     a
                out     ($FE), a
                call    db_init
                call    text_init
                call    screen_init
                call    vm_init
                ; the player starts where the config says
                ld      a, SECTION_CONFIG
                call    db_section
                ld      e, (hl)
                inc     hl
                ld      d, (hl)
                ld      (vm_location), de

                ld      a, SECTION_CONDITIONS
                call    db_section
                push    hl
                ld      e, (hl)
                inc     hl
                ld      d, (hl)                 ; where the high priority ones are
                pop     hl
                add     hl, de
                call    run_conditions

                ld      a, $FF
                ld      (done_flag), a
.stop:
                jr      .stop

done_flag:      db      0

                include "../common/database.asm"
                include "../common/unpack.asm"
                include "screen.asm"
                include "../common/conditions.asm"
                include "../common/opcodes.asm"

                ALIGN   256
database:
                INCBIN  "conditions.rgac"

                SAVESNA "conditions.sna", start
