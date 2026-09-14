; MIT License, Copyright (c) 2025 Cronomantic
;
; A payload that does nothing at all, so that a test can look at the loading
; screen that came in before it.
;
; The top half of the screen is in the map already; the bottom half is in a
; bank of its own, so a piece of it is fetched here into somewhere a test can
; read, which is cheaper than paging from the outside.

                DEVICE  NOSLOT64K

LOCK            equ $F4
UNLOCKED        equ 0
BANK_MARK       equ $80
WINDOW          equ $4000
WINDOW_PORT     equ $F1
TEXT_BANK       equ 4
HALF            equ 16 * 720
SAMPLE          equ 512                 ; of each end of it
KEPT            equ $D000

                ORG     $0100
start:
                di
                ld      sp, $FC00
                ld      a, UNLOCKED
                out     (LOCK), a
                ld      a, TEXT_BANK | BANK_MARK
                out     (WINDOW_PORT), a
                ld      hl, WINDOW
                ld      de, KEPT
                ld      bc, SAMPLE
                ldir
                ld      hl, WINDOW + HALF - SAMPLE
                ld      de, KEPT + SAMPLE
                ld      bc, SAMPLE
                ldir
                ld      a, $FF
                ld      (done_flag), a
.stop:
                jr      .stop

done_flag:      db      0
last:

                SAVEBIN "screen.bin", start, last - start
