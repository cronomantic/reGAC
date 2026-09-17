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
"""The Amstrad's keyboard, read on a real machine.

The keys hang off the sound chip there, so a build that does nothing but look
at them is run and the emulator is asked to press and release each one.  The
press and release are sent as separate events on purpose: handing the emulator
a whole string to type drops letters, which is what made this look unreliable
until it was measured.
"""

import os
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
import keystrokes  # noqa: E402

CPC = os.path.join(ROOT, "z80", "cpc")
SOURCE = os.path.join(CPC, "test_keyboard.asm")
BINARY = os.path.join(CPC, "keys.bin")
LISTING = os.path.join(CPC, "keys.lst")
DATABASE = os.path.join(CPC, "text.rgac")
LOADS_AT = 0x4000

MACHINE = "cpc"
NEWLINE = chr(10)
FRAME_CYCLES = 80000          # a fiftieth of a second of this processor
EVENTS = emulator.Session.EVENT_KEYS

if pytest is not None:
    needs_tools = pytest.mark.skipif(
        not emulator.available() or not os.path.exists(DATABASE),
        reason="sjasmplus and ZEsarUX must be in tools/, with a database built",
    )
else:

    def needs_tools(func):
        return func


def watching():
    """Start the build that watches the keyboard, and say where it keeps what
    it saw."""
    listing = emulator.assemble(SOURCE, listing=LISTING)
    where = {
        name: emulator.label_address(listing, name)
        for name in ("ready_flag", "last_seen", "seen_count")
    }
    with open(BINARY, "rb") as f:
        blob = f.read()
    session = emulator.Session(machine="CPC6128")
    time.sleep(3.0)
    for at in range(0, len(blob), 512):
        session.command(f"write-memory-raw {LOADS_AT + at} " + blob[at:at + 512].hex().upper())
    session.jump(LOADS_AT)
    time.sleep(1.0)
    assert session.read(where["ready_flag"], 1)[0] == 1, "the build never started"
    return session, where


def pressed(session, where, char, held=0.1):
    """Press one key and say what the scanning made of it."""
    session.command(f"write-memory {where['last_seen']} 0")
    code = emulator.Session.EVENT_KEYS.get(char, ord(char.lower()))
    session.command(f"send-keys-event {code} 1")
    time.sleep(held)
    session.command(f"send-keys-event {code} 0")
    time.sleep(0.05)
    return chr(session.read(where["last_seen"], 1)[0])


@needs_tools
def test_it_reads_what_is_pressed():
    session, where = watching()
    try:
        assert pressed(session, where, "A") == "A"
        assert pressed(session, where, "M") == "M"
        assert pressed(session, where, "7") == "7"
        assert pressed(session, where, ".") == "."
        assert pressed(session, where, " ") == " "
    finally:
        session.close()


@needs_tools
def test_every_key_of_a_word_arrives():
    """Five keys typed, five keys seen: nothing runs together and nothing is
    lost."""
    session, where = watching()
    try:
        session.command(f"write-memory {where['seen_count']} 0")
        session.type_keys("MIRAR")
        time.sleep(0.3)
        assert session.read(where["seen_count"], 1)[0] == 5
        assert chr(session.read(where["last_seen"], 1)[0]) == "R"
    finally:
        session.close()


def line_typed(steps, machine, events):
    """Start the build, point it at read_line, play the steps at it and give
    back the line it read, as characters."""
    import json

    from regac.binary import Database

    session, where = watching()
    at = {
        name: emulator.label_address(LISTING, name)
        for name in ("read_a_line", "line_done", "line_seen", "input_buffer")
    }
    try:
        session.command(f"write-memory-raw {at['line_done']} 00")
        session.jump(at["read_a_line"])
        time.sleep(0.3)
        keystrokes.play(session, steps, events)
        assert session.wait_for(at["line_done"], 0xFF, timeout=10.0, every=0.2), (
            "the line was never finished"
        )
        length = session.read(at["line_seen"], 2)[0]
        typed = session.read(at["input_buffer"], length)
    finally:
        session.close()

    with open(os.path.join(ROOT, "snapshots", "megacorp2.json"), encoding="utf-8") as f:
        chars = Database(json.load(f), machine=machine).store.charset.chars
    return "".join(chars[code] for code in typed)


