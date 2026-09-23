; MIT License, Copyright (c) 2025 Cronomantic
;
; The Spectrum Next interpreter: everything put together and playing.
;
; The map is the whole of what is this machine's own, and it is full:
;
;   $0000  the window a bank of the database appears in -- or the 48K ROM,
;          for as long as a save takes
;   $4000  free: a Spectrum keeps its screen here, and this machine's screen
;          is layer 2.  The tracker player and its tune lived here until the
;          music was taken out, and nothing has moved in since
;   $5C00  left free, because that is where the ROM keeps its variables and
;          the ROM is borrowed to save a game
;   $5D00  what is resident of the database
;   $8000  this, and its buffers
;   $A000  the mask a fill walks, four kilobytes on its own boundary, and
;          wiped whole every time a picture is: nothing else may live there.
;          Only an adventure off a Spectrum has one: one off an Amstrad is
;          drawn with the Amstrad's rules, whose pens are in layer 2 itself,
;          and there this is free
;   $B200  the picture interpreter, put above the mask (see ABOVE_MASK below),
;          and after it what is left of three kilobytes up to the stack --
;          which comes down from $BF00 and was measured going thirty four bytes
;          deep, drawing every picture of four adventures and playing
;   $C000  whichever sixteen kilobytes of layer 2 are wanted: the top half of
;          the picture, the bottom half, or the text
;
; Nothing of the machine is left over.  That is why layer 2 is seen a piece at
; a time rather than all at once: the database, the interpreter and forty
; eight kilobytes of screen do not fit in sixty four together.
;
; regac build writes banks.inc, which says how much of the file is resident
; and how many banks follow it:
;
;   python -m regac build partida.json game.rgac -m next -b 16k \
;          --defs banks.inc

                DEFINE  BANKED
                DEVICE  ZXSPECTRUMNEXT
; An adventure off an Amstrad: its pictures carry their inks, and the inks may
; flash.
                IFDEF   AMSTRAD_PICTURES
                DEFINE  PICTURE_INKS
                DEFINE  FLASHING_INKS
                ENDIF

                include "banks.inc"

; A build with a loading screen is told so with -DSCREEN, as on the Spectrum.
; The word is taken away again at once, and kept as another one: further down
; there is a `SAVENEX SCREEN` line, and a define is a substitution, so the
; assembler would put the value of SCREEN -- nothing at all -- in the middle
; of it and then not know what the line was.
                IFDEF SCREEN
                DEFINE  WITH_SCREEN
                UNDEFINE SCREEN
                ENDIF

STACK_AT        equ $BF00
DB_FIRST_PAGE   equ 32                  ; the 8K pages the banks are put in,
                                        ; clear of the ones a Spectrum has and
                                        ; of layer 2's own
database        equ $5D00

; A bank of the database is sixteen kilobytes, which is two of this machine's
; pages; they are mapped into the two slots the window is made of.
DB_PAGE_0       equ DB_FIRST_PAGE
DB_PAGE_1       equ DB_FIRST_PAGE + 2
DB_PAGE_2       equ DB_FIRST_PAGE + 4
DB_PAGE_3       equ DB_FIRST_PAGE + 6
DB_PAGE_4       equ DB_FIRST_PAGE + 8
DB_PAGE_5       equ DB_FIRST_PAGE + 10

; The banks themselves, each written across the two pages it is made of.
                IF DB_BANK_COUNT > 0
                SLOT    0
                PAGE    DB_PAGE_0
                SLOT    1
                PAGE    DB_PAGE_0 + 1
                SLOT    0
                ORG     $0000
                INCBIN  "game.rgac", DB_RESIDENT_SIZE, DB_BANK_BYTES
                ENDIF
                IF DB_BANK_COUNT > 1
                SLOT    0
                PAGE    DB_PAGE_1
                SLOT    1
                PAGE    DB_PAGE_1 + 1
                SLOT    0
                ORG     $0000
                INCBIN  "game.rgac", DB_RESIDENT_SIZE + DB_BANK_BYTES, DB_BANK_BYTES
                ENDIF
                IF DB_BANK_COUNT > 2
                SLOT    0
                PAGE    DB_PAGE_2
                SLOT    1
                PAGE    DB_PAGE_2 + 1
                SLOT    0
                ORG     $0000
                INCBIN  "game.rgac", DB_RESIDENT_SIZE + 2 * DB_BANK_BYTES, DB_BANK_BYTES
                ENDIF
                IF DB_BANK_COUNT > 3
                SLOT    0
                PAGE    DB_PAGE_3
                SLOT    1
                PAGE    DB_PAGE_3 + 1
                SLOT    0
                ORG     $0000
                INCBIN  "game.rgac", DB_RESIDENT_SIZE + 3 * DB_BANK_BYTES, DB_BANK_BYTES
                ENDIF
                IF DB_BANK_COUNT > 4
                SLOT    0
                PAGE    DB_PAGE_4
                SLOT    1
                PAGE    DB_PAGE_4 + 1
                SLOT    0
                ORG     $0000
                INCBIN  "game.rgac", DB_RESIDENT_SIZE + 4 * DB_BANK_BYTES, DB_BANK_BYTES
                ENDIF
                IF DB_BANK_COUNT > 5
                SLOT    0
                PAGE    DB_PAGE_5
                SLOT    1
                PAGE    DB_PAGE_5 + 1
                SLOT    0
                ORG     $0000
                INCBIN  "game.rgac", DB_RESIDENT_SIZE + 5 * DB_BANK_BYTES, DB_BANK_BYTES
                ENDIF

