; MIT License, Copyright (c) 2025 Cronomantic
;
; Finding things in the binary database, on a PC.  See doc/binario.md, and
; z80/common/database.asm, which this follows.
;
;   Header
;     0  magic "RGAC"
;     4  version
;     5  machine
;     6  page bits
;     7  reserved
;     8  reserved
;    10  number of banks
;    11  number of sections
;    12  directory, five bytes a section: bank, offset, size
;
; The whole of the database is in memory, because it is inside the .EXE and
; DOS loads all of it: a PC has the room.  What it has not got is a pointer
; that reaches past sixty four kilobytes, so the database is built in banks of
; that size -- the text and the pictures in them, the rest resident, the way
; the 128, the 6128 and the Next lay theirs out -- and every section gets a
; segment of its own, worked out once here.  Reading a section is loading ES
; with it; there is nothing to page.
;
; A section is reached at ES:SI with SI under sixteen, so none may be longer
; than 65520 bytes, which regac build makes sure of.

SECTION_CONFIG      equ 0
SECTION_VOCAB       equ 1
SECTION_OBJECTS     equ 2
SECTION_LOCATIONS   equ 3
SECTION_CONDITIONS  equ 4
SECTION_TEXT        equ 5
SECTION_FONT        equ 6
SECTION_GRAPHICS    equ 7
MOST_SECTIONS       equ 16

NO_MESSAGE          equ 0FFh    ; no message carries that number
NOT_BANKED          equ 0FFh    ; the bank of a section that is resident

HEADER_PAGE_BITS     equ 6
HEADER_SECTION_COUNT equ 11
HEADER_DIRECTORY     equ 12

; Where every section is: its segment, the offset in it, and its size.  The
; database itself starts at db_seg:0.
; Corrupts: AX, BX, CX, DX, SI, DI, BP, ES
db_init:
                mov     es, [db_seg]
                mov     al, [es:HEADER_SECTION_COUNT]
                xor     ah, ah
                mov     [db_sections], ax
                mov     cx, ax
                mov     bx, ax
                shl     bx, 1
                shl     bx, 1
                add     bx, ax                  ; five bytes a section
                add     bx, HEADER_DIRECTORY
                mov     [db_header], bx
                ; the resident block is the header and every resident section
                ; laid end to end, and the banks come after it
                mov     [db_resident], bx
                mov     si, HEADER_DIRECTORY
.add_resident:
                cmp     byte [es:si], NOT_BANKED
                jne     .banked
                mov     ax, [es:si + 3]
                add     [db_resident], ax
.banked:
                add     si, 5
                loop    .add_resident
                ; and now each one's place
                xor     di, di                  ; which section, twice over
                mov     si, HEADER_DIRECTORY
.each:
                cmp     di, [db_sections]
                je      .done
                cmp     di, MOST_SECTIONS
                je      .done
                ; the linear distance from the start of the database, in DX:AX
                mov     al, [es:si]
                cmp     al, NOT_BANKED
                jne     .in_a_bank
                mov     ax, [db_header]
                xor     dx, dx
                jmp     .plus_offset
.in_a_bank:
                ; the bank's number times its size, which is 1 << page bits
                xor     ah, ah
                xor     dx, dx
                mov     cl, [es:HEADER_PAGE_BITS]
.times_page:
                test    cl, cl
                jz      .past_resident
                shl     ax, 1
                rcl     dx, 1
                dec     cl
                jmp     .times_page
.past_resident:
                add     ax, [db_resident]
                adc     dx, 0
.plus_offset:
                add     ax, [es:si + 1]
                adc     dx, 0
                ; and from there to a segment and an offset under sixteen
                mov     bp, ax
                and     bp, 0Fh
                mov     cl, 4
                shr     ax, cl
                mov     cl, 12
                shl     dx, cl
                or      ax, dx                  ; paragraphs, under a megabyte
                add     ax, [db_seg]
                mov     bx, di
                shl     bx, 1
                mov     [section_seg + bx], ax
                mov     [section_off + bx], bp
                mov     ax, [es:si + 3]
                mov     [section_size + bx], ax
                add     si, 5
                inc     di
                jmp     .each
.done:
                ret

; Where section AL is: ES:SI, and its size in CX.
; Corrupts: BX
db_section:
                mov     bl, al
                xor     bh, bh
                shl     bx, 1
                mov     es, [section_seg + bx]
                mov     si, [section_off + bx]
                mov     cx, [section_size + bx]
                ret

; Just the segment of section AL, in ES.
; Corrupts: BX
db_segment:
                mov     bl, al
                xor     bh, bh
                shl     bx, 1
                mov     es, [section_seg + bx]
                ret

; How many bytes each picture carries in front of its orders: the last byte of
; the configuration.
; Corrupts: AX, BX, CX, SI, ES
db_picture_head:
                mov     al, SECTION_CONFIG
                call    db_section
                add     si, cx
                mov     al, [es:si - 1]
                mov     [picture_head], al
                ret

section .data
picture_head:   db      0
db_seg:         dw      0
db_header:      dw      0
db_resident:    dw      0
db_sections:    dw      0
section_seg:    times MOST_SECTIONS dw 0
section_off:    times MOST_SECTIONS dw 0
section_size:   times MOST_SECTIONS dw 0
section .text
