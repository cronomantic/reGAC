; MIT License, Copyright (c) 2025 Cronomantic
;
; What +3DOS is asked through, and where the +3 keeps what it last paged.
;
; Two pieces of a +3 build use them: the loader, which reads the adventure,
; and disk3.asm, which saves a game.  A build with banks carries both, a build
; without them only the second, so this is included by each and says itself
; once: IFNDEF looks at DEFINEs and not at labels, hence the word.

                IFNDEF  DOS3_NAMES
                DEFINE  DOS3_NAMES

DOS_OPEN        equ $0106
DOS_CLOSE       equ $0109
DOS_ABANDON     equ $010C
DOS_READ        equ $0112
DOS_WRITE       equ $0115
DOS_SET_1346    equ $013F
DOS_SET_MESSAGE equ $014E
DOS_OFF_MOTOR   equ $019C

BANKM           equ $5B5C               ; what was last sent out of $7FFD
BANK678         equ $5B67               ; and out of $1FFD
NAME_END        equ $FF                 ; what a name ends with here

                ENDIF
