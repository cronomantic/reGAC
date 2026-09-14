; MIT License, Copyright (c) 2025 Cronomantic
;
; The sector a PCW starts itself from.
;
; That machine has no ROM.  At the switch it pulls a loader out of the keyboard
; controller, reads cylinder 0, head 0, record 1 into $F000, adds the 512 bytes
; up and, if they come to $FF, jumps to $F010 with the four banks mapped 0 to
; 3.  The first sixteen bytes are the disc's own specification, which is why
; the code starts where it does; the builder writes those and bends the last
; byte of the sector to make the sum come out.
;
; From there nothing is given to us: there is no firmware to ask for a sector,
; so this talks to the disc controller itself.  It is the same PD765 the
; Amstrad and the +3 have, at ports nought and one, and reading a sector is
; nine bytes of command, the data, and seven bytes of answer.
;
; What to read and where to put it is a table the builder writes into the end
; of this same sector: which track and record the pieces start at, where to
; jump when they are all in, and then, for each piece, where it goes, how many
; sectors it is, and which of the machine's banks to put in the window first.
; The pieces lie one after another on the disc, so reading is simply going on
; to the next record and, when a track runs out, to the next track.  A piece
; that goes nowhere ends the table.
;
; The last four bytes of the table are not read here at all: they are where
; the saved game lives, and they are for the interpreter, which finds this
; sector still sitting at $F000 because nothing is ever loaded over it.

                DEVICE  NOSLOT64K

FDC_STATUS      equ $00                 ; what the controller is ready for
FDC_DATA        equ $01
SYSTEM          equ $F8                 ; among other things, the motor
MOTOR_ON        equ 9
MOTOR_OFF       equ 10

BANK_AT_4000    equ $F1                 ; which of the eight is seen at $4000
LOCK            equ $F4                 ; and whether that can be changed
UNLOCKED        equ 0
BANK_MARK       equ $80                 ; a bank number is given with this on
NO_BANK         equ $FF                 ; and this means leave the map alone

READ_DATA       equ $46                 ; read, double density
RECALIBRATE     equ $07                 ; wind the head back to track nought
SEEK            equ $0F
SENSE_INTERRUPT equ $08
SEEK_END        equ %00100000
SECTOR_CODE     equ 2                   ; which is five hundred and twelve
SECTORS         equ 9                   ; of them to a track
GAP             equ $2A
DTL             equ $FF

; The screen, laid out exactly as screen.asm lays it out again later: thirty
; two rows of eight lines, the top sixteen for the picture and the bottom
; sixteen for the text, each half in a bank of its own.  It is set up here and
; not left to the interpreter so that a loading screen can be seen while the
; rest of the disk comes in; if one of the two layouts changes, so must the
; other.
ROLLER_AT       equ $FC00               ; in bank three, clear of the keyboard
ROLLER_PORT     equ $F5
ROLLER_VALUE    equ (3 << 5) | ((ROLLER_AT & $3FFF) / 512)
ROLLER_STEP     equ 360                 ; from one row's entry to the next
SCROLL_PORT     equ $F6
DISPLAY_PORT    equ $F7
DISPLAY_ON      equ %01000000
PICTURE_BANK    equ 2
TEXT_BANK       equ 4
SCREEN_ROWS     equ 16
SCREEN_BYTES    equ SCREEN_ROWS * 720

BOOT_CODE_AT    equ $F010
TABLE_AT        equ $F1C0               ; the last sixty four bytes of the
                                        ; sector, which the builder fills in

                ORG     BOOT_CODE_AT
boot:
                di
                ld      sp, $F000
                ld      a, UNLOCKED     ; the banks are ours to move
                out     (LOCK), a
                ld      a, MOTOR_ON
                out     (SYSTEM), a
                ld      de, 0
.settle:                                ; a moment for the disc to come up
                dec     de
                ld      a, d
                or      e
                jr      nz, .settle

                ld      a, RECALIBRATE
                call    send
                xor     a
                call    send            ; drive nought
                call    settled

                call    the_screen      ; so that a loading screen is seen
                                        ; coming in, and not after it has
                ld      ix, TABLE_AT
                ld      b, (ix+0)       ; the track the pieces start on
                ld      c, (ix+1)       ; and the record
                ld      a, b
                or      a
                call    nz, seek        ; which may not be where the head is
                ld      de, 4           ; past the track and the entry point
                add     ix, de
.each_piece:
                ld      l, (ix+0)
                ld      h, (ix+1)       ; where this piece goes
                ld      a, h
                or      l
                jr      z, .run
                ld      a, (ix+3)       ; and in which bank, if any
                cp      NO_BANK
                jr      z, .mapped
                or      BANK_MARK
                out     (BANK_AT_4000), a
