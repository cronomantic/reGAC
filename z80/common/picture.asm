; MIT License, Copyright (c) 2025 Cronomantic
;
; The picture interpreter: it walks the drawing commands of a picture and asks
; the machine underneath to put them on the screen.
;
; Nothing here knows how a screen works, what colour means or how many pixels
; there are.  That is all on the other side of gfx_line, gfx_fill and the
; rest, which is the same boundary the Python renderer draws between its
; devices.  See doc/graficos.md.
;
; Two of those commands are handed straight over as macros rather than calls,
; because they are met inside this loop and a picture can meet them tens of
; thousands of times: GFX_BORDER, which most machines do in three
; instructions, and GFX_COLOURS, which is empty on every machine that settles
; its colours once per shape.  A machine whose colours belong to a pixel
; rather than to a cell cannot wait that long -- an ink of nine is settled
; against the paper of the moment, and the paper may change before the shape
; arrives -- so it settles here instead.

GFX_MAX_DEPTH   equ 8                   ; a picture may call others

; PICTURE_BOTTOM and PICTURE_TOP -- the rows a picture may use, in the
; coordinates the commands are written in -- come from each machine's own
; fill.asm, which needs them for the same reason.

CMD_BORDER      equ $01
CMD_PLOT        equ $02
CMD_ELLIPSE     equ $03
CMD_FILL        equ $04
CMD_BGFILL      equ $05
CMD_SHADE       equ $06
CMD_CALL        equ $07
CMD_RECT        equ $08
CMD_LINE        equ $09
CMD_INK         equ $10
CMD_PAPER       equ $11
CMD_BRIGHT      equ $12
CMD_FLASH       equ $13
CMD_PENS        equ $14                 ; the two pens a fill weaves, on the
                                        ; machines that have such a thing

; Where the pictures are.
; Corrupts: AF, BC, DE, HL
picture_init:
                ld      a, SECTION_GRAPHICS
                call    db_section
                ld      (gfx_section), hl
                ld      e, (hl)
                inc     hl
                ld      d, (hl)
                inc     hl
                ld      (gfx_count), de
                ld      (gfx_index), hl
                ld      hl, 0                   ; nothing known yet, and no
                ld      (gfx_known), hl         ; picture is numbered zero
                ld      (gfx_behind), hl
                ret

; Find picture HL.  Its commands come back in HL with their length in BC;
; carry set when there is no such picture.
;
; **The last two found are kept**, because a picture that calls another calls
; it over and over: the animations are built as one small picture called a
; dozen times, from a picture called a dozen times, four deep.  Without any
; of this the index is walked from the top for every one of them.
;
; One was kept before, and one is not enough, because the misses are exactly
; the moments of coming back up a level: with A calling B and B calling C, the
; one slot holds C while A asks for B again.  Counted on picture 28 of Los
; pajaros de Bangkok, which makes 4726 of these calls: **one slot misses 657
; times and two slots miss 81**.  Three would miss 27 and four 7, and neither
; is worth its bytes.
;
; The second slot is not promoted when it answers -- the front one stays in
; front -- because that costs code and, counted the same way, changes
; nothing: still 81.
; Corrupts: AF, DE
picture_find:
                ld      (gfx_wanted), hl
                ld      de, (gfx_known)
                or      a
                sbc     hl, de
                jr      z, .the_front
                ld      hl, (gfx_wanted)
                ld      de, (gfx_behind)
                or      a
                sbc     hl, de
                jr      nz, .look
                ld      hl, (gfx_behind_at)
                ld      bc, (gfx_behind_size)
                or      a
                ret
.the_front:
                ld      hl, (gfx_known_at)
                ld      bc, (gfx_known_size)
                or      a
                ret
.look:
                ; Neither of the two knew it, so the one in front steps back
                ; and the search will put the new one in its place.  Here and
                ; not at .found because here is where HL and BC are free.
                ld      hl, (gfx_known)
                ld      (gfx_behind), hl
                ld      hl, (gfx_known_at)
                ld      (gfx_behind_at), hl
                ld      hl, (gfx_known_size)
                ld      (gfx_behind_size), hl
                ld      hl, (gfx_index)
                ld      bc, (gfx_count)
.each:
                ld      a, b
                or      c
                scf
                ret     z
                dec     bc
                ld      e, (hl)
                inc     hl
                ld      d, (hl)
                inc     hl
                push    hl
                ld      hl, (gfx_wanted)
                or      a
                sbc     hl, de
                pop     hl
                jr      z, .found
                inc     hl
                inc     hl
                jr      .each
