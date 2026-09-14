; MIT License, Copyright (c) 2025 Cronomantic
;
; Saving and loading a game on an MSX, which means borrowing the BIOS back.
;
; The interpreter runs with RAM in all four pages, so the BIOS is not there any
; more -- and the BIOS is the only thing on this machine that knows how to talk
; to a cassette.  So for as long as a save takes, the two low pages go back to
; the slot they came from, the routines are called, and the machine is taken
; again.  What travels is the game alone, which lives up here with the code and
; is not touched by any of that.
;
; The five entries are the ones every MSX has at the same addresses:
;
;       $00E1 TAPION   find the lead and get in step, to read
;       $00E4 TAPIN    one byte in
;       $00E7 TAPIOF   and stop
;       $00EA TAPOON   write a lead, A saying long or short
;       $00ED TAPOUT   one byte out
;       $00F0 TAPOOF   and stop

TAPION          equ $00E1
TAPIN           equ $00E4
TAPIOF          equ $00E7
TAPOON          equ $00EA
TAPOUT          equ $00ED
TAPOOF          equ $00F0

LEAD_LONG       equ 1                   ; the lead that goes before a file

; Those routines come back with the interrupts on, and an interrupt with the
; machine ours is a jump to $0038, which is the database by then.  So the
; machine is never taken back without this.
TAPE_ERROR      equ 2                   ; the border, when the tape gives out

; Where the database comes in and how much of it at a time: the copy of the
; screen, which the interpreter has not started using while this is loading.
DB_BUFFER       equ SHADOW
DB_CHUNK        equ 8192

; Read the database off the cassette and put it where the BIOS was.
;
; It cannot be read straight there.  The BIOS is the only thing on this machine
; that can read a cassette and it sits over the first two pages, which is
; exactly where the database goes; so each chunk comes into the buffer up here
; with the BIOS in, and the machine is taken back for as long as the copy
; takes.  The motor stops each time that happens, which is why every chunk is
; a block of its own on the tape.
;
; The first block starts with three bytes that say what is coming -- the size
; of the whole database, and whether a loading screen comes in front of it --
; so there is nothing about one adventure built into this.
; Corrupts: everything
load_database:
                ld      hl, database
                ld      (db_where), hl
                call    the_bios_back
                call    start_reading
                jr      c, tape_gave_out
                call    read_byte               ; the size, low byte first
                jr      c, tape_gave_out
                ld      l, a
                push    hl
                call    read_byte
                pop     hl
                jr      c, tape_gave_out
                ld      h, a
                ld      (db_left), hl
                call    read_byte               ; and whether a screen comes
                jr      c, tape_gave_out
                or      a
                jr      z, .chunk
                call    screen_from_tape
                jr      c, tape_gave_out
.chunk:
                ; the whole of a chunk, or what is left if that is less
                ld      hl, (db_left)
                ld      de, DB_CHUNK
                or      a
                sbc     hl, de
                jr      nc, .full
                ld      de, (db_left)
.full:
                ld      (db_count), de
                ld      ix, DB_BUFFER
.each:
                call    read_byte
                jr      c, tape_gave_out
                ld      (ix+0), a
                inc     ix
                dec     de
                ld      a, d
                or      e
                jr      nz, .each
                call    stop_reading
                call    the_machine_back
                ; and now that the first two pages are ours, into place
                ld      hl, DB_BUFFER
                ld      de, (db_where)
                ld      bc, (db_count)
                ldir
                ld      (db_where), de
                ld      hl, (db_left)
                ld      bc, (db_count)
                or      a
                sbc     hl, bc
                ld      (db_left), hl
                ld      a, h
                or      l
                ret     z                       ; that was the last of it
                call    the_bios_back
                call    start_reading
                jr      nc, .chunk

; Nothing to be done and nothing to say it with: there is no screen yet and no
; way back along a tape.  The border says it, as it always did.
tape_gave_out:
                call    stop_reading
                call    the_machine_back
                ld      a, TAPE_ERROR
                call    set_border
.stop:
                jr      .stop

db_where:       dw      0                       ; where the next chunk goes
db_left:        dw      0                       ; and how much there is to come
db_count:       dw      0

; The loading screen, straight from the cassette into the video chip, which
; wants no room in memory at all: the chip counts its own address up, so every
; byte goes out as it comes in and the picture fills in while the tape runs.
; It is in the same block as the first chunk of the database, so the motor
; does not stop between the two.
; Carry set when the tape gave out.
; Corrupts: everything
screen_from_tape:
                call    vdp_setup
                ld      hl, VRAM_PATTERNS
                call    vram_write
                ld      de, VRAM_SHOWN
.each:
                call    read_byte
                ret     c
                out     (VDP_DATA), a
                dec     de
                ld      a, d
                or      e
                jr      nz, .each
                ret                             ; the `or` left no carry: it came

; Find the lead and get in step.  Carry set when nothing came.
; Corrupts: AF
start_reading:
                push    bc
                push    de
                push    hl
                push    ix
                call    TAPION
                jr      tape_done
; Stop the motor.  The interrupts come back on with it, and they are not
; wanted: the routine that answers them is about to be paged out.
; Corrupts: AF
stop_reading:
                push    bc
                push    de
                push    hl
                push    ix
                call    TAPIOF
                jr      tape_done
; One byte off the cassette, into A.  Carry set when it did not come.
; Corrupts: AF
read_byte:
                push    bc
                push    de
                push    hl
                push    ix
                call    TAPIN
tape_done:
                pop     ix
                pop     hl
                pop     de
                pop     bc
                di
                ret

; Put the block at IX, DE bytes of it, on the cassette.  Carry set when it
; went.
; Corrupts: everything
tape_save:
                call    the_bios_back
                push    ix
                push    de
                ld      a, LEAD_LONG
                call    TAPOON
                pop     de
                pop     ix
                jr      c, .gave_up
.each:
                ld      a, (ix+0)
                push    ix
                push    de
                call    TAPOUT
                pop     de
                pop     ix
                jr      c, .gave_up
                inc     ix
                dec     de
                ld      a, d
                or      e
                jr      nz, .each
                call    TAPOOF
                call    the_machine_back
                scf
                ret
.gave_up:
                call    TAPOOF
                call    the_machine_back
                or      a
                ret

; Read the block back into IX, DE bytes of it.  Carry set when it came.
; Corrupts: everything
tape_load:
                call    the_bios_back
                push    ix
                push    de
                call    TAPION
                pop     de
                pop     ix
                jr      c, .gave_up
.each:
                push    ix
                push    de
                call    TAPIN
                pop     de
                pop     ix
                jr      c, .gave_up
                ld      (ix+0), a
                inc     ix
                dec     de
                ld      a, d
                or      e
                jr      nz, .each
                call    TAPIOF
                call    the_machine_back
                scf
                ret
.gave_up:
                call    TAPIOF
                call    the_machine_back
                or      a
                ret

; The two low pages back to the slot the BIOS is in, and then ours again.
; Which slot that is was noted when the machine was taken.
; Corrupts: AF
the_bios_back:
                ld      a, (bios_slots)
                out     (PPI_SLOTS), a
                ret

the_machine_back:
                di                              ; before the BIOS goes away
                ld      a, (our_slots)
                out     (PPI_SLOTS), a
                ret
