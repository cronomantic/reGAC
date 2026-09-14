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
; A section is either resident, meaning always reachable, or it lives in a
; bank, and then the bank has to be brought in before the section can be read.
; How to bring it in is the machine's business: it gives db_page and says at
; what address a bank appears, and a machine with no banks gives the pair that
; does nothing, which is at the end of this file.

SECTION_CONFIG      equ 0
SECTION_VOCAB       equ 1
SECTION_OBJECTS     equ 2
SECTION_LOCATIONS   equ 3
SECTION_CONDITIONS  equ 4
SECTION_TEXT        equ 5
SECTION_FONT        equ 6
SECTION_GRAPHICS    equ 7
SECTION_MUSIC       equ 8

NO_MESSAGE          equ $FF   ; no message carries that number
NOT_BANKED          equ $FF   ; the bank of a section that is resident

; Inside the config section
CONFIG_DIGITS       equ 3     ; the codes of "0" to "9"
CONFIG_ASCII        equ 13    ; ASCII 32 to 127 -> this adventure's codes
CONFIG_PUNCTUATION  equ 109   ; how many, then the codes; the space comes first

NO_CHARACTER        equ $FF   ; the adventure has no such character

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

; Address of section A in HL, its size in BC.  A section that lives in a bank
; is brought in first, so what comes back is good until another section is
; asked for.
; Corrupts: AF, DE
db_section:
                push    af
                call    db_entry
                ld      a, (hl)                 ; which bank it lives in
                inc     hl
                ld      e, (hl)
                inc     hl
                ld      d, (hl)                 ; offset within its block
                inc     hl
                ld      c, (hl)
                inc     hl
                ld      b, (hl)                 ; size
                cp      NOT_BANKED
                jr      z, .resident
                call    db_page                 ; the machine brings it in
                ld      hl, DB_WINDOW
                add     hl, de
                pop     af
                ret
.resident:
                ld      hl, (db_resident)
                add     hl, de
                pop     af
                ret

; The five bytes the directory keeps for section A, in HL.
; Corrupts: DE, HL
db_entry:
                ld      l, a
                ld      h, 0
                ld      d, h
                ld      e, l
                add     hl, hl                  ; x2
                add     hl, hl                  ; x4
                add     hl, de                  ; x5
                ld      de, database + HEADER_DIRECTORY
                add     hl, de
                ret

; Bring section A's bank in again, for the code that kept a pointer into it
; from an earlier look: the text and the pictures both do that, and printing
; something is what takes the pictures' bank away.
; Corrupts: AF
db_bank_in:
                push    hl
                push    de
                call    db_entry
                ld      a, (hl)
                cp      NOT_BANKED
                call    nz, db_page
                pop     de
                pop     hl
                ret

db_resident:    dw      0
db_sections:    db      0

; A machine with no banks says so by not defining BANKED, and gets the pair
; that does nothing: every section is resident and nothing is ever paged.
                IFNDEF BANKED
DB_WINDOW       equ 0
db_page:
                ret
                ENDIF