.found:
                ld      e, (hl)
                inc     hl
                ld      d, (hl)
                ld      hl, (gfx_section)
                add     hl, de                  ; the block for this picture
                ld      c, (hl)
                inc     hl
                ld      b, (hl)
                inc     hl                      ; BC = how many bytes of commands
                ld      (gfx_known_at), hl
                ld      (gfx_known_size), bc
                ld      de, (gfx_wanted)
                ld      (gfx_known), de
                or      a
                ret

; Draw picture HL.
; Corrupts: everything
draw_picture:
                push    hl                      ; clearing treads on HL
                call    text_window_below       ; a picture takes its rows back
                ld      a, SECTION_GRAPHICS     ; printing may have taken the
                call    db_bank_in              ; pictures' bank away
                xor     a
                ld      (gfx_depth), a
                dec     a                       ; $FF, which is no colour
                ld      (gfx_border_now), a     ; so the first one is written
                call    gfx_clear
                pop     hl
                IFDEF   PICTURE_INKS
                call    picture_inks_set        ; its own inks, where it has any
                ENDIF
                call    gfx_start_colours       ; what a picture starts in
                call    run_picture
                jp      gfx_show                ; and let the machine show it

; Draw picture HL without clearing first, which is what CALL needs.
; Corrupts: everything
run_picture:
                call    picture_find
                ret     c
                ld      d, b
                ld      e, c                    ; DE counts the bytes left
.next:
                ld      a, d
                or      e
                ret     z
                dec     de
                ld      a, (hl)
                inc     hl
                ld      c, a
                ; one byte commands first, and the border before them all:
                ; it is first because it is the one a picture meets most --
                ; forty three thousand times in one of them -- and having its
                ; own landing saves reading the command a second time to find
                ; out what it was.
                cp      CMD_BORDER
                jp      z, .a_border
                cp      CMD_INK
                jp      z, .one_byte
                cp      CMD_PAPER
                jp      z, .one_byte
                cp      CMD_BRIGHT
                jp      z, .one_byte
                cp      CMD_FLASH
                jp      z, .one_byte
                cp      CMD_PENS
                jp      z, .two_pens
                cp      CMD_CALL
                jp      z, .call_picture
                cp      CMD_PLOT
                jp      z, .two_bytes
                cp      CMD_FILL
                jp      z, .two_bytes
                cp      CMD_BGFILL
                jp      z, .two_bytes
                cp      CMD_SHADE
                jp      z, .two_bytes
                ; the rest take four
                ld      a, (hl)
                inc     hl
                dec     de
                ld      (gfx_x0), a
                ld      a, (hl)
                inc     hl
                dec     de
                ld      (gfx_y0), a
                ld      a, (hl)
                inc     hl
                dec     de
                ld      (gfx_x1), a
                ld      a, (hl)
                inc     hl
                dec     de
                ld      (gfx_y1), a
                call    .keep_place
                ld      a, c
                cp      CMD_LINE
                jr      nz, .not_line
                call    gfx_line
                jr      .resume
.not_line:
                cp      CMD_RECT
                jr      nz, .not_rect
                call    gfx_rect
                jr      .resume
.not_rect:
                call    gfx_ellipse
.resume:
                ld      hl, (gfx_code)
                ld      de, (gfx_left)
                jp      .next

; Drawing treads on every register, so the place in the commands goes to
; memory for as long as that takes.  The commands that only set a colour cost
; nothing at all, which matters: the animations are thousands of them.  That
; is why the border does not come through here either, and why the machine
; gives it as a macro that may only touch AF: one picture of Los pájaros de
; Bangkok sets the border forty three thousand times, and putting the place
; away and fetching it back for each of them cost it a second and three
; quarters, and even the call and the return cost it half a second.
.keep_place:
                ld      (gfx_code), hl
                ld      (gfx_left), de
                ret

; The border, which is its own landing because of how often it is met.
;
; **The same border as last time is not written again.** These are not a
; handful: picture 28 of Los pajaros de Bangkok is forty three thousand
; BORDER commands and fifty three lines -- it is a flashing border built out
; of one small picture called over and over -- and only seventeen thousand of
; them ask for a colour the border is not already showing.  The other twenty
; six thousand wrote the same value to the hardware, which on an MSX is a
; call, a table and two writes to the video chip.
;
; What is compared is the colour as the picture gave it, **not masked**: how
; many of its bits mean anything is the machine's business, and the Amstrad
; uses more than three.
.a_border:
                ld      a, (hl)                 ; the colour it asks for
                inc     hl
                dec     de
                ld      c, a
                ld      a, (gfx_border_now)
                cp      c
                jp      z, .next
                ld      a, c
                ld      (gfx_border_now), a     ; and this leaves A alone
                GFX_BORDER                      ; the machine knows how
                jp      .next