.mapped:
                ld      e, (ix+2)       ; how many sectors of it
.each_sector:
                call    read_sector
                dec     e
                jr      nz, .each_sector
                ld      de, 4
                add     ix, de
                jr      .each_piece
.run:
                ld      a, MOTOR_OFF
                out     (SYSTEM), a
                ld      hl, (TABLE_AT + 2)      ; where the builder says to go
                jp      (hl)

; Give the video a table of its own, wipe what both halves of the screen had
; in them, and turn it on.
; Corrupts: AF, BC, DE, HL
the_screen:
                ld      hl, ROLLER_AT
                ld      de, PICTURE_BANK << 13
                call    .a_half
                ld      de, TEXT_BANK << 13
                call    .a_half
                ld      a, PICTURE_BANK
                call    .wipe
                ld      a, TEXT_BANK
                call    .wipe
                ld      a, ROLLER_VALUE
                out     (ROLLER_PORT), a
                xor     a
                out     (SCROLL_PORT), a
                ld      a, DISPLAY_ON
                out     (DISPLAY_PORT), a
                ret

.a_half:
                ld      c, SCREEN_ROWS
.each_row:
                ld      b, 8            ; the eight lines of the row
.each_line:
                ld      (hl), e
                inc     hl
                ld      (hl), d
                inc     hl
                inc     de
                djnz    .each_line
                ld      a, e            ; and on to the next row, which is
                add     a, (ROLLER_STEP - 8) & $FF      ; eight entries beyond
                ld      e, a            ; where we stand
                ld      a, d
                adc     a, (ROLLER_STEP - 8) >> 8
                ld      d, a
                dec     c
                jr      nz, .each_row
                ret

.wipe:
                or      BANK_MARK
                out     (BANK_AT_4000), a
                ld      hl, $4000
                ld      de, $4001
                ld      bc, SCREEN_BYTES - 1
                ld      (hl), 0
                ldir
                ret

; One sector into HL, from track B and record C, moving both on afterwards.
; Corrupts: AF
read_sector:
                push    de
                ld      a, READ_DATA
                call    send
                xor     a
                call    send            ; drive nought, head nought
                ld      a, b
                call    send            ; the cylinder
                xor     a
                call    send            ; the head again
                ld      a, c
                call    send            ; the record
                ld      a, SECTOR_CODE
                call    send
                ld      a, c
                call    send            ; and the last one to read, this one
                ld      a, GAP
                call    send
                ld      a, DTL
                call    send
.data:
                in      a, (FDC_STATUS)
                bit     7, a            ; has it something to say?
                jr      z, .data
                bit     5, a            ; and is it still the data?
                jr      z, .answer
                in      a, (FDC_DATA)
                ld      (hl), a
                inc     hl
                jr      .data
.answer:
                push    bc
                ld      b, 7            ; seven bytes of how it went, unread
.each_answer:
                call    take
                djnz    .each_answer
                pop     bc
                ; and on to the next record, or the next track
                inc     c
                ld      a, c
                cp      SECTORS + 1
                jr      c, .done
                ld      c, 1
                inc     b
                call    seek
.done:
                pop     de
                ret

; Put the head on track B.
; Corrupts: AF
seek:
                ld      a, SEEK
                call    send
                xor     a
                call    send            ; drive nought, head nought
                ld      a, b
                call    send
                ; fall through, and wait for it

; Wait for the head to stop moving, which is asking until it says so.
; Corrupts: AF
settled:
                push    bc
.again:
                ld      a, SENSE_INTERRUPT
                call    send
                call    take            ; the first byte says whether it ended
                and     SEEK_END
                ld      c, a
                call    take            ; and the second is the track
                ld      a, c
                or      a
                jr      z, .again
                pop     bc
                ret

; Give the controller the byte in A.
; Corrupts: AF
send:
                push    af
.wait:
                in      a, (FDC_STATUS)
                add     a, a            ; ready goes to carry, direction to sign
                jr      nc, .wait
                jp      m, .wait        ; it wants to talk, not listen
                pop     af
                out     (FDC_DATA), a
                ret

; And take one from it.
; Corrupts: AF
take:
.wait:
                in      a, (FDC_STATUS)
                add     a, a
                jr      nc, .wait
                jp      p, .wait        ; it is listening, not talking
                in      a, (FDC_DATA)
                ret

last:
                SAVEBIN "boot.bin", boot, last - boot
