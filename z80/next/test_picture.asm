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
; An adventure off an Amstrad: its pictures carry their inks.  They may flash,
; but only while a key is waited for, and this build waits for none.
                IFDEF   AMSTRAD_PICTURES
                DEFINE  PICTURE_INKS
                ENDIF

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

; Drawing again is asked for with go_flag: a test writes the picture's number,
; clears done_flag and sets go_flag, and the loop the build parks in sees it
; and comes back here.  It used to be asked for by writing this label into the
; program counter while the processor ran, and that is not safe: the emulator
; takes its orders on a thread of its own, and a program counter changed
; between an instruction's first byte and the rest of it finishes the
; instruction with bytes from here.  In the parking loop that instruction can
; be a CALL, whose address then comes out of the LD SP in front of this -- a
; call into the database, which fits what the Next's test caught now and then:
; the processor and the stack both down in the database, and code trampled.
; Asked with this byte instead, ten rounds of that test in a row came out
; clean, and none of them needed asking twice.  A byte of memory has nothing
; in the middle to be caught in.
redraw:
                ld      sp, STACK_AT
                xor     a
                ld      (go_flag), a
                ld      hl, (picture_wanted)
                call    draw_picture
                ld      a, $FF
                ld      (done_flag), a
                ; and from here it shows whichever piece of layer 2 is asked
                ; for, which is how a test reads the picture back: sixteen
                ; kilobytes of it are in the map at a time and only the machine
                ; itself can say which.
.stop:
                ld      a, (go_flag)
                or      a
                jr      nz, redraw
                ld      a, (piece_wanted)
                call    map_piece
                jr      .stop

done_flag:      db      0
go_flag:        db      0
picture_wanted: dw      1
piece_wanted:   db      PIECE_TOP

                include "../common/database.asm"
                include "../common/config.asm"
                include "../common/unpack.asm"
                include "screen.asm"
                include "../common/textout.asm"
                include "pixels.asm"
                ; The rules of the GAC the adventure was written with: an
                ; adventure off an Amstrad is built with -DAMSTRAD_PICTURES and
                ; draws with the Amstrad's, and one off a Spectrum with the
                ; Spectrum's.  One or the other, never both.
                IFDEF   AMSTRAD_PICTURES
                include "amstrad.asm"
                include "../cpc/shapes.asm"
                include "amstrad_fill.asm"
                ELSE
                include "draw.asm"
                include "../common/shapes.asm"
                include "fill.asm"
                ENDIF
                include "../common/picture.asm"

last_code:
                IFNDEF  AMSTRAD_PICTURES
                ASSERT  last_code < MASK        ; or it would draw over itself
                ENDIF

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
