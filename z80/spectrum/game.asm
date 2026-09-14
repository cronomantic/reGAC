; MIT License, Copyright (c) 2025 Cronomantic
;
; The Spectrum interpreter: everything put together and playing.

                DEVICE  ZXSPECTRUM48

                include "loader.asm"

                ORG     $8000
start:
                di
                ld      sp, $7FF0
                xor     a
                out     ($FE), a
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

                include "../common/database.asm"
                include "../common/config.asm"
                include "../common/unpack.asm"
                include "screen.asm"
                include "../common/textout.asm"
                include "keyboard.asm"
                include "tape.asm"
                include "draw.asm"
                include "shapes.asm"
                include "fill.asm"
                include "../common/conditions.asm"
                include "../common/opcodes.asm"
                include "../common/parser.asm"
                include "../common/loop.asm"
                include "../common/picture.asm"

                ALIGN   256
database:
                INCBIN  "game.rgac"
last:

                SAVESNA "game.sna", start
                SAVEBIN "game.bin", start, last - start

; The tape: the BASIC that carries the loader, and then the whole of the
; interpreter and its database in one block.
                EMPTYTAP "game.tap"
                SAVETAP "game.tap", BASIC, "reGAC", basic, basic_end - basic, 10
                SAVETAP "game.tap", HEADLESS, start, last - start
