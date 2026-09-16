; MIT License, Copyright (c) 2025 Cronomantic
;
; The same interpreter on a 6128, which loads from disk and keeps its
; database in the second sixty four kilobytes.
;
; The map is not the 464's, and what decides it is the paging: the only
; sixteen kilobytes the gate array can swap are the ones at $4000, so the
; window goes there and everything else moves around it.
;
;   $0100-$02FF  free: below it are the restarts and the BASIC line that
;                 loaded us, and neither is worth stepping on
;   $0300-$1FFF  the music, when there is any, as on a 464
;   $2000-$3FFF  what is resident of the database, or from $0300 with no music
;   $4000-$7FFF  the window, one of four banks at a time
;   $8000-$BEFF  the interpreter, with the stack on top of it
;   $C000-$FFFF  the screen
;
; And one consequence worth knowing, because it is what settles the medium:
; this build never calls the firmware.  Its entries are restarts, and a
; restart brings the lower ROM back for as long as the routine lasts, which
; would cover the resident half of the database while it did.  So the tape is
; out -- a game is saved on the disk, by sectors, the way the PCW does it --
; and nothing here goes through the jumpblock.
;
; What comes out is not a medium but its pieces, because the disk is put
; together by regac release:
;
;   python -m regac build partida.json game6128.rgac -m cpc -b 16k \
;          --defs banks6128.inc

                DEFINE  BANKED
                DEVICE  AMSTRADCPC6128

                include "banks6128.inc"

; The four arrangements of the gate array's RAM register that swap the window
; and leave the rest of the map alone.  There are only four, which is the one
; hard limit of this machine: sixty four kilobytes of database and no more.
DB_PAGE_0       equ $C4
DB_PAGE_1       equ $C5
DB_PAGE_2       equ $C6
DB_PAGE_3       equ $C7
                ASSERT DB_BANK_COUNT <= 4

; A build with music is told so with -DWITH_MUSIC, and one with sound effects
; as well with -DWITH_EFFECTS.  The music lives where it does on a 464 and
; travels the same way, in a file of its own with a mover in front of it: the
; loader brings it in at $4000, calls it, and it carries itself down.
                IFDEF WITH_MUSIC
                DEFINE  PLY_AKM_HARDWARE_CPC 1
                DEFINE  MUSIC_RATE 300          ; this one interrupts that often
                IFDEF WITH_EFFECTS
                DEFINE  PLY_AKM_MANAGE_SOUND_EFFECTS 1
                ENDIF
                ENDIF

MUSIC_AT        equ $0300               ; above the BASIC line that loads us
MUSIC_CEILING   equ $2000               ; and below what the database wants
MUSIC_LOADS_AT  equ $4000               ; where its file comes in, to be moved

; Where the resident half of the database ends up, and where the loader has
; left it: it comes in through the window, in the bank that is there when
; nothing has been paged, and none of the four ever covers that one.
;
; Music costs it room, because both live in the sixteen kilobytes under the
; window: with a tune there are eight kilobytes for what stays resident and
; without one there are nearly sixteen.  Which is a thing to know before
; giving an adventure music on this machine, and the assert below says so at
; build time rather than in play.
                IFDEF WITH_MUSIC
database        equ MUSIC_CEILING
                ELSE
database        equ MUSIC_AT
                ENDIF
RESIDENT_LOADS  equ $4000
                ASSERT  database + DB_RESIDENT_SIZE <= RESIDENT_LOADS

STACK_AT        equ $BF00

                ORG     $8000
start:
                jr      start_up

; Where the saved game is on the disk: the track and the record its file
; starts at, and how many sectors it has.  The builder writes these three once
; it has laid the disk out -- CPC6128_SAVE_WHERE in media.py is where in this
; file it writes them -- and disc.asm reads them.  A build that was never put
; on a disk that way leaves them nought, and saving says it could not.
save_where:     db      0, 0, 0
                ASSERT  save_where == $8002

start_up:
                di
                ld      sp, STACK_AT
                ; the resident half down out of the window, before anything
                ; asks for a bank and takes it away
                ld      hl, RESIDENT_LOADS
                ld      de, database
                ld      bc, DB_RESIDENT_SIZE
                ldir
                call    keyboard_init
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
                IFNDEF WITH_MUSIC
                IFDEF NOISES
                include "ay.asm"
                ENDIF
                ENDIF
                include "disc.asm"
                include "draw.asm"
                include "shapes.asm"
                include "fill.asm"
                include "../common/conditions.asm"
                include "../common/opcodes.asm"
                include "../common/parser.asm"
                include "../common/loop.asm"
                include "../common/picture.asm"
last:
                ASSERT  last <= STACK_AT        ; or the stack would land in it
                ASSERT  last <= SAVE_AREA       ; or a saved game would land on us
                ASSERT  SAVE_AREA + SAVE_BYTES <= STACK_AT - 256
                ASSERT  vm_state_end - vm_state <= SAVE_BYTES   ; and a game fits

                SAVEBIN "game6128.bin", start, last - start

; And the music, as a file of its own, exactly as on a 464: assembled for
; $0300 and stored behind a mover that is put where the loader brings it in.
                IFDEF WITH_MUSIC
                ORG     MUSIC_LOADS_AT
music_mover:
                ld      hl, music_image
                ld      de, MUSIC_AT
                ld      bc, MUSIC_BYTES
                ldir
                ret

music_image:
                DISP    MUSIC_AT
music_at:
                include "../common/music.asm"
                include "../arkos/PlayerAkm.asm"
                include "interrupt.asm"
                IFDEF PLY_AKM_MANAGE_SOUND_EFFECTS
effects:
                include "../../music/effects.asm"
                ENDIF
                DEFINE  MUSIC_LIST 1
                DEFINE  MUSIC_STORE 1
                include "../../music/tunes.asm"
                UNDEFINE MUSIC_LIST
                UNDEFINE MUSIC_STORE
music_end:
MUSIC_BYTES     equ music_end - music_at
                ASSERT  music_end <= MUSIC_CEILING
                ENT
music_image_end:
                SAVEBIN "game6128_music.bin", music_mover, music_image_end - music_mover
                ENDIF
