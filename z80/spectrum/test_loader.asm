; MIT License, Copyright (c) 2025 Cronomantic
;
; A tape with the loader on it and nothing else worth running: what comes off
; it is a program that stops dead, so that a test can look at what the loader
; left behind without an interpreter clearing the screen half a second later.

                DEVICE  ZXSPECTRUM48

                include "loader.asm"

                IFDEF SCREEN
                ORG     SCREEN_AT
loading_screen:
                INCBIN  "screen.bin", 0, SCREEN_BYTES
                ENDIF

                ORG     $8000
start:
                di
                ld      a, $2A                  ; something to know it by
                ld      ($9000), a
.stop:
                jr      .stop
                ds      64                      ; a block worth loading
last:

                EMPTYTAP "loader.tap"
                SAVETAP "loader.tap", BASIC, "reGAC", basic, basic_end - basic, 10
                IFDEF SCREEN
                SAVETAP "loader.tap", HEADLESS, loading_screen, SCREEN_BYTES
                ENDIF
                SAVETAP "loader.tap", HEADLESS, start, last - start
