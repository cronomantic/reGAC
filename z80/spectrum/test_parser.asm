; MIT License, Copyright (c) 2025 Cronomantic
;
; A build that makes sense of one sentence and stops, so the tests can read
; the verb, the nouns and the adverb it settled on.  The sentence is written
; by the test into parser_input.inc.

                DEVICE  ZXSPECTRUM48

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
                call    vm_init
                call    vocab_init

                ; turn what was typed into this adventure's own codes
                ld      hl, input_text
                ld      de, input_buffer
                ld      b, input_length
.convert:
                ld      a, (hl)
                push    hl
                push    de
                push    bc
                call    ascii_to_code
                pop     bc
                pop     de
                pop     hl
                ld      (de), a
                inc     hl
                inc     de
                djnz    .convert

                ld      hl, input_buffer
                ld      bc, input_length
                call    parse_sentence
                ld      a, 0
                jr      nc, .not_understood
                inc     a
.not_understood:
                ld      (understood), a

                ld      a, $FF
                ld      (done_flag), a
.stop:
                jr      .stop

understood:     db      0
done_flag:      db      0

                include "parser_input.inc"

                include "../common/database.asm"
                include "../common/config.asm"
                include "../common/unpack.asm"
                include "screen.asm"
                include "../common/textout.asm"
                include "keyboard.asm"
                include "tape.asm"
                include "../common/conditions.asm"
                include "draw.asm"
                include "../common/shapes.asm"
                include "fill.asm"
                include "../common/opcodes.asm"
                include "../common/parser.asm"
                include "../common/picture.asm"

                ALIGN   256
database:
                INCBIN  "parser.rgac"

                SAVESNA "parser.sna", start
