; MIT License, Copyright (c) 2025 Cronomantic
;
; Something for the boot sector to load and run, so that a test can see that
; it did: leave a couple of bytes where they can be looked for, and stop.
                DEVICE  NOSLOT64K
                ORG     $0100
start:
                di
                ld      sp, $F000
                ld      hl, $5040               ; "P@", easy to find
                ld      ($8000), hl
                ld      a, $CB
                ld      ($8002), a
.stop:
                jr      .stop
last:
                SAVEBIN "test_payload.bin", start, last - start
