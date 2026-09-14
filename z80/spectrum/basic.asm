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
