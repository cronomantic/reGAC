; MIT License, Copyright (c) 2025 Cronomantic
;
; What a cassette carries in front of an adventure, and how it is taken off.
;
; The interpreter is loaded by the machine itself, with BLOAD, and everything
; behind it is read here: a loading screen, if there is one, and the database.
; Why it has to be this way round is in doc/binario.md -- the BIOS is the only
; thing that can read a tape and it sits exactly where the database goes, so
; the interpreter is the only thing that can put one there.

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
