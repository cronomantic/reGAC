; MIT License, Copyright (c) 2025 Cronomantic
;
; Unpacking a message: z80/common/unpack.asm, and doc/textos.md.
;
; A code below the first pair is a character; anything else stands for two
; codes, and those may stand for two more.  Walking that needs a stack, so the
; machine's own is used by letting the routine call itself.  A message unpacks
; on its own and is printed as it unpacks, a character at a time.
;
; Everything here reads the text section through ES, which the printer takes
; for the screen: so it is loaded again after every character printed.

; Read the text section's header and remember where its parts are, as offsets
; in its segment.
; Corrupts: AX, BX, CX, SI, ES
text_init:
                mov     al, SECTION_TEXT
                call    db_section
                mov     [text_seg], es
                mov     al, [es:si]
                mov     [first_pair], al
                mov     al, [es:si + 1]
                mov     [pair_count], al
                add     si, 2
                mov     [pair_table], si
                xor     ah, ah
                shl     ax, 1                   ; two bytes a pair
                add     si, ax
                mov     [message_lookup], si    ; message number -> its place
                add     si, 256
                mov     ax, [es:si]
                mov     [message_count], ax
                add     si, 2
                mov     [offset_table], si
                shl     ax, 1                   ; two bytes a message
                add     si, ax
                mov     ax, [es:si]
                mov     [data_size], ax
                add     si, 2
                mov     [message_data], si
                ret

; Where message DX starts, in AX, counted from the packed bytes.  One past the
; last gives their length, which makes the end of a message easy.
; Corrupts: BX, ES
message_offset:
                cmp     dx, [message_count]
                jne     .from_table
                mov     ax, [data_size]
                ret
.from_table:
                mov     es, [text_seg]
                mov     bx, dx
                shl     bx, 1
                add     bx, [offset_table]
                mov     ax, [es:bx]
                ret

; Print message DX, unpacking it as it goes.  A change of ink lasts to the end
; of the message it is in: see z80/common/unpack.asm.
; Corrupts: everything but DS
print_packed:
                call    unpack_message
                call    text_end                ; the last word goes out
                mov     al, [text_ink_start]    ; and the ink goes back
                jmp     text_ink

; Unpack message DX into the printer, and nothing else: the word it ends in is
; left open and the ink as it is, for a hole that prints an object's name
; inside another text.
; Corrupts: everything but DS
unpack_message:
                call    message_offset
                mov     cx, ax                  ; where it starts
                inc     dx
                call    message_offset          ; where the next one does
                sub     ax, cx                  ; how many packed bytes
                mov     si, [message_data]
                add     si, cx
                mov     cx, ax
.next:
                jcxz    .ended
                dec     cx
                mov     es, [text_seg]
                mov     al, [es:si]
                inc     si
                push    si
                push    cx
                call    expand_code
                pop     cx
                pop     si
                jmp     .next
.ended:
                ret

; Expand one code, AL, and print what it stands for: the left half of a pair
; first, by calling itself, and the right half after.
; Corrupts: everything but DS
expand_code:
                cmp     al, [first_pair]
                jb      .a_character
                sub     al, [first_pair]        ; which pair
                xor     ah, ah
                mov     bx, ax
                shl     bx, 1                   ; two bytes an entry
                add     bx, [pair_table]
                mov     es, [text_seg]
                mov     ax, [es:bx]             ; the left half, and the right
                push    ax
                call    expand_code             ; left first, so order holds
                pop     ax
                mov     al, ah
                jmp     expand_code             ; then right, as a tail call
.a_character:
                jmp     text_put

; The place in the store of message number AL, in DX.  Carry set if there is
; no such message.
; Corrupts: AX, BX, ES
message_index:
                mov     es, [text_seg]
                mov     bl, al
                xor     bh, bh
                add     bx, [message_lookup]
                mov     al, [es:bx]
                cmp     al, NO_MESSAGE
                je      .none
                xor     ah, ah
                mov     dx, ax
                clc
                ret
.none:
                stc
                ret

section .data
text_seg:       dw      0
pair_table:     dw      0
message_lookup: dw      0
offset_table:   dw      0
message_data:   dw      0
message_count:  dw      0
data_size:      dw      0
first_pair:     db      0
pair_count:     db      0
section .text
