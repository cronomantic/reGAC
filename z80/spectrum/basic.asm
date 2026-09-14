; MIT License, Copyright (c) 2025 Cronomantic
;
; The little of BASIC a loader is written in: where a program lives, the four
; words it uses, and the mark that hides a number's real value after its
; digits.  Both loaders, the tape one and the +3's, are built out of these.

BASIC_START     equ 23755               ; where a BASIC program begins
TOKEN_REM       equ 234
TOKEN_CLEAR     equ 253
TOKEN_RANDOMIZE equ 249
TOKEN_USR       equ 192
NUMBER_MARK     equ 14                  ; what hides a number after its digits
ENTER           equ 13

; Where a loading screen goes and how much of it there is.  A build says
; whether there is one by defining SCREEN, and then the file has to be next to
; the source; see doc/binario.md.
SCREEN_AT       equ $4000
SCREEN_BYTES    equ 6912
