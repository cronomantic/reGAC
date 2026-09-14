; MIT License, Copyright (c) 2025 Cronomantic
;
; A build that draws one picture on a Spectrum Next and stops, so the tests can
; compare what is in layer 2 against what the reference renderer says.
;
; It is laid out the way the interpreter will be, in the part that matters: the
; database low, the code and the mask in the middle, and the sixteen kilobytes
; at $C000 kept for whichever piece of layer 2 is being drawn.  Nothing here
; needs the ROM, so nothing pages it back.
;
;       $0000   the database, in pages of its own
;       $8000   this build, its mask and its stack
;       $C000   a piece of layer 2
;
; It is loaded as a .nex file, which the assembler writes itself: the pages it
; was told to fill are in it, and so is where to start.

                DEVICE  ZXSPECTRUMNEXT

STACK_AT        equ $9F00
database        equ $0000
DB_FIRST_PAGE   equ 32                  ; the 8K pages the database is put in
DB_PAGES        equ 3

                ORG     $8000
start:
                di
                ld      sp, STACK_AT
                nextreg REG_TURBO, TURBO_28     ; the speed this machine has
                ; the database into the three pages below us
                ld      a, DB_FIRST_PAGE
                nextreg $50, a
                inc     a
                nextreg $51, a
                inc     a
                nextreg $52, a
                call    db_init
                call    config_init
                call    text_init
                call    screen_init
                call    picture_init
                ; fall through

; Drawing again needs none of the setting up, so the tests can poke a new
; number in here, clear the flag and point the processor back at this label.
redraw:
                ld      sp, STACK_AT
                ld      hl, (picture_wanted)
                call    draw_picture
                ld      a, $FF
                ld      (done_flag), a
                ; and from here it shows whichever piece of layer 2 is asked
                ; for, which is how a test reads the picture back: sixteen
                ; kilobytes of it are in the map at a time and only the machine
                ; itself can say which.
.stop:
                ld      a, (piece_wanted)
                call    map_piece
                jr      .stop

done_flag:      db      0
picture_wanted: dw      1
piece_wanted:   db      PIECE_TOP

                include "../common/database.asm"
                include "../common/config.asm"
                include "../common/unpack.asm"
                include "screen.asm"
                include "../common/textout.asm"
                include "draw.asm"
                include "../common/shapes.asm"
                include "fill.asm"
                include "../common/picture.asm"

last_code:
                ASSERT  last_code < MASK        ; or it would draw over itself

; The database, in pages of its own so that all of it is reachable at once:
; three of them mapped low, one after another, and then it is written across
; the three as if they were one stretch of memory -- which is what they are
; once the build has mapped them the same way.
                SLOT    0
                PAGE    DB_FIRST_PAGE
                SLOT    1
                PAGE    DB_FIRST_PAGE + 1
                SLOT    2
                PAGE    DB_FIRST_PAGE + 2
                SLOT    0
                ORG     $0000
                INCBIN  "picture.rgac"

                SAVENEX OPEN "picture.nex", start, STACK_AT
                SAVENEX CORE 3, 0, 0
                SAVENEX CFG  0
                SAVENEX AUTO
                SAVENEX CLOSE
