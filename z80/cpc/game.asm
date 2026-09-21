; MIT License, Copyright (c) 2025 Cronomantic
;
; The Amstrad interpreter: everything put together and playing.

                DEVICE  AMSTRADCPC6128

; An adventure that asks for a noise is told so with -DNOISES, and then
; the sound chip engine travels with it.  There is no music: the tracker
; player was taken out, and with it the second file that used to be
; carried down under $4000 -- see doc/pendiente.md.
FIRMWARE_AT     equ $B100               ; what the firmware keeps for itself
; Where BASIC's own is, while it loads: the cassette buffer is the two
; kilobytes under HIMEM, which the loader sets to $3FFF, and the variables of
; a six line program grow down from there and want almost nothing.
BASIC_KEEPS_FROM equ $3700

; An adventure whose database does not leave room for the interpreter above
; $4000 -- the two parts of the Quijote are the ones that do not -- is built
; with -DLOW_CODE, and then the two change places: the interpreter goes into
; the sixteen kilobytes under $4000, which are RAM like any other with both
; ROMs out of the way, and the database has everything from $4000 to the
; island below.  That gives it 27392 bytes instead of the eight and a half
; thousand it has left over the interpreter.
;
;   $0400  the interpreter, which is some 8200 bytes
;   $4000  the database, all of it
;   $AB00  the island: a copy of the game and the two calls that put it on
;          tape, which cannot be under $4000 -- see tape.asm
;   $B100  the firmware's own
;
; It cannot be loaded where it runs, because the BASIC line that loads it is
; itself at $0170: the file comes in at $4000 with a mover in front of it,
; the mover carries it down and comes back, and then the database is loaded
; over where it landed.
                IFDEF LOW_CODE
CODE_AT         equ $0400
CODE_LOADS_AT   equ $4000               ; where its file comes in, to be moved
DATABASE_AT     equ $4000
ISLAND_AT       equ $AB00
; The mover, and with it the seven bytes that start the thing.  BASIC cannot
; call $0400 itself: at that moment the lower ROM is still in and $0400 is
; ROM, not the interpreter.  So what BASIC calls is the starter, up where
; there is no ROM, which puts both of them out of the way and jumps down.  It
; is left where the island goes, which the interpreter writes over once it is
; running and has no more use for it.
                ORG     CODE_LOADS_AT
code_mover:
                ld      hl, starter
                ld      de, ISLAND_AT
                ld      bc, starter_end - starter
                ldir
                ld      hl, code_image
                ld      de, CODE_AT
                ld      bc, CODE_BYTES
                ldir
                ret

; Assembled here and run up there: it names no address of its own.
starter:
                di
                ld      bc, GATE_ARRAY
                ld      a, MODE_1               ; mode one, both ROMs out
                out     (c), a
                jp      CODE_AT
starter_end:

code_image:
                DISP    CODE_AT
                ELSE
                ; above the lower ROM, which covers anything under $4000
                ORG     $4000
                ENDIF
start:
                di
                ld      sp, $BF00
                IFDEF LOW_CODE
                call    island_init             ; the tape's calls, up above
                ENDIF
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

                include "../common/database.asm"
                include "../common/config.asm"
                include "../common/unpack.asm"
                include "screen.asm"
                include "../common/textout.asm"
                include "keyboard.asm"
; This machine's only speaker is its sound chip, so ay.asm is what clicks and
; what makes a noise here.  It is not included from this file: it comes in
; with keyboard.asm above, because the click is the keyboard's business.  What
; it carries is not all of a piece -- the chip access and one flat note are
; forty odd bytes and travel always, because the original clicked at every
; key; the table of effects and the player that walks a pitch are another
; hundred and four and travel only with -DNOISES, which none of the eight of
; 1986 needs, since SOUND and QUIET are opcodes of ours.
                include "tape.asm"
                include "draw.asm"
                include "shapes.asm"
                include "fill.asm"
                include "../common/conditions.asm"
                include "../common/opcodes.asm"
                include "../common/parser.asm"
                include "../common/loop.asm"
                include "../common/picture.asm"

                IFDEF LOW_CODE
; The database is not in here: it is a file of its own, loaded at $4000 after
; the mover has carried this down.  How much of it fits is the builder's to
; check, because the assembler never sees it.
last:
                ; Not up to $4000 but well short of it, because the mover runs
                ; as a CALL from BASIC and BASIC is still alive underneath:
                ; with HIMEM at $3FFF the cassette buffer is the two kilobytes
                ; below it and the loader's variables grow down from there, so
                ; an LDIR that reached them would come back to nothing.
                ASSERT  last <= BASIC_KEEPS_FROM
database        equ DATABASE_AT
CODE_BYTES      equ last - start
                ENT                             ; back to where the file loads

                SAVEBIN "game.bin", code_mover, last - start + code_image - code_mover
                ELSE
database:
                INCBIN  "game.rgac"
last:
                ASSERT  last <= FIRMWARE_AT     ; or the tape would stop working

                SAVEBIN "game.bin", start, last - start
                ENDIF

