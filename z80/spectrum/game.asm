; MIT License, Copyright (c) 2025 Cronomantic
;
; The Spectrum interpreter: everything put together and playing.
;
; The same interpreter goes on a +3 disk that has no banks: built with
; -DPLUS3 a game is saved in a file on that disk, by +3DOS, instead of on the
; tape, and what comes out is game3flat.bin, for regac release -m plus3:
;
;   python -m regac build partida.json game.rgac -m spectrum48
;   sjasmplus -DPLUS3 game.asm
;   python -m regac release z80/spectrum/game3flat.bin salida/ -m plus3

                DEVICE  ZXSPECTRUM48

                include "loader.asm"

                IFDEF SCREEN
                ; A loading screen, if the build says there is one: it goes
                ; where the screen is and travels as the first block.
                ORG     SCREEN_AT
loading_screen:
                INCBIN  "screen.bin", 0, SCREEN_BYTES
                ENDIF

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
                IFDEF   PLUS3
                include "disk3.asm"
; Where a game being loaded is read first, in page five above the BASIC that
; loads us and short of the stack: see disk3.asm.
LOAD_AREA       equ $7600
                ELSE
                include "tape.asm"
                ENDIF
                include "draw.asm"
                include "../common/shapes.asm"
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

                IFDEF   PLUS3
                ASSERT  LOAD_AREA + vm_state_end - vm_state <= $7FF0 - 512
                ; +3DOS writes the game from where it is, with its page seven
                ; in the window: it has to be under it.
                ASSERT  vm_state_end <= $C000
                SAVEBIN "game3flat.bin", start, last - start
                ELSE
                SAVESNA "game.sna", start
                SAVEBIN "game.bin", start, last - start

; The tape: the BASIC that carries the loader, and then the whole of the
; interpreter and its database in one block.
                EMPTYTAP "game.tap"
                SAVETAP "game.tap", BASIC, "reGAC", basic, basic_end - basic, 10
                IFDEF SCREEN
                SAVETAP "game.tap", HEADLESS, loading_screen, SCREEN_BYTES
                ENDIF
                SAVETAP "game.tap", HEADLESS, start, last - start
                ENDIF
