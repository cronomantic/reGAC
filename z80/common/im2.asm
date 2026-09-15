; MIT License, Copyright (c) 2025 Cronomantic
;
; Mode two interrupts, which is how three of these machines get their music
; played, and the same three lines of reasoning on each of them.
;
; It is mode two and not mode one because mode one goes to $0038, and what is
; at $0038 is either the machine's own handler -- which scans a keyboard,
; counts frames and wants system variables we have long since written over --
; or, on a machine that takes the whole of its memory, the database.  Mode two
; goes where we say.
;
; Where we say has to be memory that is always there, whatever is paged in, so
; each machine picks an address in the part of its map that never moves and
; says so before including this.  The table is 257 bytes of the same byte: the
; extra one because the byte the machine puts on the bus is not to be relied
; upon, so the vector may be the last entry and its address read across the
; end.  The filler is chosen so that a pair of it is an address with room for
; the routine.
;
; Neither the table nor the routine is in the file that is loaded.  They sit
; in a corner of the map that the interpreter and its data stop short of, and
; a build that carried them there would have to carry everything in between as
; well -- kilobytes of nothing, which on a cassette is a minute of nothing.
; So the routine is assembled where it will run but kept where the code is,
; and put in place, along with the table, when the interrupts are turned on.
;
; What each machine says:
;
;   IM2_TABLE       where the 257 bytes go, on a page boundary
;   IM2_FILLER      the byte they are, whose pair is where the routine goes
;   INTERRUPT_ACK   a macro: whatever this machine wants doing to be told the
;                   interrupt has been seen, or nothing at all

IM2_HANDLER     equ IM2_FILLER * 257
                ; either the routine ends before its own table or starts after
                ASSERT  IM2_HANDLER + im2_handler_bytes <= IM2_TABLE || IM2_HANDLER >= IM2_TABLE + 257

; Lay the table out, put the routine where it points, and let the interrupts
; in.  It is called im2_init and not interrupt_init because a machine may have
; something of its own to do first: each says which name the interpreter is to
; call.
; Corrupts: AF, BC, DE, HL
im2_init:
                di
                ld      hl, IM2_TABLE
                ld      de, IM2_TABLE + 1
                ld      (hl), IM2_FILLER
                ld      bc, 256
                ldir
                ld      hl, im2_handler_image
                ld      de, IM2_HANDLER
                ld      bc, im2_handler_bytes
                ldir
                ld      a, IM2_TABLE >> 8
                ld      i, a
                im      2
                ei
                ret

; And the routine itself, written for the address that table points at and
; kept here until it is wanted there.
im2_handler_image:
                DISP    IM2_HANDLER
                include "ticker.asm"
                ENT
im2_handler_bytes equ $ - im2_handler_image
