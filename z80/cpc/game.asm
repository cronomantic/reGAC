; MIT License, Copyright (c) 2025 Cronomantic
;
; The Amstrad interpreter: everything put together and playing.

                DEVICE  AMSTRADCPC6128

; A build with music is told so with -DWITH_MUSIC, and one with sound effects
; as well with -DWITH_EFFECTS.  What it then takes in is the author's own
; music/tunes.asm, which says what tunes there are.
;
; The music does not go where the interpreter is.  Above $4000 there is
; nothing to spare -- the code and the database are one stretch and the
; firmware's own variables stop them at $B100, because the tape is saved
; through its jumpblock -- and the sixteen kilobytes under $4000 are empty
; and ours, with both ROMs out of the way.  What stopped them being used was
; the loading and not the memory: the BASIC line that loads the game is itself
; at $0170, and a file loaded down there would land on the loader while it
; ran.
;
; So the music travels as a second file with a mover in front of it: the
; loader brings it in at $4000, where nothing is yet, calls it, and twenty
; instructions carry the music down to $0300 -- clear of the BASIC line, which
; is the whole of the trick -- and come back.  Then the interpreter is loaded
; over the top of where it was and started, and finds the music waiting.
                IFDEF WITH_MUSIC
                DEFINE  PLY_AKM_HARDWARE_CPC 1
                DEFINE  MUSIC_RATE 300          ; this one interrupts that often
                IFDEF WITH_EFFECTS
                DEFINE  PLY_AKM_MANAGE_SOUND_EFFECTS 1
                ENDIF
                ENDIF

FIRMWARE_AT     equ $B100               ; what the firmware keeps for itself
MUSIC_LOADS_AT  equ $4000               ; where its file comes in, to be moved

; Where the music ends up is not the same in the two builds, so it is named
; further down, once it is known which one this is.  The usual way round it is
; $0300, above the BASIC line that loads us and under everything else, where
; there is nothing else to want the room.
;
; In a low build the interpreter is down there, and the music goes to the
; other end instead: the five kilobytes under the island, which is room the
; database would otherwise have had.  Above the interpreter would have been
; less trouble and it was tried, but it left a hundred and eighty three bytes
; between the two and the interpreter is the thing that grows.  This way it
; keeps the whole of the low RAM -- some four and a half kilobytes spare --
; and what the database loses still leaves it bigger than it is the usual way
; round, where the interpreter is eating into it from below.
MUSIC_ROOM      equ $1400               ; five kilobytes, and the assert says
                                        ; so if a set of tunes wants more

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
; It travels like the music does, because the BASIC line that loads it is
; itself at $0170: the file comes in at $4000 with a mover in front of it,
; the mover carries it down and comes back, and then the database is loaded
; over where it landed.
;
; This goes with music, and the two no longer fight over the same bytes,
; because the music moves: in a low build it is put in the five kilobytes
; under the island rather than at $0300, which is where the interpreter now
; is.  So the interpreter has the low RAM to itself and what the music costs
; comes off the end of the database, which even so is left bigger than it is
; the usual way round.
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

                include "../common/database.asm"
                include "../common/config.asm"
                include "../common/unpack.asm"
                include "screen.asm"
                include "../common/textout.asm"
                include "keyboard.asm"
; Without music there is still SOUND, and this machine's only speaker is its
; sound chip: ay.asm makes the same noises the others make with a bit of a
; port.  It comes in before the opcodes, which ask whether there is anything
; here that can make one.  With music the effects are the tracker's and this
; stays out -- and so does it when the adventure never asks for a noise,
; which the build says with NOISES and which none of the eight of 1986 does:
; SOUND and QUIET are opcodes of ours.  A hundred and sixty three bytes on a
; machine that counts them one by one.
                IFNDEF WITH_MUSIC
                IFDEF NOISES
                include "ay.asm"
                ENDIF
                ENDIF
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

; And the music, as a file of its own.  It is assembled here, after the
; interpreter has been written out, because the mover in front of it is put
; where the interpreter will be loaded: by the time that matters, game.bin is
; already a file.
;
; The music itself is assembled for $0300 and stored behind the mover, which
; is what DISP is for -- the same way the interrupt's routine travels.
                IFDEF WITH_MUSIC
                IFDEF LOW_CODE
MUSIC_AT        equ ISLAND_AT - MUSIC_ROOM
                ELSE
MUSIC_AT        equ $0300
                ENDIF
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
; The effects are not paged and not copied: one is asked for in the middle of
; a turn and has to be there, so the bank lives with the player.
effects:
                include "../../music/effects.asm"
                ENDIF
                DEFINE  MUSIC_LIST 1    ; no banks to page here, so the list
                DEFINE  MUSIC_STORE 1   ; and the tunes live side by side
                include "../../music/tunes.asm"
                UNDEFINE MUSIC_LIST
                UNDEFINE MUSIC_STORE
music_end:
                IFDEF LOW_CODE
                ASSERT  music_end <= ISLAND_AT          ; or it would reach the
                ELSE                                    ; island
                ASSERT  music_end <= MUSIC_LOADS_AT     ; or it would reach the
                ENDIF                                   ; interpreter
                ENT
MUSIC_BYTES     equ music_end - music_at

                SAVEBIN "game_music.bin", music_mover, $ - music_mover
                ENDIF
