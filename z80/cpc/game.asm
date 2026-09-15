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
MUSIC_AT        equ $0300               ; above the BASIC line that loads us
MUSIC_LOADS_AT  equ $4000               ; where its file comes in, to be moved

                ; above the lower ROM, which covers anything under $4000
                ORG     $4000
start:
                di
                ld      sp, $BF00
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

                include "../common/database.asm"
                include "../common/config.asm"
                include "../common/unpack.asm"
                include "screen.asm"
                include "../common/textout.asm"
                include "keyboard.asm"
                include "tape.asm"
                include "draw.asm"
                include "shapes.asm"
                include "fill.asm"
                include "../common/conditions.asm"
                include "../common/opcodes.asm"
                include "../common/parser.asm"
                include "../common/loop.asm"
                include "../common/picture.asm"

                ALIGN   256
database:
                INCBIN  "game.rgac"
last:
                ASSERT  last <= FIRMWARE_AT     ; or the tape would stop working

                SAVEBIN "game.bin", start, last - start

; And the music, as a file of its own.  It is assembled here, after the
; interpreter has been written out, because the mover in front of it is put
; where the interpreter will be loaded: by the time that matters, game.bin is
; already a file.
;
; The music itself is assembled for $0300 and stored behind the mover, which
; is what DISP is for -- the same way the interrupt's routine travels.
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
                ASSERT  music_end <= MUSIC_LOADS_AT     ; or it would reach the
                ENT                                     ; interpreter
MUSIC_BYTES     equ music_end - music_at

                SAVEBIN "music.bin", music_mover, $ - music_mover
                ENDIF
