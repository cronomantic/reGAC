; MIT License, Copyright (c) 2025 Cronomantic
;
; The Amstrad interpreter: everything put together and playing.

                DEVICE  AMSTRADCPC6128

; A build with music is told so with -DWITH_MUSIC, and one with sound effects
; as well with -DWITH_EFFECTS.  What it then takes in is the author's own
; music/tunes.asm, which says what tunes there are.
;
; This is the tightest of the four machines that can play anything.  The code,
; the database and now the music are one stretch from $4000, and what stops
; them is the firmware's own variables at $B100 -- the firmware is asleep, but
; the tape is saved through its jumpblock, so what it keeps down there has to
; stay.  Sixteen kilobytes are going begging under $4000, where both ROMs are
; out of the way, but nothing can be loaded there: the BASIC line that loads
; this is itself at $0170 and would be loaded over while it ran.  So for now
; an adventure with music has to end before $A200 or so, and the ASSERT below
; says which ones do not.  doc/pendiente.md has what the way out looks like.
                IFDEF WITH_MUSIC
                DEFINE  PLY_AKM_HARDWARE_CPC 1
                DEFINE  MUSIC_RATE 300          ; this one interrupts that often
                IFDEF WITH_EFFECTS
                DEFINE  PLY_AKM_MANAGE_SOUND_EFFECTS 1
                ENDIF
                ENDIF

FIRMWARE_AT     equ $B100               ; what the firmware keeps for itself

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

                IFDEF WITH_MUSIC
                include "../common/music.asm"
                include "../arkos/PlayerAkm.asm"
                include "interrupt.asm"
                IFDEF PLY_AKM_MANAGE_SOUND_EFFECTS
; The effects are not paged and not copied: one is asked for in the middle of
; a turn and has to be there, so the bank lives with the player.
effects:
                include "../../music/effects.asm"
                ENDIF
                DEFINE  MUSIC_LIST 1    ; no banks here, so the list and
                DEFINE  MUSIC_STORE 1   ; the tunes live side by side
                include "../../music/tunes.asm"
                UNDEFINE MUSIC_LIST
                UNDEFINE MUSIC_STORE
                ENDIF

                ALIGN   256
database:
                INCBIN  "game.rgac"
last:
                ASSERT  last <= FIRMWARE_AT     ; or the tape would stop working

                SAVEBIN "game.bin", start, last - start
