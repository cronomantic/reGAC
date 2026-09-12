; MIT License, Copyright (c) 2025 Cronomantic
;
; Finding things in the binary database.  See doc/binario.md.
;
;   Header
;     0  magic "RGAC"
;     4  version
;     5  machine
;     6  page bits
;     7  music mode
;     8  music buffer size
;    10  number of banks
;    11  number of sections
;    12  directory, five bytes a section: bank, offset, size
;
; Only resident sections are handled here.  Paging comes with the machines
; that have banks; the Spectrum 48 has none.

SECTION_CONFIG      equ 0
SECTION_VOCAB       equ 1
SECTION_OBJECTS     equ 2
SECTION_LOCATIONS   equ 3
SECTION_CONDITIONS  equ 4
SECTION_TEXT        equ 5
SECTION_FONT        equ 6
SECTION_GRAPHICS    equ 7
SECTION_MUSIC       equ 8

HEADER_SECTION_COUNT equ 11
HEADER_DIRECTORY     equ 12
DIRECTORY_ENTRY_SIZE equ 5

; Work out where the resident sections start and keep it.
; Corrupts: AF, BC, DE, HL
db_init:
                ld      hl, database + HEADER_SECTION_COUNT
                ld      a, (hl)                 ; how many sections
                ld      (db_sections), a
                ; the resident block follows the directory
                ld      l, a
                ld      h, 0
                ld      b, h
                ld      c, l
                add     hl, hl                  ; x2
                add     hl, hl                  ; x4
                add     hl, bc                  ; x5
                ld      bc, database + HEADER_DIRECTORY
                add     hl, bc
                ld      (db_resident), hl
                ret

; Address of section A in HL, its size in BC.
; Corrupts: AF, DE
db_section:
                push    af
                ld      l, a
                ld      h, 0
                ld      d, h
                ld      e, l
                add     hl, hl                  ; x2
                add     hl, hl                  ; x4
                add     hl, de                  ; x5
                ld      de, database + HEADER_DIRECTORY
                add     hl, de                  ; the entry for this section
                inc     hl                      ; skip the bank byte
                ld      e, (hl)
                inc     hl
                ld      d, (hl)                 ; offset within the block
                inc     hl
                ld      c, (hl)
                inc     hl
                ld      b, (hl)                 ; size
                ld      hl, (db_resident)
                add     hl, de
                pop     af
                ret

db_resident:    dw      0
db_sections:    db      0
