; MIT License, Copyright (c) 2025 Cronomantic
;
; The PC interpreter: everything put together and playing, on an IBM PC or
; anything like one, with a CGA or anything that does its 320 by 200 mode.
;
; Assembled with NASM into a flat image, and given its .EXE header by regac:
;
;   nasm -f bin -I x86/ -DDATABASE="game.rgac" -o game.bin x86/game.asm
;
; with -DAMSTRAD_PICTURES for an adventure off an Amstrad.  No linker: the
; image is three pieces, each starting on a paragraph of its own, and the
; program works out where the second and third are from where DOS put the
; first:
;
;   the code        CS, which the header says starts at nought
;   the data        DS, straight after it
;   the database    straight after that, a segment to each of its sections
;
; and the stack is the header's, in a segment of its own behind all of it.
; See doc/pendiente.md.

bits 16
cpu 8086

section .text start=0
section .data follows=.text align=16 vstart=0
data_start:
section .database follows=.data align=16 vstart=0
database:
                incbin  DATABASE
section .text

start:
                mov     ax, cs
                add     ax, DATA_PARAGRAPH
                mov     ds, ax
                mov     [psp_seg], es           ; DOS hands it over in ES
                mov     ax, cs
                add     ax, DATABASE_PARAGRAPH
                mov     [db_seg], ax
                cld
                %ifdef TRANSCRIPT
                call    transcript_init
                %endif
                call    db_init
                call    db_picture_head
                call    config_init
                call    text_init
                call    screen_init
                call    picture_init
                call    vm_init
                call    vocab_init
                call    loop_init
                call    save_init
                call    timer_init
                call    keyboard_init
                ; the player starts where the adventure says
                mov     al, SECTION_CONFIG
                call    db_section
                mov     ax, [es:si]
                mov     [vm_location], ax
                call    play
                %ifdef TRANSCRIPT
                call    transcript_done
                %endif
                ; The score stays on the screen until a key is typed, and
                ; then it is back to DOS as it was left.
                call    next_key
                call    keyboard_done
                call    timer_done
                mov     ax, 0003h               ; the text screen again
                int     10h
                mov     ax, 4C00h
                int     21h

                %ifdef TRANSCRIPT
; What a test reads when the machine has gone: everything printed, a line to
; a line, in TRANSCR.TXT; the screen as it was at the end in SCREEN.BIN; and
; the screen as it was every time a line was asked for, in S00.BIN, S01.BIN
; and so on.
transcript_init:
                mov     ah, 3Ch
                xor     cx, cx
                mov     dx, transcript_name
                int     21h
                mov     [transcript_file], ax
                mov     ah, 3Ch
                xor     cx, cx
                mov     dx, palette_name
                int     21h
                mov     [palette_file], ax
                ret

; Every palette put up, two bytes each: the colour select and the mode, in
; PALETTE.BIN.  The ports cannot be read back, so this is how a test knows.
; Corrupts: AX, DX
transcript_palette:
                cmp     word [palette_file], 0
                je      .none                   ; not open yet
                push    bx
                push    cx
                mov     ah, 40h
                mov     bx, [palette_file]
                mov     cx, 2
                mov     dx, shown_select        ; which the mode follows
                int     21h
                mov     ah, 68h
                int     21h
                pop     cx
                pop     bx
.none:
                ret

; One character of the transcript, AL.
; Corrupts: nothing
transcript_put:
                push    ax
                push    bx
                push    cx
                push    dx
                mov     [transcript_char], al
                mov     ah, 40h
                mov     bx, [transcript_file]
                mov     cx, 1
                mov     dx, transcript_char
                int     21h
                mov     ah, 68h                 ; and on the disk now, so that
                int     21h                     ; a machine that hangs says where
                pop     dx
                pop     cx
                pop     bx
                pop     ax
                ret

transcript_done:
                mov     ah, 3Eh
                mov     bx, [transcript_file]
                int     21h
                mov     ah, 3Eh
                mov     bx, [palette_file]
                int     21h
                mov     word [palette_file], 0
                mov     dx, screen_name
                jmp     transcript_card

; The screen as it is, into the next of S00.BIN and on.
; Corrupts: everything but DS
transcript_screen:
                mov     al, [screens_taken]
                inc     byte [screens_taken]
                mov     ah, al
                mov     cl, 4
                shr     ah, cl
                and     al, 0Fh
                mov     bx, hex_digits
                xlat
                mov     [asked_name + 2], al
                mov     al, ah
                xlat
                mov     [asked_name + 1], al
                mov     dx, asked_name
                ; fall through

; The card's memory into the file named at DS:DX.
transcript_card:
                mov     ah, 3Ch
                xor     cx, cx
                int     21h
                mov     bx, ax
                push    ds
                mov     ax, CGA_SEGMENT
                mov     ds, ax
                mov     ah, 40h
                mov     cx, 4000h
                xor     dx, dx
                int     21h
                pop     ds
                mov     ah, 3Eh
                int     21h
                ret

section .data
transcript_name: db     "TRANSCR.TXT", 0
screen_name:    db      "SCREEN.BIN", 0
asked_name:     db      "S00.BIN", 0
hex_digits:     db      "0123456789ABCDEF"
screens_taken:  db      0
transcript_file: dw     0
palette_file:   dw      0
palette_name:   db      "PALETTE.BIN", 0
transcript_char: db     0
section .text
                %endif

%include "database.asm"
%include "config.asm"
%include "unpack.asm"
%include "textout.asm"
%include "screen.asm"
%include "timer.asm"
%include "keyboard.asm"
%include "sound.asm"
%include "conditions.asm"
%include "opcodes.asm"
%include "save.asm"
%include "parser.asm"
%include "loop.asm"
%include "picture.asm"
%include "cga.asm"
%include "line.asm"
%include "shapes.asm"
; The rules of the GAC the adventure was written with: one or the other.
%ifdef AMSTRAD_PICTURES
%include "amstrad.asm"
%include "amstrad_fill.asm"
%else
%include "draw.asm"
%include "fill.asm"
%endif

; Where the data and the database start, in paragraphs from the code.
section .text
code_end:
section .data
data_end:
section .text
DATA_PARAGRAPH  equ (code_end - start + 15) >> 4
DATABASE_PARAGRAPH equ DATA_PARAGRAPH + ((data_end - data_start + 15) >> 4)