@needs_tools
def test_keys_typed_over_each_other_all_arrive():
    """Each key down before the last one is up, which is typing quickly: the
    original keeps all of them, and so does this."""
    assert line_typed(keystrokes.ROLLED, MACHINE, EVENTS) == keystrokes.ROLLED_GIVES


@needs_tools
def test_a_key_pressed_while_another_is_held_types_nothing_twice():
    """While two keys are down nothing is decided, so the one that stays down
    is not typed a second time when the other goes up."""
    assert line_typed(keystrokes.TWO_AT_ONCE, MACHINE, EVENTS) == keystrokes.TWO_AT_ONCE_GIVES


@needs_tools
def test_a_key_held_down_repeats():
    """As on the original, where the ROM repeats a key that is held."""
    line = line_typed(keystrokes.HELD, MACHINE, EVENTS)
    assert len(line) > 1 and set(line) == {keystrokes.HELD_KEY}, line


@needs_tools
def test_a_hold_lasts_as_long_as_it_says():
    """A wait like HOLD's, a hundred frames with nothing pressed, counted in
    the processor's own cycles: this emulator does not keep the machine's
    time, and a frame is only as long as the looks at the keyboard it is
    counted in.  Those were guessed once and out by up to three and a half
    times."""
    session, where = watching()
    at = {name: emulator.label_address(LISTING, name)
          for name in ("hold_a_while", "line_done")}
    try:
        session.command(f"write-memory-raw {at['line_done']} 00")
        session.command("reset-tstates-partial")
        session.jump(at["hold_a_while"])
        deadline = time.time() + 30.0
        while session.read(at["line_done"], 1)[0] != 0xFF:
            assert time.time() < deadline, "the wait never ended"
            time.sleep(0.02)
        cycles = int(session.command("get-tstates-partial").split("\n")[0].strip())
    finally:
        session.close()
    frame = cycles / 100
    assert FRAME_CYCLES * 0.9 < frame < FRAME_CYCLES * 1.1, (
        f"a frame took {frame:.0f} cycles, not about {FRAME_CYCLES}"
    )


@needs_tools
def test_a_held_key_repeats_in_frames_as_long_as_frames():
    """While a key is held next_key counts the frames to its repeat, and a
    look at the keyboard that finds a key costs more than one that finds
    nothing, so those frames are counted in looks of their own.  Measured in
    the processor's cycles, from the counter as it goes down."""
    session, where = watching()
    at = {name: emulator.label_address(LISTING, name)
          for name in ("read_a_line", "key_repeat")}
    code = EVENTS.get("R", ord("r"))
    try:
        session.jump(at["read_a_line"])
        time.sleep(0.3)
        session.command(f"send-keys-event {code} 1")
        time.sleep(0.05)
        session.command("reset-tstates-partial")
        first = last = session.read(at["key_repeat"], 1)[0]
        spent = 0
        while True:
            now = session.read(at["key_repeat"], 1)[0]
            cycles = int(session.command("get-tstates-partial").split(NEWLINE)[0].strip())
            if now < 4 or now > last:
                break
            last, spent = now, cycles
            time.sleep(0.05)
        session.command(f"send-keys-event {code} 0")
    finally:
        session.close()
    frames = first - last
    assert frames >= 10, f"only {frames} frames were counted"
    frame = spent / frames
    assert FRAME_CYCLES * 0.85 < frame < FRAME_CYCLES * 1.15, (
        f"a frame with a key held took {frame:.0f} cycles, not about {FRAME_CYCLES}"
    )


if __name__ == "__main__":
    test_it_reads_what_is_pressed()
    print("it reads what is pressed")
    test_every_key_of_a_word_arrives()
    print("every key of a word arrives")
