; MIT License, Copyright (c) 2025 Cronomantic
;
; The PCW interpreter: everything put together and playing.
;
; The machine is taken as its own boot sector leaves it -- interrupts off, the
; banks unlocked, nought to three in the four windows -- and the map from then
; on is ours:
;
;   $0000  the interpreter, and the part of the database that stays
;   $4000  the window the rest of the database is paged through
;   $8000  whichever half of the screen is being written to
;   $C000  the mask, the buffers, the stack, the table the video reads, and at
;          the very top the sixteen bytes the keyboard leaves itself
;
; What comes out of here is not a medium but the pieces of one, because the
; disk itself is put together by regac release:
;
;   python -m regac build partida.json game.rgac -m pcw -b 16k \
;          --defs banks.inc
;   python -m regac release z80/pcw/game_code.bin salida/ -m pcw \
;          --boot z80/pcw/boot.bin --database z80/pcw/game.rgac

                DEFINE  BANKED
                DEVICE  NOSLOT64K

                include "banks.inc"

; The banks the loader puts the database in: the map takes nought to four, so
; the database starts at five.  A PCW 8256 has sixteen of them.
DB_PAGE_0       equ 5
DB_PAGE_1       equ 6
DB_PAGE_2       equ 7
DB_PAGE_3       equ 8
DB_PAGE_4       equ 9
DB_PAGE_5       equ 10
                ASSERT DB_BANK_COUNT <= 6

LOCK            equ $F4
UNLOCKED        equ 0

                ORG     $0100
start:
                di
                ld      sp, $FC00
                ld      a, UNLOCKED             ; the banks are ours to move
                out     (LOCK), a
                call    keyboard_init
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
                include "disc.asm"
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
                INCBIN  "game.rgac", 0, DB_RESIDENT_SIZE
last:
                ASSERT  last <= DB_WINDOW       ; or it would page itself out

                SAVEBIN "game_code.bin", start, last - start
