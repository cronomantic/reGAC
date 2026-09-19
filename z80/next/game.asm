; MIT License, Copyright (c) 2025 Cronomantic
;
; The Spectrum Next interpreter: everything put together and playing.
;
; The map is the whole of what is this machine's own, and it is full:
;
;   $0000  the window a bank of the database appears in -- or the 48K ROM,
;          for as long as a save takes
;   $4000  the music, in a build that has any: seven kilobytes nothing else
;          wants, because this machine's screen is layer 2 and the sixteen
;          kilobytes a Spectrum keeps its screen in are free here
;   $5C00  left free, because that is where the ROM keeps its variables and
;          the ROM is borrowed to save a game
;   $5D00  what is resident of the database
;   $8000  this, and its buffers
;   $A000  the mask a fill walks, four kilobytes on its own boundary, and
;          wiped whole every time a picture is: nothing else may live there
;   $B000  the table mode two interrupts go through, and $B1B1 the routine it
;          points at, both put there when the music starts
;   $B200  free, some three kilobytes of it up to the stack -- which comes down
;          from $BF00 and was measured going thirty four bytes deep, drawing
;          every picture of four adventures and playing
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

; A build with music is told so with -DWITH_MUSIC, and one with sound effects
; as well with -DWITH_EFFECTS.  The sound chip here is the Spectrum's, at the
; same ports and the same clock, so the player is the Spectrum's as well.
                IFDEF WITH_MUSIC
                DEFINE  PLY_AKM_HARDWARE_SPECTRUM 1
                DEFINE  MUSIC_PAGED 1           ; the tunes live in pages
                IFDEF WITH_EFFECTS
                DEFINE  PLY_AKM_MANAGE_SOUND_EFFECTS 1
                ENDIF
                ENDIF

MUSIC_AT        equ $4000
MUSIC_CEILING   equ $5C00               ; where the ROM's variables begin
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
MUSIC_PAGE      equ DB_FIRST_PAGE + 12  ; and the two after all six of those

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

; And the music, in the same page, below where the database begins: the
; player, the bank of effects, the list of what tunes there are, and then the
; buffer a tune is played out of, which is whatever is left up to the ROM's
; variables.  All of it is written into the .nex with everything else in that
; page, so there is no loading to arrange.
;
; The tunes themselves are not here.  They are in two pages of their own --
; sixteen kilobytes, the size of the window they are read through -- and the
; one being played is copied into the buffer when it starts.  This machine has
; pages to spare, so they go after the last the database took.
                IFDEF WITH_MUSIC
                ORG     MUSIC_AT
music_at:
                include "../common/music.asm"
                include "../arkos/PlayerAkm.asm"
                include "interrupt.asm"
                IFDEF PLY_AKM_MANAGE_SOUND_EFFECTS
; The effects are not paged and not copied: one is asked for in the middle of
; a turn and has to be there, so the bank lives with the player.
effects:
                include "../../music/effects.asm"
                ENDIF
; The list of what tunes there are, which is read at any moment and so lives
; here and not in the pages they are in.
                DEFINE  MUSIC_LIST 1
                include "../../music/tunes.asm"
                UNDEFINE MUSIC_LIST
music_buffer:
MUSIC_BUFFER_BYTES equ MUSIC_CEILING - music_buffer
music_end:
                ASSERT  music_end <= MUSIC_CEILING

; And the tunes, in their own pages.  It comes after the player because the
; list is written with a macro the player's own source declares.
                SLOT    0
                PAGE    MUSIC_PAGE
                SLOT    1
                PAGE    MUSIC_PAGE + 1
                SLOT    0
                ORG     $0000
music_store:
                DEFINE  MUSIC_STORE 1
                include "../../music/tunes.asm"
                UNDEFINE MUSIC_STORE
music_store_end:
                SLOT    4
                PAGE    4
                ENDIF

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
                IFDEF WITH_MUSIC
                call    music_init
                IFDEF PLY_AKM_MANAGE_SOUND_EFFECTS
                ld      hl, effects
                call    sound_init
                ENDIF
                call    interrupt_init
                ENDIF
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
                include "../spectrum/keyboard.asm"
                include "tape.asm"
                include "draw.asm"
                include "../common/shapes.asm"
                include "fill.asm"
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
                ASSERT  last <= MASK            ; or the first picture wipes it
                ASSERT  last < STACK_AT         ; or the stack would land in it

; Above the mask there is room that nothing touches, and for a long time it
; went unused because the wall at $A000 looked like the end of the machine.
; It is not: gfx_clear wipes MASK for MASK_BYTES and stops there, and the
; stack comes down from STACK_AT, so between the end of one and the foot of
; the other there are nearly four kilobytes going spare.  They travel in the
; file already -- SAVENEX BANK 2 carries the whole of $8000 to $BFFF -- so a
; module put here costs nothing and leaves that much more room under the wall.
;
; The first kilobyte of it is spoken for, though: with music the mode two
; table is at $B000 and its routine just above, at $B1B1 -- see
; interrupt.asm, which says why they are as far from the stack as they can
; be.  So what goes here starts clear of both.
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
                IFDEF MUSIC_PAGED
                SAVENEX BANK MUSIC_PAGE / 2     ; and the tunes, in theirs
                ENDIF
                SAVENEX CLOSE
