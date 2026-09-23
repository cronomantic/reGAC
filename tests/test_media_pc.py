# ReGAC, tools for Graphic Adventure Creator adventures.
#
# Copyright (C) 2025 Cronomantic
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see <https://www.gnu.org/licenses/>.
#
# The interpreters in z80/ are not part of this program and are given under
# the MIT licence instead: see z80/LICENSE.
#
"""The .EXE a PC runs, loaded by DOS itself.

What `mz_exe` writes is only right if DOS agrees, so the test that matters
builds a program that asks DOS where it put it -- its PSP, CS, SS, SP and the
top of the memory it was given -- and writes the answers to a file.  It also
reads a word of its own image through DS set from CS, which is how the
interpreter will find its data with no relocation table.
"""

import os
import struct
import sys

try:
    import pytest
except ImportError:
    pytest = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import dosbox  # noqa: E402
from regac.media import MZ_PAGE, mz_exe, paragraphs  # noqa: E402

if pytest is not None:
    needs_tools = pytest.mark.skipif(
        not dosbox.available(), reason="NASM and DOSBox-X must be on the path"
    )
else:

    def needs_tools(func):
        return func


ENTRY = 0x40                    # not nought, so that IP is seen to be read
MEMORY = 3000                   # bytes behind the image the file does not carry
STACK = 0x400
MARK = b"REGAC"

PROBE = f"""\
bits 16
org 0
seen:   times 10 db 0           ; PSP, CS, SS, SP, top of memory
mark:   db "{MARK.decode()}"
name:   db "OUT.BIN", 0
        times {ENTRY} - ($ - $$) db 0
start:  mov ax, cs
        mov ds, ax
        mov [seen + 0], es
        mov [seen + 2], cs
        mov [seen + 4], ss
        mov [seen + 6], sp
        mov ax, [es:2]
        mov [seen + 8], ax
        mov ah, 0x3C
        xor cx, cx
        mov dx, name
        int 0x21
        jc .out
        mov bx, ax
        mov ah, 0x40
        mov cx, name - seen
        mov dx, seen
        int 0x21
        mov ah, 0x3E
        int 0x21
.out:   mov ax, 0x4C00
        int 0x21
"""


def header(exe):
    return struct.unpack("<2s13H", exe[:28])


def test_the_image_starts_on_a_paragraph():
    exe = mz_exe(b"\x90" * 100)
    assert header(exe)[4] == 2
    assert exe[32:] == b"\x90" * 100


def test_a_last_page_that_is_full_is_written_as_nought():
    exe = mz_exe(bytes(MZ_PAGE - 32))
    assert len(exe) == MZ_PAGE
    assert header(exe)[1:3] == (0, 1)


def test_a_stack_dos_cannot_set_up_is_refused():
    for stack in (0, 3, 0x10002):
        with pytest.raises(ValueError):
            mz_exe(b"", stack=stack)


@needs_tools
def test_dos_loads_it_where_the_header_says(tmp_path):
    folder = str(tmp_path)
    source = os.path.join(folder, "probe.asm")
    with open(source, "w") as f:
        f.write(PROBE)
    image = open(dosbox.assemble(source, os.path.join(folder, "probe.bin")),
                 "rb").read()
    with open(os.path.join(folder, "PROBE.EXE"), "wb") as f:
        f.write(mz_exe(image, entry=ENTRY, stack=STACK, memory=MEMORY))
    dosbox.run(folder, "PROBE.EXE")

    out = open(os.path.join(folder, "OUT.BIN"), "rb").read()
    psp, cs, ss, sp, top = struct.unpack("<5H", out[:10])
    assert out[10:] == MARK, "DS set from CS does not see the image"
    assert cs == psp + paragraphs(256), "the image is not behind the PSP"
    assert ss - cs == paragraphs(len(image)) + paragraphs(MEMORY)
    assert sp == STACK
    # Asked for all of it, it gets far more than the least it needs.
    assert top > ss + paragraphs(STACK)
