; MIT License, Copyright (c) 2025 Cronomantic
;
; The same interpreter on a 128, with the database living in memory banks.
;
; What changes is only where the database is.  What the interpreter touches at
; any moment without warning stays resident, next to the code in page two;
; the text and the pictures go to pages of their own and are
; brought into the window at $C000 when they are wanted.  Which pages those
; are is said here, because it is the machine's business, and the table the
; paging routine walks is built from the same names.
;
; regac build writes banks.inc, which says how much of the file is resident
; and how many banks follow it:
;
;   python -m regac build partida.json game128.rgac -m spectrum128 -b 16k \
;          --defs banks.inc

                DEFINE  BANKED
                DEVICE  ZXSPECTRUM128

                include "banks.inc"

; The machine's own pages, in the order the database numbers its banks.  Two
; are spoken for: page two holds the interpreter and page five the screen.
DB_PAGE_0       equ 1
DB_PAGE_1       equ 3
DB_PAGE_2       equ 4
DB_PAGE_3       equ 6
DB_PAGE_4       equ 7
DB_PAGE_5       equ 0

                SLOT    3
                IF DB_BANK_COUNT > 0
                PAGE    DB_PAGE_0
                ORG     $C000
                INCBIN  "game128.rgac", DB_RESIDENT_SIZE, DB_BANK_BYTES
                ENDIF
                IF DB_BANK_COUNT > 1
                PAGE    DB_PAGE_1
                ORG     $C000
                INCBIN  "game128.rgac", DB_RESIDENT_SIZE + DB_BANK_BYTES, DB_BANK_BYTES
                ENDIF
                IF DB_BANK_COUNT > 2
                PAGE    DB_PAGE_2
                ORG     $C000
                INCBIN  "game128.rgac", DB_RESIDENT_SIZE + 2 * DB_BANK_BYTES, DB_BANK_BYTES
                ENDIF
                IF DB_BANK_COUNT > 3
                PAGE    DB_PAGE_3
                ORG     $C000
                INCBIN  "game128.rgac", DB_RESIDENT_SIZE + 3 * DB_BANK_BYTES, DB_BANK_BYTES
                ENDIF
                IF DB_BANK_COUNT > 4
                PAGE    DB_PAGE_4
                ORG     $C000
                INCBIN  "game128.rgac", DB_RESIDENT_SIZE + 4 * DB_BANK_BYTES, DB_BANK_BYTES
                ENDIF
                IF DB_BANK_COUNT > 5
                PAGE    DB_PAGE_5
                ORG     $C000
                INCBIN  "game128.rgac", DB_RESIDENT_SIZE + 5 * DB_BANK_BYTES, DB_BANK_BYTES
                ENDIF

                ; The loader travels in the BASIC area, which is page five
                ; and is always there.
                SLOT    1
                PAGE    5
                include "loader.asm"

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
; This machine has a sound chip, so the noises and the key click go through
; it rather than through the speaker: see spectrum/keyboard.asm.
                DEFINE  WITH_AY 1
                include "keyboard.asm"
                include "tape.asm"
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
                INCBIN  "game128.rgac", 0, DB_RESIDENT_SIZE
last:
                ; What is resident has to end before the window, or paging a
                ; bank in would take the end of it away without a word.  The
                ; eight adventures leave from 338 bytes (Bangkok2) to four
                ; kilobytes; nothing looked at it before.
                ASSERT  last <= $C000

                SAVESNA "game128.sna", start

; The tape: the BASIC that carries the loader, then the interpreter with what
; is resident of the database, then a block for each bank.  Each of those is
; read straight into the window with its own page in, which is what the table
; in the loader says.
                EMPTYTAP "game128.tap"
                SAVETAP "game128.tap", BASIC, "reGAC", basic, basic_end - basic, 10
                IFDEF SCREEN
                SAVETAP "game128.tap", HEADLESS, loading_screen, SCREEN_BYTES
                ENDIF
                SLOT    2
                PAGE    2
                SAVETAP "game128.tap", HEADLESS, start, last - start
                SLOT    3
                IF DB_BANK_COUNT > 0
                PAGE    DB_PAGE_0
                SAVETAP "game128.tap", HEADLESS, DB_WINDOW, DB_BANK_USED_0
                ENDIF
                IF DB_BANK_COUNT > 1
                PAGE    DB_PAGE_1
                SAVETAP "game128.tap", HEADLESS, DB_WINDOW, DB_BANK_USED_1
                ENDIF
                IF DB_BANK_COUNT > 2
                PAGE    DB_PAGE_2
                SAVETAP "game128.tap", HEADLESS, DB_WINDOW, DB_BANK_USED_2
                ENDIF
                IF DB_BANK_COUNT > 3
                PAGE    DB_PAGE_3
                SAVETAP "game128.tap", HEADLESS, DB_WINDOW, DB_BANK_USED_3
                ENDIF
                IF DB_BANK_COUNT > 4
                PAGE    DB_PAGE_4
                SAVETAP "game128.tap", HEADLESS, DB_WINDOW, DB_BANK_USED_4
                ENDIF
                IF DB_BANK_COUNT > 5
                PAGE    DB_PAGE_5
                SAVETAP "game128.tap", HEADLESS, DB_WINDOW, DB_BANK_USED_5
                ENDIF
