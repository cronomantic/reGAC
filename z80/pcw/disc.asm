; MIT License, Copyright (c) 2025 Cronomantic
;
; Saving and loading a game on a PCW, which has neither tape nor firmware.
;
; What it has is a file the builder made: an ordinary CP/M file, of the right
; size and empty, whose first track and record the builder left in the last
; four bytes of the boot sector.  That sector is still where it landed, at
; $F000, and nothing is ever loaded over it, so the runtime only has to read
; those three numbers and write the sectors.
;
; The directory is never touched, and it does not have to be: the file already
; exists, its blocks are already allocated and its size is already right.  The
; filesystem is there for the person, who can copy the saved game about with
; CP/M's own tools; the runtime only touches sectors it was told about.
;
; The controller is the same PD765 the boot sector drives, at ports nought and
; one.  Its code is not shared with this: a boot sector has to be whole on its
; own, in 496 bytes, and cannot call anything that is not in it.
;
; A whole number of sectors goes down every time, out of an area of our own,
; so that what is written does not depend on where the game happens to end.

FDC_STATUS      equ $00                 ; what the controller is ready for
FDC_DATA        equ $01
SYSTEM          equ $F8                 ; among other things, the motor
MOTOR_ON        equ 9
MOTOR_OFF       equ 10

READ_DATA       equ $46                 ; read, double density
WRITE_DATA      equ $45
RECALIBRATE     equ $07                 ; wind the head back to track nought
SEEK            equ $0F
SENSE_INTERRUPT equ $08
SEEK_END        equ %00100000
SECTOR_CODE     equ 2                   ; which is five hundred and twelve
SECTORS         equ 9                   ; of them to a track
GAP             equ $2A
DTL             equ $FF

SECTOR_BYTES    equ 512
SAVE_SECTORS    equ 4                   ; what the builder sets aside for it,
                                        ; which is PCW_SAVE_SECTORS in
                                        ; media.py: if one moves, so does the
                                        ; other, and the loop below will not
                                        ; write past the area whatever it is
                                        ; told
SAVE_BYTES      equ SAVE_SECTORS * SECTOR_BYTES
SAVE_WHERE      equ $F1FC               ; track, record and how many sectors
SAVE_AREA       equ $D000               ; and where it is put together, which
                                        ; is out of the way of the code: the
                                        ; first sixteen kilobytes are the one
                                        ; part of this machine that is tight

; Put the block at IX, DE bytes of it, on the disc.  Carry set when it went.
; Corrupts: everything
tape_save:
                call    to_the_area
                ld      a, WRITE_DATA
                jp      transfer

; Read the block back into IX, DE bytes of it.  Carry set when it came.
; Corrupts: everything
tape_load:
                push    ix
                push    de
                ld      a, READ_DATA
                call    transfer
                pop     bc                      ; how much of it there was
                pop     de                      ; and where it goes back to
                ld      hl, SAVE_AREA
                ldir
                scf
                ret

; Copy DE bytes from IX into the area that travels, having wiped it first so
; that the same game always writes the same sectors.
; Corrupts: everything
to_the_area:
                push    de
                push    ix
                ld      hl, SAVE_AREA
                ld      de, SAVE_AREA + 1
                ld      bc, SAVE_BYTES - 1
                ld      (hl), 0
                ldir
                pop     hl                      ; where the game is
                pop     bc                      ; and how much of it
                ld      de, SAVE_AREA
                ldir
                ret

; Move the area to or from the disc, A saying which way.
; Corrupts: everything
transfer:
                ld      (disc_command), a
                ld      a, MOTOR_ON
                out     (SYSTEM), a
                ld      de, 0
.settle:                                        ; a moment for the disc to come up
                dec     de
                ld      a, d
                or      e
                jr      nz, .settle

                ld      a, RECALIBRATE
                call    send
                xor     a
                call    send                    ; drive nought
                call    settled

                ld      a, (SAVE_WHERE)
                ld      b, a                    ; the track the file starts on
                ld      a, (SAVE_WHERE + 1)
                ld      c, a                    ; and the record
                ld      a, b
                or      a
                call    nz, seek
                ld      hl, SAVE_AREA
                ld      a, (SAVE_WHERE + 2)
                ld      e, a                    ; how many sectors it holds
                cp      SAVE_SECTORS + 1
                jr      c, .each_sector
                ld      e, SAVE_SECTORS         ; and no more than we have
.each_sector:
                call    one_sector
                dec     e
                jr      nz, .each_sector

                ld      a, MOTOR_OFF
                out     (SYSTEM), a
                scf
                ret

; One sector between HL and track B, record C, moving both on afterwards.
; Corrupts: AF
one_sector:
                push    de
                ld      a, (disc_command)
                call    send
                xor     a
                call    send                    ; drive nought, head nought
                ld      a, b
                call    send                    ; the cylinder
                xor     a
                call    send                    ; the head again
                ld      a, c
                call    send                    ; the record
                ld      a, SECTOR_CODE
                call    send
                ld      a, c
                call    send                    ; and the last one, this one
                ld      a, GAP
                call    send
                ld      a, DTL
                call    send
                ld      a, (disc_command)
                cp      WRITE_DATA
                jr      z, .writing
.reading:
                in      a, (FDC_STATUS)
                bit     7, a                    ; has it something to say?
                jr      z, .reading
                bit     5, a                    ; and is it still the data?
                jr      z, .answer
                in      a, (FDC_DATA)
                ld      (hl), a
                inc     hl
                jr      .reading
.writing:
                in      a, (FDC_STATUS)
                bit     7, a
                jr      z, .writing
                bit     5, a
                jr      z, .answer
                ld      a, (hl)
                out     (FDC_DATA), a
                inc     hl
                jr      .writing
.answer:
                push    bc
                ld      b, 7                    ; seven bytes of how it went
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
                call    send                    ; drive nought, head nought
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
                call    take                    ; the first byte says whether
                and     SEEK_END                ; it ended
                ld      c, a
                call    take                    ; and the second is the track
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
                add     a, a                    ; ready to carry, direction to sign
                jr      nc, .wait
                jp      m, .wait                ; it wants to talk, not listen
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
                jp      p, .wait                ; it is listening, not talking
                in      a, (FDC_DATA)
                ret

disc_command:   db      0
