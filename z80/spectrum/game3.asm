; MIT License, Copyright (c) 2025 Cronomantic
;
; The same interpreter on a +3, which loads from disk instead of tape.
;
; The database is banked exactly as it is on a 128, and the only thing that
; changes is which pages it goes in and who puts it there.  A +3 has fewer to
; spare: +3DOS keeps the seventh for itself and holds the sixth for its cache,
; so what is left is nought, one, three and four.  The loader is the one in
; loader3.asm, and +3DOS reads each bank into its own page.
;
; What comes out of here is not a medium but its two pieces, because the disk
; itself is put together by regac release:
;
;   python -m regac build partida.json game3.rgac -m spectrum128 -b 16k ;          --defs banks3.inc
;   python -m regac release z80/spectrum/game3_code.bin salida/ -m plus3 ;          --boot z80/spectrum/game3_boot.bin --database z80/spectrum/game3.rgac

                DEFINE  BANKED
                DEVICE  ZXSPECTRUM128

                include "banks3.inc"

; The pages a +3 has to spare, in the order the database numbers its banks.
DB_PAGE_0       equ 0
DB_PAGE_1       equ 1
DB_PAGE_2       equ 3
DB_PAGE_3       equ 4
DB_PAGE_4       equ 0                   ; there is no fifth or sixth to give,
DB_PAGE_5       equ 0                   ; which is what the next line says
                ASSERT DB_BANK_COUNT <= 4

                ; The loader travels in the BASIC area, which is page five and
                ; is always there.
                SLOT    1
                PAGE    5
                include "loader3.asm"

                SLOT    2
                PAGE    2
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
                ld      a, 1
                ld      (vm_new_room), a
                call    play
                ld      a, $FF
                ld      (done_flag), a
.stop:
                jr      .stop

done_flag:      db      0

                include "paging.asm"
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
                INCBIN  "game3.rgac", 0, DB_RESIDENT_SIZE
last:

                IFDEF SCREEN
                SAVEBIN "game3_screen.bin", loading_screen, SCREEN_BYTES
                ENDIF
                SAVEBIN "game3_code.bin", start, last - start
                SAVEBIN "game3_boot.bin", basic, basic_end - basic
