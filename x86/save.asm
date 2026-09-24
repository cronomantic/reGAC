; MIT License, Copyright (c) 2025 Cronomantic
;
; SAVE and LOAD on a PC: the game, and not the adventure, in one file beside
; the program -- the program's own name with .SAV for its last part, so that
; MEGACORP.EXE keeps its game in MEGACORP.SAV wherever it was run from.  No
; name is asked for, as none is on the 6128 or the PCW, which keep one game
; on the disk: the original saved one block and said nothing.
;
; Where the program is DOS says, at the end of its environment: the strings,
; an empty one, a word, and then the program's path.  A DOS too old to say --
; before 3.0 -- gets the file in the current directory, named GAME.SAV.
;
; A load that goes wrong leaves the game as it was: the file is read whole
; into a place of its own first, and only copied over the game once all of it
; has come.

PSP_ENVIRONMENT equ 2Ch
PATH_MOST       equ 80

; Work out the name the game is kept under.
; Corrupts: AX, BX, CX, SI, DI, ES
save_init:
                mov     es, [psp_seg]
                mov     es, [es:PSP_ENVIRONMENT]
                xor     si, si
.each_string:
                cmp     byte [es:si], 0
                je      .strings_done
.skip:
                inc     si
                cmp     byte [es:si], 0
                jne     .skip
                inc     si
                jmp     .each_string
.strings_done:
                cmp     word [es:si + 1], 1     ; one more string: the path
                jne     .as_it_was
                add     si, 3
                mov     di, save_name
                mov     bx, save_name           ; where the last part starts
                mov     cx, PATH_MOST - 5
.copy:
                mov     al, [es:si]
                inc     si
                test    al, al
                jz      .copied
                mov     [di], al
                inc     di
                cmp     al, '\'
                jne     .not_folder
                mov     bx, di
.not_folder:
                loop    .copy
                jmp     .as_it_was              ; too long to be a path
.copied:
                ; and the part after the last dot of the last part goes
                mov     si, bx
.find_dot:
                cmp     si, di
                je      .no_dot
                cmp     byte [si], '.'
                je      .dot
                inc     si
                jmp     .find_dot
.dot:
                mov     di, si
.no_dot:
                mov     byte [di], '.'
                mov     byte [di + 1], 'S'
                mov     byte [di + 2], 'A'
                mov     byte [di + 3], 'V'
                mov     byte [di + 4], 0
.as_it_was:
                ret

; Write CX bytes from DS:SI to the file.  Carry set if it went.
; Corrupts: everything but DS
tape_save:
                push    si
                push    cx
                mov     ah, 3Ch                 ; make it, or empty it
                xor     cx, cx
                mov     dx, save_name
                int     21h
                pop     cx
                pop     dx
                jc      .failed
                mov     bx, ax
                mov     ah, 40h
                int     21h
                pushf
                push    ax
                mov     ah, 3Eh
                int     21h
                pop     ax
                popf
                jc      .failed
                cmp     ax, cx                  ; all of it, or it did not go
                jne     .failed
                stc
                ret
.failed:
                clc
                ret

; Read CX bytes of the file back into DS:SI.  Carry set if it came; nothing
; is touched if it did not.
; Corrupts: everything but DS
tape_load:
                push    si
                push    cx
                mov     ax, 3D00h               ; open it to read
                mov     dx, save_name
                int     21h
                jc      .none
                mov     bx, ax
                pop     cx
                push    cx
                mov     ah, 3Fh
                mov     dx, save_place
                int     21h
                pushf
                push    ax
                mov     ah, 3Eh
                int     21h
                pop     ax
                popf
                pop     cx
                pop     di
                jc      .failed
                cmp     ax, cx
                jne     .failed
                mov     si, save_place          ; all of it came: over the game
                push    ds
                pop     es
                cld
                rep     movsb
                stc
                ret
.none:
                pop     cx
                pop     si
.failed:
                clc
                ret

section .data
psp_seg:        dw      0
save_name:      db      "GAME.SAV", 0
                times PATH_MOST - ($ - save_name) db 0
save_place:     times VM_STATE_BYTES db 0
section .text