; What is resident goes in the page that is always at $4000, next to the mask.
                SLOT    2
                PAGE    10
                ORG     database
db_resident_image:
                INCBIN  "game.rgac", 0, DB_RESIDENT_SIZE
                ASSERT  $ <= $8000      ; or it would run into the interpreter

                SLOT    4
                PAGE    4
                ORG     $8000
start:
                di
                ld      sp, STACK_AT
                nextreg REG_TURBO, TURBO_28     ; the speed this machine has
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
; The Spectrum's keyboard, read at twenty eight megahertz: a fiftieth of a
; second is 559104 cycles here and a look at the keyboard with nothing held
; about 2080 of them, measured, so a frame would be 268 looks.  The count is
; a byte, so it is 255, and a frame here is five per cent short.
                DEFINE  NEXT_LOOKS_A_FRAME 255
                DEFINE  NEXT_LOOKS_HELD 247     ; a look with a key held, 2260
; This machine has a sound chip, so the noises and the key click go through
; it rather than through the speaker: see spectrum/keyboard.asm.
                DEFINE  WITH_AY 1
                include "../spectrum/keyboard.asm"
                include "tape.asm"
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
                include "../common/conditions.asm"
                include "../common/opcodes.asm"
                include "../common/parser.asm"
                include "../common/loop.asm"

last:
                ; Not past the mask.  This was the Next's "wall at $A000", which
                ; for a long time looked like bytes the file carried and the
                ; machine never received: they were received, and the first
                ; picture wiped them, because gfx_clear clears the mask and the
                ; mask is there.  Loaded with the processor held, a marker at
                ; $A020 is in memory; after the first room it is noughts, and
                ; one at $B300 is still there.
                IFNDEF  AMSTRAD_PICTURES
                ASSERT  last <= MASK            ; or the first picture wipes it
                ELSE
                ASSERT  last <= ABOVE_MASK      ; no mask: up to what is above it
                ENDIF
                ASSERT  last < STACK_AT         ; or the stack would land in it

; Above the mask there is room that nothing touches, and for a long time it
; went unused because the wall at $A000 looked like the end of the machine.
; It is not: gfx_clear wipes MASK for MASK_BYTES and stops there, and the
; stack comes down from STACK_AT, so between the end of one and the foot of
; the other there are nearly four kilobytes going spare.  They travel in the
; file already -- SAVENEX BANK 2 carries the whole of $8000 to $BFFF -- so a
; module put here costs nothing and leaves that much more room under the wall.
;
; What goes here has to be code that does not care where it is, and it is
; taken from the end of the list so that nothing before it changes order.
ABOVE_MASK      equ $B200
                ORG     ABOVE_MASK
above_mask:
                include "../common/picture.asm"
past_mask:
                ; Clear of the stack, with room for it to come down: a turn of
                ; the interpreter does not go deep, but the tape routines call
                ; the ROM and the ROM has its own ideas.
STACK_ROOM      equ 512
                ASSERT  past_mask <= STACK_AT - STACK_ROOM

; A loading screen, if the build says there is one.  It is put where layer 2
; keeps its own memory and the file carries it in front of everything else, so
; the machine's own loader has it up before a byte of the adventure is in.
                IFDEF WITH_SCREEN
                SLOT    0
                PAGE    L2_FIRST_PAGE
                SLOT    1
                PAGE    L2_FIRST_PAGE + 1
                SLOT    2
                PAGE    L2_FIRST_PAGE + 2
                SLOT    3
                PAGE    L2_FIRST_PAGE + 3
                SLOT    0
                ORG     $0000
                INCBIN  "screen.bin", 0, 4 * $2000
                SLOT    0
                PAGE    L2_FIRST_PAGE + 4
                SLOT    1
                PAGE    L2_FIRST_PAGE + 5
                SLOT    0
                ORG     $0000
                INCBIN  "screen.bin", 4 * $2000
                ENDIF

                SAVENEX OPEN "game.nex", start, STACK_AT
                SAVENEX CORE 3, 0, 0
                IFDEF WITH_SCREEN
                SAVENEX CFG  0                  ; black border while it loads
                SAVENEX SCREEN L2
                ELSE
                SAVENEX CFG  0
                ENDIF
                ; The banks are named rather than gathered, so that layer 2's
                ; own three do not travel twice over: the loading screen is in
                ; the file already, in front.
                SAVENEX BANK 5, 2
                IF DB_BANK_COUNT > 0
                SAVENEX BANK DB_PAGE_0 / 2
                ENDIF
                IF DB_BANK_COUNT > 1
                SAVENEX BANK DB_PAGE_1 / 2
                ENDIF
                IF DB_BANK_COUNT > 2
                SAVENEX BANK DB_PAGE_2 / 2
                ENDIF
                IF DB_BANK_COUNT > 3
                SAVENEX BANK DB_PAGE_3 / 2
                ENDIF
                IF DB_BANK_COUNT > 4
                SAVENEX BANK DB_PAGE_4 / 2
                ENDIF
                IF DB_BANK_COUNT > 5
                SAVENEX BANK DB_PAGE_5 / 2
                ENDIF
                SAVENEX CLOSE
