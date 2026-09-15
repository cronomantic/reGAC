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

; A build with music is told so with -DWITH_MUSIC, and one with sound effects
; as well with -DWITH_EFFECTS, exactly as on a 128: the machine is the same
; one and the music goes in the same places.  What differs is that the pieces
; do not travel as blocks of a tape but as more of the one file the loader
; reads, and that this machine has fewer pages to spare.
                IFDEF WITH_MUSIC
                DEFINE  PLY_AKM_HARDWARE_SPECTRUM 1
                DEFINE  MUSIC_PAGED 1
                IFDEF WITH_EFFECTS
                DEFINE  PLY_AKM_MANAGE_SOUND_EFFECTS 1
                ENDIF
                ENDIF

; The pages a +3 has to spare, in the order the database numbers its banks.
DB_PAGE_0       equ 0
DB_PAGE_1       equ 1
DB_PAGE_2       equ 3
DB_PAGE_3       equ 4
DB_PAGE_4       equ 0                   ; there is no fifth or sixth to give,
DB_PAGE_5       equ 0                   ; which is what the next line says
                IFDEF WITH_MUSIC
                ; The tunes want a page of their own, and it comes out of the
                ; four: an adventure of three banks has music on this machine
                ; and one of four has not.
MUSIC_PAGE      equ DB_PAGE_3
                ASSERT DB_BANK_COUNT <= 3
                ELSE
                ASSERT DB_BANK_COUNT <= 4
                ENDIF

; Where the music lives, which is the 128's arrangement: the player below the
; interpreter, in the page that is always there, and the buffer a tune is
; played out of filling what is left up to the stack.
MUSIC_AT        equ $6000
MUSIC_CEILING   equ $7C00

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

                IFDEF WITH_MUSIC
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
                include "../common/shapes.asm"
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
                IFDEF WITH_MUSIC
                ASSERT  last <= IM2_TABLE       ; or it would run into the
                ENDIF                           ; interrupt's own corner

                IFDEF SCREEN
                SAVEBIN "game3_screen.bin", loading_screen, SCREEN_BYTES
                ENDIF
                SAVEBIN "game3_code.bin", start, last - start
                SAVEBIN "game3_boot.bin", basic, basic_end - basic
                IFDEF WITH_MUSIC
                ; The two pieces the music is, in the order the load table
                ; asks for them: the player and then the tunes.
                SLOT    1
                PAGE    5
                SAVEBIN "game3_music.bin", MUSIC_AT, MUSIC_BYTES
                SLOT    3
                PAGE    MUSIC_PAGE
                SAVEBIN "game3_tunes.bin", DB_WINDOW, MUSIC_STORE_BYTES
                ENDIF
