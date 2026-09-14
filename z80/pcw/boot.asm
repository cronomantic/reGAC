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
; of this same sector: which track and record the pieces start at, and then,
; for each piece, where it goes, how many sectors it is, and which of the
; machine's banks to put in the window first.  The pieces lie one after
; another on the disc, so reading is simply going on to the next record and,
; when a track runs out, to the next track.  A piece that goes nowhere ends
; the table, and then the first piece is jumped into.

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

                ld      ix, TABLE_AT
                ld      b, (ix+0)       ; the track the pieces start on
                ld      c, (ix+1)       ; and the record
                ld      a, b
                or      a
                call    nz, seek        ; which may not be where the head is
                ld      de, 2
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
                ld      hl, (TABLE_AT + 2)      ; the first piece is the one to run
                jp      (hl)

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
