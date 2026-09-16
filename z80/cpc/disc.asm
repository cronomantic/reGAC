; MIT License, Copyright (c) 2025 Cronomantic
;
; Saving and loading a game on a 6128, which is the disk and not the tape.
;
; The same thing the PCW does.  The builder makes a file on the disk, of the
; right size and empty, and writes where it starts -- the track, the record,
; and how many sectors -- into the three bytes at save_where, which every
; build that includes this puts at $8002.  The runtime reads those numbers and
; writes the sectors, without ever touching the directory, so what comes out
; is still a file AMSDOS can copy about.
;
; It cannot go through the firmware, which is what a 464 does: an entry of the
; jumpblock is a restart and a restart brings the lower ROM back, and on this
; machine the lower ROM covers the resident half of the database.  That is the
; whole reason this file exists rather than tape.asm being included.
;
; The controller is the PD765 of the PCW, and what changes is three things.
; Its ports are sixteen bits wide -- the status at $FB7E, the data at the one
; after it, the motor at $FA7E -- so every one is spoken to through C.  The
; sectors of a data disk are numbered $C1 to $C9.  And the interrupts go off
; while it works: in the middle of a sector the controller hands over a byte
; every thirty two millionths of a second and does not wait, and the tune's
; three hundred interrupts a second would lose some.
;
; Unlike the PCW's, this one listens to what the controller says when it is
; done.  A disk with its tab over, or a sector that will not read, comes back
; with the carry clear instead of saying it went.

FDC_MOTOR       equ $FA7E               ; bit nought turns it on
FDC_STATUS      equ $FB7E               ; what the controller is ready for, with
                                        ; the data at the port after it

READ_DATA       equ $46                 ; read, double density
WRITE_DATA      equ $45
RECALIBRATE     equ $07                 ; wind the head back to track nought
SEEK            equ $0F
SENSE_INTERRUPT equ $08
SEEK_END        equ %00100000
SECTOR_CODE     equ 2                   ; which is five hundred and twelve
SECTORS         equ 9                   ; of them to a track
FIRST_SECTOR    equ $C1                 ; numbered from here on a data disk
GAP             equ $2A
DTL             equ $FF

; What in the second and third bytes of the controller's answer means it went
; wrong.  An Amstrad has no line to tell the controller a transfer is over, so
; every sector read or written ends with "end of cylinder" set, and that one
; bit is left out; the rest are a bad sector, a missing one, an overrun, a
; disk that will not be written to, a wrong track.
ST1_WRONG       equ %00110111
ST2_WRONG       equ %01110011

SECTOR_BYTES    equ 512
SAVE_SECTORS    equ 4                   ; what the builder sets aside for it,
                                        ; which is CPC6128_SAVE_SECTORS in
                                        ; media.py: if one moves, so does the
                                        ; other, and the loop below will not
                                        ; write past the area whatever it is
                                        ; told
SAVE_BYTES      equ SAVE_SECTORS * SECTOR_BYTES
SAVE_AREA       equ $B000               ; where it is put together, between the
                                        ; end of the interpreter and the stack

; Put the block at IX, DE bytes of it, on the disk.  Carry set when it went.
; Corrupts: everything
tape_save:
                call    to_the_area
                ld      a, WRITE_DATA
                jp      transfer

; Read the block back into IX, DE bytes of it.  Carry set when it came, and
; nothing is touched when it did not: a load that goes wrong leaves the game
; as it was.
; Corrupts: everything
tape_load:
                push    ix
                push    de
                ld      a, READ_DATA
                call    transfer
                pop     bc                      ; how much of it there was
                pop     de                      ; and where it goes back to
                ret     nc
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

; Move the area to or from the disk, A saying which way.  Carry set when all
; of it went.
; Corrupts: everything
transfer:
                ld      (disc_command), a
                ld      a, (save_where + 2)
                or      a                       ; no file was set aside for it,
                ret     z                       ; and the carry is clear
                di
                ld      bc, FDC_MOTOR
                ld      a, 1
                out     (c), a
                ld      b, 3                    ; a second or so for it to spin up
.spin:
                ld      de, 0
.settle:
                dec     de
                ld      a, d
                or      e
                jr      nz, .settle
                djnz    .spin

                ld      a, RECALIBRATE
                call    send
                xor     a
                call    send                    ; drive nought
                call    settled

                ld      a, (save_where)
                ld      (disc_track), a         ; the track the file starts on
                ld      a, (save_where + 1)
                ld      (disc_record), a        ; and the record
                ld      a, (disc_track)
                or      a
                call    nz, seek
                ld      hl, SAVE_AREA
                ld      a, (save_where + 2)
                ld      e, a                    ; how many sectors it holds
                cp      SAVE_SECTORS + 1
                jr      c, .each_sector
                ld      e, SAVE_SECTORS         ; and no more than we have
