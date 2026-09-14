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
; What it does is read the pieces that follow this sector and jump into them.

                DEVICE  NOSLOT64K

FDC_STATUS      equ $00                 ; what the controller is ready for
FDC_DATA        equ $01
SYSTEM          equ $F8                 ; among other things, the motor
MOTOR_ON        equ 9
MOTOR_OFF       equ 10

READ_DATA       equ $46                 ; read, double density
RECALIBRATE     equ $07                 ; wind the head back to track nought
SENSE_INTERRUPT equ $08
SECTOR_CODE     equ 2                   ; which is five hundred and twelve
GAP             equ $2A
DTL             equ $FF

BOOT_CODE_AT    equ $F010
PAYLOAD_AT      equ $0100               ; where what follows is put
FIRST_SECTOR    equ 2                   ; this one being the first of the track
SECTORS         equ 8                   ; and the rest of the track after it

                ORG     BOOT_CODE_AT
boot:
                di
                ld      sp, $F000
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

                ld      hl, PAYLOAD_AT
                ld      d, 0            ; the track
                ld      c, FIRST_SECTOR
.each:
                call    read_sector
                inc     c
                ld      a, c
                cp      FIRST_SECTOR + SECTORS
                jr      nz, .each

                ld      a, MOTOR_OFF
                out     (SYSTEM), a
                jp      PAYLOAD_AT

; One sector, track D and record C, into HL, which is left after it.
; Corrupts: AF, B
read_sector:
                ld      a, READ_DATA
                call    send
                xor     a
                call    send            ; drive nought, head nought
                ld      a, d
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
                ld      b, 7            ; seven bytes of how it went, unread
.each_answer:
                call    take
                djnz    .each_answer
                ret

; Wait for the head to stop moving, which is asking until it says so.
; Corrupts: AF, B
settled:
                ld      a, SENSE_INTERRUPT
                call    send
                call    take            ; the first byte says whether it ended
                and     %00100000       ; seek end
                jr      z, settled
                call    take            ; and the second is the track
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
