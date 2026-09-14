; MIT License, Copyright (c) 2025 Cronomantic
;
; Where each block goes, how long it is, and on a 128 which page it goes in.
; A block that goes nowhere ends the list.
;
; Both loaders read this: the tape one to ask the ROM for each block, and the
; +3 one to ask +3DOS, which pages the bank itself when it is told which.
load_table:
                IFDEF SCREEN
                ; The loading screen goes first, so that there is something to
                ; look at while the rest comes in.
                dw      SCREEN_AT
                dw      SCREEN_BYTES
                IFDEF BANKED
                db      5               ; the page the screen itself lives in
                ENDIF
                ENDIF
                dw      start
                dw      last - start
                IFDEF BANKED
                db      2               ; the interpreter's own page, always in
                IF DB_BANK_COUNT > 0
                dw      DB_WINDOW
                dw      DB_BANK_USED_0
                db      DB_PAGE_0
                ENDIF
                IF DB_BANK_COUNT > 1
                dw      DB_WINDOW
                dw      DB_BANK_USED_1
                db      DB_PAGE_1
                ENDIF
                IF DB_BANK_COUNT > 2
                dw      DB_WINDOW
                dw      DB_BANK_USED_2
                db      DB_PAGE_2
                ENDIF
                IF DB_BANK_COUNT > 3
                dw      DB_WINDOW
                dw      DB_BANK_USED_3
                db      DB_PAGE_3
                ENDIF
                IF DB_BANK_COUNT > 4
                dw      DB_WINDOW
                dw      DB_BANK_USED_4
                db      DB_PAGE_4
                ENDIF
                IF DB_BANK_COUNT > 5
                dw      DB_WINDOW
                dw      DB_BANK_USED_5
                db      DB_PAGE_5
                ENDIF
                ENDIF
                dw      0
                db      ENTER