.each_sector:
                push    de
                call    one_sector
                pop     de
                jr      nz, .failed
                dec     e
                jr      nz, .each_sector
                call    stop_the_motor
                scf
                ret
.failed:
                call    stop_the_motor
                or      a
                ret

; Turn the motor off and let the interrupts back in, if the build has any.
; Corrupts: AF, BC
stop_the_motor:
                ld      bc, FDC_MOTOR
                xor     a
                out     (c), a
                IFDEF WITH_MUSIC
                ei                              ; the tune's, back
                ENDIF
                ret

; One sector between HL and the track and record the disc_ bytes say, moving
; both on afterwards.  Zero flag set when it went.
; Corrupts: AF, BC, DE, and HL moves on by the sector
one_sector:
                xor     a
                ld      (disc_talked), a
                ld      a, (disc_command)
                call    send
                xor     a
                call    send                    ; drive nought, head nought
                ld      a, (disc_track)
                call    send                    ; the cylinder
                xor     a
                call    send                    ; the head again
                ld      a, (disc_record)
                call    send                    ; the record
                ld      a, SECTOR_CODE
                call    send
                ld      a, (disc_record)
                call    send                    ; and the last one, this one
                ld      a, GAP
                call    send
                ld      a, DTL
                call    send
                ld      a, (disc_talked)        ; given up on already, and
                or      a                       ; waiting to say why
                jr      nz, .answer
                ; The bytes themselves.  This is the part that has thirty two
                ; millionths of a second a byte, and it takes about twenty.
                ld      bc, FDC_STATUS
                ld      a, (disc_command)
                cp      WRITE_DATA
                jr      z, .writing
.reading:
                in      a, (c)
                jp      p, .reading             ; nothing for us yet
                and     %00100000               ; and is it still the data?
                jr      z, .answer
                inc     c
                in      a, (c)
                dec     c
                ld      (hl), a
                inc     hl
                jr      .reading
.writing:
                in      a, (c)
                jp      p, .writing
                and     %00100000
                jr      z, .answer
                inc     c
                ld      a, (hl)
                out     (c), a
                dec     c
                inc     hl
                jr      .writing
.answer:
                call    take                    ; how it ended, which on this
                call    take                    ; machine always says abnormally
                and     ST1_WRONG
                ld      d, a
                call    take
                and     ST2_WRONG
                or      d
                ld      d, a                    ; anything wrong at all
                ld      b, 4
.rest:
                call    take                    ; and where it got to
                djnz    .rest
                ld      a, d
                or      a
                ret     nz
                ; on to the next record, or the next track
                ld      a, (disc_record)
                inc     a
                cp      FIRST_SECTOR + SECTORS
                jr      c, .same_track
                ld      a, (disc_track)
                inc     a
                ld      (disc_track), a
                call    seek
                ld      a, FIRST_SECTOR
.same_track:
                ld      (disc_record), a
                xor     a
                ret

; Put the head on the track disc_track says.
; Corrupts: AF
seek:
                ld      a, SEEK
                call    send
                xor     a
                call    send                    ; drive nought, head nought
                ld      a, (disc_track)
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
;
; If it wants to talk instead of listen, it has given up on the command before
; hearing all of it -- the emulator does that with a disk it may not write to,
; where a real controller hears the whole command first -- and is waiting to
; say why.  Then the byte is not sent, and that is written down in disc_talked
; for whoever is sending the command to go and ask; waiting for it to listen
; again would be waiting for ever.
; Corrupts: AF
send:
                push    bc
                push    af
                ld      bc, FDC_STATUS
.wait:
                in      a, (c)
                add     a, a                    ; ready to carry, direction to sign
                jr      nc, .wait
                jp      m, .talking
                pop     af
                inc     c
                out     (c), a
                pop     bc
                ret
.talking:
                ld      a, 1
                ld      (disc_talked), a
                pop     af
                pop     bc
                ret

; And take one from it.
; Corrupts: AF
take:
                push    bc
                ld      bc, FDC_STATUS
.wait:
                in      a, (c)
                add     a, a
                jr      nc, .wait
                jp      p, .wait                ; it is listening, not talking
                inc     c
                in      a, (c)
                pop     bc
                ret

disc_command:   db      0
disc_talked:    db      0               ; it wanted to talk in the middle
disc_track:     db      0
disc_record:    db      0
