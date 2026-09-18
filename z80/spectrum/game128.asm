; MIT License, Copyright (c) 2025 Cronomantic
;
; The same interpreter on a 128, with the database living in memory banks.
;
; What changes is only where the database is.  What the interpreter touches at
; any moment without warning stays resident, next to the code in page two;
; the text, the pictures and the music go to pages of their own and are
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

; A build with music is told so with -DWITH_MUSIC, and one with sound effects
; as well with -DWITH_EFFECTS.  What it then takes in is the author's own
; music/tunes.asm, which says what tunes there are; doc/pendiente.md has the
; shape of it.  Without them not a byte of any of this is in the build.
                IFDEF WITH_MUSIC
                DEFINE  PLY_AKM_HARDWARE_SPECTRUM 1
                DEFINE  MUSIC_PAGED 1           ; the tunes live in a page
                IFDEF WITH_EFFECTS
                DEFINE  PLY_AKM_MANAGE_SOUND_EFFECTS 1
                ENDIF
                ENDIF

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

; The music, if there is any, goes below the interpreter and not above it.
; Above it there is nothing to spare: the interpreter, what is resident of the
; database and the interrupt's own corner fill the map to $C000.  Below it
; there is a great deal -- the screen ends at $5B00 and the stack starts at
; $8000, and the only thing in between is the BASIC line the loader travelled
; in, which has done its work by the time any of this runs.  So the player
; goes at $6000, and what is left over from there to $7C00 is the buffer a
; tune is played out of.
;
; The tunes themselves are not here at all: they are in a page of their own,
; and the one being played is copied down into the buffer when it starts.
; That way a tune costs nothing of the sixty four kilobytes until it plays,
; and what a build pays for having twenty of them is the biggest one once.
;
; The page they are in is the one after the last the database took.  Six are
; free on this machine and an adventure that took all six would leave none, so
; there is an assert to say so rather than a tune played over the text.
MUSIC_AT        equ $6000
MUSIC_CEILING   equ $7C00               ; leaving the stack the rest
MUSIC_PAGE      equ DB_PAGE_5           ; the last of the six

                IFDEF WITH_MUSIC
                ASSERT  DB_BANK_COUNT <= 5      ; or there is no page for it
                SLOT    2
                PAGE    2
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
; here and not in the page they are in.
                DEFINE  MUSIC_LIST 1
                include "../../music/tunes.asm"
                UNDEFINE MUSIC_LIST

music_buffer:
MUSIC_BUFFER_BYTES equ MUSIC_CEILING - music_buffer
music_end:
MUSIC_BYTES     equ music_end - music_at
                ASSERT  music_end <= MUSIC_CEILING

; And the tunes, in a page of their own.  It comes after the player because
; the list is written with a macro the player's own source declares.
                SLOT    3
                PAGE    MUSIC_PAGE
                ORG     $C000
music_store:
                DEFINE  MUSIC_STORE 1
                include "../../music/tunes.asm"
                UNDEFINE MUSIC_STORE
music_store_end:
MUSIC_STORE_BYTES equ music_store_end - music_store
                SLOT    2
                PAGE    2
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
                IFDEF WITH_MUSIC
                ASSERT  last <= IM2_TABLE       ; or it would run into the
                ENDIF                           ; interrupt's own corner

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
                IFDEF WITH_MUSIC
                SLOT    1
                PAGE    5                       ; where $6000 always is
                SAVETAP "game128.tap", HEADLESS, MUSIC_AT, MUSIC_BYTES
                SLOT    3
                PAGE    MUSIC_PAGE              ; and the tunes, in theirs
                SAVETAP "game128.tap", HEADLESS, DB_WINDOW, MUSIC_STORE_BYTES
                ENDIF
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