; INK, PAPER, BRIGHT and FLASH, which are kept and not acted on.  The border
; used to come through here too and does not any more, so there is no longer
; a command to tell apart at the top.
.one_byte:
                ld      a, (hl)
                inc     hl
                dec     de
                ld      b, a
                ld      a, c
                push    hl
                ld      hl, gfx_ink
                cp      CMD_INK
                jr      z, .store
                ld      hl, gfx_paper
                cp      CMD_PAPER
                jr      z, .store
                ld      hl, gfx_bright
                cp      CMD_BRIGHT
                jr      z, .store
                ld      hl, gfx_flash
.store:
                ld      (hl), b
                pop     hl
                GFX_COLOURS                     ; only for a machine that has
                jp      .next                   ; to settle them here: see below
.two_pens:
                ld      a, (hl)
                inc     hl
                dec     de
                ld      (gfx_pen1), a
                ld      a, (hl)
                inc     hl
                dec     de
                ld      (gfx_pen2), a
                jp      .next
.two_bytes:
                ld      a, (hl)
                inc     hl
                dec     de
                ld      (gfx_x0), a
                ld      a, (hl)
                inc     hl
                dec     de
                ld      (gfx_y0), a
                call    .keep_place
                ld      a, c
                cp      CMD_PLOT
                jr      nz, .a_fill
                ; A point outside the picture is not drawn at all, and the
                ; picture carries on: their ROM refuses to plot out of range,
                ; where a line's far end is brought to the edge instead.
                ; Asked of the original with pictures of our own written over
                ; one of MegaCorp's -- see doc/pendiente.md.
                ; The two ends in one test, because the Next has no bytes
                ; to spare here: the rows a picture may use are a hundred and
                ; twenty eight of them, so taking the bottom off leaves one
                ; comparison to make -- and anything below it wraps past the
                ; top and fails the same test.
                ld      a, (gfx_y0)
                sub     PICTURE_BOTTOM
                cp      PICTURE_TOP - PICTURE_BOTTOM + 1
                call    c, gfx_plot
                jp      .resume                 ; too far for a jr since the
                                                ; border learned to say no
.a_fill:
                ld      b, FILL_INK
                cp      CMD_FILL
                jr      z, .fill_kind
                ld      b, FILL_PAPER
                cp      CMD_BGFILL
                jr      z, .fill_kind
                ld      b, FILL_SHADE
.fill_kind:
                ld      a, b
                call    set_fill_pattern
                call    gfx_fill
                jp      .resume
.call_picture:
                ld      a, (hl)
                inc     hl
                dec     de
                ld      c, a
                ld      a, (hl)
                inc     hl
                dec     de
                ld      b, a                    ; the number is two bytes here
                ld      a, (gfx_depth)
                inc     a
                cp      GFX_MAX_DEPTH
                jp      nc, .next               ; too deep, leave it
                ld      (gfx_depth), a
                push    hl                      ; keep our place, draw the
                push    de                      ; other one, then carry on
                ld      h, b
                ld      l, c
                call    run_picture
                pop     de
                pop     hl
                ld      a, (gfx_depth)
                dec     a
                ld      (gfx_depth), a
                jp      .next

gfx_section:    dw      0
gfx_index:      dw      0
gfx_count:      dw      0
gfx_wanted:     dw      0
; The second of the two pictures kept, which is what stops the index being
; walked every time a call comes back up a level.  See picture_find.
gfx_behind:      dw     0
gfx_behind_at:   dw     0
gfx_behind_size: dw     0
gfx_known:      dw      0                       ; the last picture looked up
gfx_known_at:   dw      0
gfx_known_size: dw      0
gfx_code:       dw      0
gfx_left:       dw      0
gfx_depth:      db      0
; What the border is showing, so that asking for it again costs nothing.  It
; is no colour at all between pictures, because gfx_clear and the machines'
; own mode setting may have moved it.  See .one_byte.
gfx_border_now: db      $FF
gfx_x0:         db      0
gfx_y0:         db      0
gfx_x1:         db      0
gfx_y1:         db      0
gfx_ink:        db      0
gfx_paper:      db      7
gfx_pen1:       db      1               ; only the machines with pens use these
gfx_pen2:       db      1
gfx_bright:     db      0
gfx_flash:      db      0
