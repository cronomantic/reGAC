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
;   $0300-$3FFF  what is resident of the database, nearly sixteen kilobytes
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
                DEFINE  PICTURE_INKS            ; its pictures carry their inks

                include "banks6128.inc"

; The four arrangements of the gate array's RAM register that swap the window
; and leave the rest of the map alone.  There are only four, which is the one
; hard limit of this machine: sixty four kilobytes of database and no more.
DB_PAGE_0       equ $C4
DB_PAGE_1       equ $C5
DB_PAGE_2       equ $C6
DB_PAGE_3       equ $C7
                ASSERT DB_BANK_COUNT <= 4

DATABASE_AT     equ $0300   ; above the BASIC line that loads us

; Where the resident half of the database ends up, and where the loader has
; left it: it comes in through the window, in the bank that is there when
; nothing has been paged, and none of the four ever covers that one.
;
database        equ DATABASE_AT
RESIDENT_LOADS  equ $4000
                ASSERT  database + DB_RESIDENT_SIZE <= RESIDENT_LOADS

STACK_AT        equ $BF00
MASK            equ (last + 255) & $FF00  ; see the ASSERT at the end

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
                include "disc.asm"
                include "pixels.asm"
                ; The rules of the GAC the adventure was written with: an
                ; adventure off an Amstrad is built with -DAMSTRAD_PICTURES and
                ; draws with the Amstrad's, and one off a Spectrum with the
                ; Spectrum's.  One or the other, never both.
                IFDEF   AMSTRAD_PICTURES
                include "draw.asm"
                include "shapes.asm"
                include "fill.asm"
                ELSE
                include "spectrum.asm"
                include "../common/shapes.asm"
                include "spectrum_fill.asm"
                ENDIF
                include "../common/conditions.asm"
                include "../common/opcodes.asm"
                include "../common/parser.asm"
                include "../common/loop.asm"
                include "../common/picture.asm"
last:
                ASSERT  last <= STACK_AT        ; or the stack would land in it
                ; A picture off a Spectrum keeps its mask here while it is
                ; drawn.  It shares the room with where a saved game is put
                ; together, because the two are never wanted at once: the mask
                ; only while a picture is drawn, and a picture drawn after a
                ; game is loaded starts by wiping it.
                IFNDEF  AMSTRAD_PICTURES
                ASSERT  MASK + MASK_BYTES <= STACK_AT - 256
                ENDIF
                ASSERT  last <= SAVE_AREA       ; or a saved game would land on us
                ASSERT  SAVE_AREA + SAVE_BYTES <= STACK_AT - 256
                ASSERT  vm_state_end - vm_state <= SAVE_BYTES   ; and a game fits

                SAVEBIN "game6128.bin", start, last - start

