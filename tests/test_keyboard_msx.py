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
"""The MSX's keyboard, read on a real machine and without its BIOS.

That machine has a routine for this and keeps the whole matrix in memory at
$FBE5 for anyone to read -- which is where the eleven rows were measured, one
key at a time -- but none of it survives the interpreter taking the machine
for itself: the BIOS is paged out and its interrupt is not running, so nothing
is scanning any more.  What is checked here is our own scanning, of the same
8255 the Amstrad has: the row into the low half of port C, its eight keys back
on port B.

The build takes the whole machine first, as the real one will, because the
font it prints with comes out of the database and the database goes where the
BIOS was.
"""

import json
import os
import subprocess
import sys
import time

try:
    import pytest
except ImportError:
    pytest = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import emulator  # noqa: E402

MSX = os.path.join(ROOT, "z80", "msx")
SOURCE = os.path.join(MSX, "test_keyboard.asm")
BINARY = os.path.join(MSX, "keys.bin")
LISTING = os.path.join(MSX, "keys.lst")
DATABASE = os.path.join(MSX, "text.rgac")
ADVENTURE = os.path.join(ROOT, "snapshots", "megacorp2.json")
LOADS_AT = 0x8000

# What the host's keys are called here.  Enter and the rub out are the two the
# emulator does not give a character of its own; everything else is its ASCII.
EVENTS = {chr(13): 129, chr(10): 129, chr(8): 140}

if pytest is not None:
    needs_tools = pytest.mark.skipif(
        not emulator.available() or not os.path.exists(ADVENTURE),
        reason="sjasmplus and ZEsarUX must be in tools/, with an adventure",
    )
else:

    def needs_tools(func):
        return func


def watching():
    """Start the build that watches the keyboard, and say where it keeps what
    it saw."""
    subprocess.run(
        [sys.executable, "-m", "regac", "build", ADVENTURE, DATABASE, "-m", "msx"],
        cwd=ROOT, check=True, capture_output=True,
    )
    listing = emulator.assemble(SOURCE, listing=LISTING)
    where = {
        name: emulator.label_address(listing, name)
        for name in ("ready_flag", "last_seen", "seen_count", "raw_row",
                     "read_a_line", "line_done", "line_seen", "input_buffer")
    }
    with open(BINARY, "rb") as f:
        blob = f.read()
    session = emulator.Session(machine="MSX1")
    time.sleep(7.0)
    started = session.start_code(blob, LOADS_AT, where["ready_flag"], wanted=1,
                                 timeout=20.0)
    assert started, "the build never started"
    return session, where


def pressed(session, where, char, held=0.12):
    """Press one key and say what the scanning made of it."""
    session.command(f"write-memory-raw {where['last_seen']} 00")
    code = EVENTS.get(char, ord(char.lower()))
    session.command(f"send-keys-event {code} 1")
    time.sleep(held)
    session.command(f"send-keys-event {code} 0")
    time.sleep(0.06)
    return chr(session.read(where["last_seen"], 1)[0])


def type_them(session, text, hold_for=0.08):
    last = None
    for char in text:
        code = EVENTS.get(char, ord(char.lower()))
        if code == last:
            time.sleep(hold_for * 2)
        session.command(f"send-keys-event {code} 1")
        time.sleep(hold_for)
        session.command(f"send-keys-event {code} 0")
        last = code
        time.sleep(hold_for)


@needs_tools
def test_it_reads_what_is_pressed():
    session, where = watching()
    try:
        for char in "AMZ7 ":
            assert pressed(session, where, char) == char, f"{char} did not arrive"
        assert pressed(session, where, chr(13)) == chr(13)
        assert pressed(session, where, chr(8)) == chr(8)
    finally:
        session.close()


@needs_tools
def test_the_row_a_letter_sits_on_is_the_one_measured():
    """A and B are the top two bits of row two, and a bit goes *low* while its
    key is held -- which is the other way round from the PCW and the same as
    the Spectrum and the Amstrad.  read_row turns it about, so what the
    interpreter sees is a bit set."""
    session, where = watching()
    try:
        assert session.read(where["raw_row"], 1)[0] == 0, (
            "something is held with nothing pressed"
        )
        for char, bit in (("a", 0b01000000), ("b", 0b10000000)):
            session.command(f"send-keys-event {ord(char)} 1")
            time.sleep(0.12)
            seen = session.read(where["raw_row"], 1)[0]
            session.command(f"send-keys-event {ord(char)} 0")
            time.sleep(0.08)
            assert seen == bit, f"{char} came back as {seen:08b}, not {bit:08b}"
    finally:
        session.close()


@needs_tools
def test_every_key_of_a_word_arrives():
    """Five keys typed, five keys seen: nothing runs together and nothing is
    lost."""
    session, where = watching()
    try:
        session.command(f"write-memory-raw {where['seen_count']} 00")
        type_them(session, "MIRAR")
        time.sleep(0.3)
        assert session.read(where["seen_count"], 1)[0] == 5
        assert chr(session.read(where["last_seen"], 1)[0]) == "R"
    finally:
        session.close()


@needs_tools
def test_a_whole_line_is_read():
    """The path the runtime uses: keys into the line, a rub out that takes the
    last one back, and enter to end it.  What lands in the buffer is the
    adventure's own codes, not ASCII."""
    from regac.binary import Database

    session, where = watching()
    try:
        session.command(f"write-memory-raw {where['line_done']} 00")
        session.command(f"set-register PC={where['read_a_line']:04X}H")
        time.sleep(0.2)
        type_them(session, "MIRARX" + chr(8) + chr(13))
        assert session.wait_for(where["line_done"], 0xFF, timeout=10.0, every=0.2), (
            "the line was never finished"
        )
        length = session.read(where["line_seen"], 2)
        typed = session.read(where["input_buffer"], length[0])
    finally:
        session.close()

    with open(ADVENTURE, encoding="utf-8") as f:
        chars = Database(json.load(f), machine="msx").store.charset.chars
    code = {char: number for number, char in chars.items()}
    assert length[0] == 5, f"five characters were left, not {length[0]}"
    assert typed == bytes(code[c] for c in "MIRAR")


if __name__ == "__main__":
    test_it_reads_what_is_pressed()
    print("it reads what is pressed")
