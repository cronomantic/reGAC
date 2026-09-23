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
; The database has a segment of its own, db_seg, and what is in it is reached
; through ES.  Everything is resident for now: a database over sixty four
; kilobytes will be banks of that size, one segment each, and bringing one in
; will be loading ES -- see doc/pendiente.md -- but none of the adventures to
; hand is half that.

SECTION_CONFIG      equ 0
SECTION_VOCAB       equ 1
SECTION_OBJECTS     equ 2
SECTION_LOCATIONS   equ 3
SECTION_CONDITIONS  equ 4
SECTION_TEXT        equ 5
SECTION_FONT        equ 6
SECTION_GRAPHICS    equ 7

NOT_BANKED          equ 0FFh

HEADER_SECTION_COUNT equ 11
HEADER_DIRECTORY     equ 12

; Work out where the resident sections start and keep it.
; Corrupts: AX, BX, ES
db_init:
                mov     es, [db_seg]
                mov     al, [es:HEADER_SECTION_COUNT]
                mov     [db_sections], al
                xor     ah, ah
                mov     bx, ax
                shl     ax, 1
                shl     ax, 1
                add     ax, bx                  ; five bytes a section
                add     ax, HEADER_DIRECTORY
                mov     [db_resident], ax
                ret

; Where section AL is, in SI, and its size in CX, with ES the database's.
; Corrupts: AX, BX, ES
db_section:
                mov     es, [db_seg]
                xor     ah, ah
                mov     bx, ax
                shl     bx, 1
                shl     bx, 1
                add     bx, ax
                add     bx, HEADER_DIRECTORY
                mov     si, [es:bx + 1]         ; its offset within the block
                mov     cx, [es:bx + 3]         ; and its size
                add     si, [db_resident]
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

db_seg:         dw      0
db_resident:    dw      0
db_sections:    db      0
picture_head:   db      0
