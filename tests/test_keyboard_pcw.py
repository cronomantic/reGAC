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
"""The PCW's keyboard, read on a real machine.

There is no port to ask: the keyboard's own controller writes the state of
every key into the last sixteen bytes of the first sixty four kilobytes of
RAM, and a bit is high while its key is held, which is the other way round
from every other machine here.  Both of those were found by holding a key down
and watching which byte of the whole 256K moved.

A build that does nothing but look at the keys is run and the emulator asked
to press and release each one.  The press and the release go as separate
events on purpose: handing the emulator a whole string to type drops letters.
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

PCW = os.path.join(ROOT, "z80", "pcw")
SOURCE = os.path.join(PCW, "test_keyboard.asm")
BINARY = os.path.join(PCW, "keys.bin")
LISTING = os.path.join(PCW, "keys.lst")
DATABASE = os.path.join(PCW, "text.rgac")
LOADS_AT = 0x0100
KEYS_AT = 0xFFF0

# What the host's keys are called here.  Enter and the rub out are the two the
# emulator does not give a character of its own; everything else is its ASCII.
EVENTS = {chr(13): 129, chr(10): 129, chr(8): 132}

MACHINE = "pcw"
NEWLINE = chr(10)
FRAME_CYCLES = 80000          # a fiftieth of a second of this processor

# A key that is held sets its count to KEY_DELAY -- thirty five frames -- and
# it goes down one a frame until the key repeats.  Measuring is started once
# the count has been seen this high, which both proves the press arrived and
# leaves room for the ten frames the measuring wants.
COUNTING_FROM = 20

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
        for name in ("ready_flag", "last_seen", "seen_count", "raw_row",
                     "scan_result")
    }
    with open(BINARY, "rb") as f:
        blob = f.read()
    session = emulator.Session(machine="PCW8256")
    try:
        # A Joyce with no disk in it is still busy with the loader its
        # keyboard gave it, and what is written into it while that goes on
        # gets trodden on.  Eight seconds and not four: the failure it saves
        # is the clock's, not the build's.
        time.sleep(emulator.longer(8.0))
        # Fifteen seconds and not five: what this waits for takes well under
        # one, and the only thing a short plazo buys is a failure that is the
        # clock's and not the build's.
        started = session.start_code(blob, LOADS_AT, where["ready_flag"],
                                     wanted=1, timeout=15.0)
        assert started, "the build never started"
        # And that the loop is turning, not just that it set its flag once.
        # The look writes raw_row every time round, so a byte put there that
        # comes back changed is the loop answering.  Without this the first
        # key of a test can be sent into a machine that is not yet scanning,
        # and then it is simply lost -- which is what this file used to fail
        # on, a different test each run.
        session.command(f"write-memory {where['raw_row']} 170")
        assert session.wait_for_change(where["raw_row"], 170, timeout=10.0), (
            "the build started but never scanned"
        )
    except BaseException:
        # Whatever goes wrong here, the machine is this function's to close:
        # the caller has not got it yet, and one left running holds the port
        # and takes every test after it down with it.
        session.close()
        raise
    return session, where


def pressed(session, where, char, held=0.1):
    """Press one key and say what the scanning made of it.  The key is let go
    when the scan has seen it and not when a sleep runs out, and the next
    press does not start until the keyboard has come back to rest: a press
    that begins while the last one is still down is a different test."""
    session.command(f"write-memory {where['last_seen']} 0")
    code = EVENTS.get(char, ord(char.lower()))
    session.command(f"send-keys-event {code} 1")
    session.wait_for_change(where["last_seen"], 0, timeout=10.0)
    seen = session.read(where["last_seen"], 1)[0]
    session.command(f"send-keys-event {code} 0")
    session.wait_for(where["scan_result"], 0, timeout=10.0, every=0.05)
    return chr(seen)


def machine_frames(session, how_many):
    """Let the machine run for a number of its own frames.

    Holding a key for a tenth of a second of ours is not holding it for a
    tenth of a second of the machine's: this emulator does not keep the
    machine's time, and when the host has other work the same sleep buys
    fewer cycles.  A key held for less than one look at the keyboard is a key
    nobody sees, and that is how this file used to lose one -- a different
    test every run, which looked like the build's fault and was the clock's.
    So the waiting here is counted in the processor's own cycles."""
    wanted = FRAME_CYCLES * how_many
    session.command("reset-tstates-partial")
    deadline = time.time() + emulator.longer(10.0)
    while time.time() < deadline:
        spent = int(session.command("get-tstates-partial").split(NEWLINE)[0].strip())
        if spent >= wanted:
            return
        time.sleep(0.01)


def type_them(session, text, hold_frames=4):
    last = None
    for char in text:
        code = EVENTS.get(char, ord(char.lower()))
        if code == last:
            time.sleep(emulator.Session.SAME_KEY_GAP)
        session.command(f"send-keys-event {code} 1")
        machine_frames(session, hold_frames)
        session.command(f"send-keys-event {code} 0")
        last = code
        machine_frames(session, hold_frames)


def jumped(session, at, where):
    """Point the processor at one of the build's other entries and wait until
    it is really there.  Everything above `read_a_line` in the source is those
    entries and what they call, and everything below is the loop that watches
    the keyboard, so a program counter past that address is the jump having
    landed.  Typing before it lands throws the first keys away."""
    session.jump(at)
    deadline = time.time() + emulator.longer(10.0)
    while time.time() < deadline:
        if session.pc() >= where:
            return True
        time.sleep(0.02)
    return False


@needs_tools
def test_it_reads_what_is_pressed():
    session, where = watching()
    try:
        assert pressed(session, where, "A") == "A"
        assert pressed(session, where, "M") == "M"
        assert pressed(session, where, "7") == "7"
        assert pressed(session, where, ".") == "."
        assert pressed(session, where, ",") == ","
        assert pressed(session, where, " ") == " "
        assert pressed(session, where, chr(13)) == chr(13)
        assert pressed(session, where, chr(8)) == chr(8)
    finally:
        session.close()


@needs_tools
def test_a_bit_is_high_while_its_key_is_held():
    """Which is worth saying out loud, because it is the other way round from
    the Spectrum and the Amstrad, and the row the letters sit on is read
    straight out of memory."""
    session, where = watching()
    try:
        # The last three bytes are not keys: one bit of them is always on and
        # another comes and goes with nothing held at all, which is the
        # controller's own business.  Every row that carries a character does
        # come to rest with nothing pressed -- looked at more than once,
        # because a machine that has just been switched on takes a moment to
        # settle and one look can catch it still doing so.
        for _ in range(5):
            rest = session.read(KEYS_AT, 13)
            if rest == bytes(13):
                break
            time.sleep(0.2)
        assert rest == bytes(13), f"something is held with nothing pressed: {rest.hex()}"
        session.command("send-keys-event 97 1")  # the letter A
        assert session.wait_for(where["raw_row"], 0b00100000, timeout=10.0,
                                every=0.05), "the row never showed the key"
        session.command("send-keys-event 97 0")
        assert session.wait_for(where["raw_row"], 0, timeout=10.0, every=0.05), (
            "the row never came clear again"
        )
    finally:
        session.close()


@needs_tools
def test_every_key_of_a_word_arrives():
    """Five keys typed, five keys seen: nothing runs together and nothing is
    lost."""
    session, where = watching()
    try:
        session.command(f"write-memory {where['seen_count']} 0")
        type_them(session, "MIRAR")
        assert session.wait_for(where["seen_count"], 5, timeout=10.0,
                                every=0.05), (
            f"{session.read(where['seen_count'], 1)[0]} keys were counted, not 5"
        )
        assert chr(session.read(where["last_seen"], 1)[0]) == "R"
    finally:
        session.close()


@needs_tools
def test_a_whole_line_is_read_and_shown():
    """The path the runtime uses: keys into the line, a rub out that takes the
    last one back, and enter to end it.  What lands in the buffer is the
    adventure's own codes, not ASCII."""
    import json

    from regac.binary import Database

    # Three goes at it: a key held while the machine stalls repeats, as it
    # does on the original, so a host busy enough can turn one letter into
    # two, or drop one altogether and leave the line never finished.  What is
    # being tested is the reading of a line, not the emulator's sense of
    # time, so a line that did not arrive as it was sent is typed again --
    # and **that includes one that never arrived at all**, which used to
    # break straight out of this loop and waste the two goes left.
    length, typed, why = (0,), b"", None
    for attempt in range(3):
        session, where = watching()
        at = {
            name: emulator.label_address(LISTING, name)
            for name in ("read_a_line", "line_done", "line_seen", "input_buffer")
        }
        try:
            session.command(f"write-memory {at['line_done']} 0")
            if not jumped(session, at["read_a_line"], at["read_a_line"]):
                why = "the jump into read_line never landed"
                continue
            type_them(session, "MIRARX" + chr(8) + chr(13))
            if not session.wait_for(at["line_done"], 0xFF, timeout=10.0,
                                    every=0.2):
                why = "the line was never finished"
                continue
            why = None
            length = session.read(at["line_seen"], 2)
            typed = session.read(at["input_buffer"], length[0])
        finally:
            session.close()
        if why is None and length[0] == 5:
            break
    assert why is None, f"{why}, three times over"

    with open(os.path.join(ROOT, "snapshots", "megacorp2.json"), encoding="utf-8") as f:
        chars = Database(json.load(f), machine="pcw").store.charset.chars
    code = {char: number for number, char in chars.items()}
    assert length[0] == 5, f"five characters were left, not {length[0]}"
    assert typed == bytes(code[c] for c in "MIRAR")


def line_typed(steps, machine, events):
    """Start the build, point it at read_line, play the steps at it and give
    back the line it read, as characters."""
    import json

    from regac.binary import Database

    # Three goes, for the reason the test above gives: what is being tested
    # is what the reading makes of the keys, not whether a busy host got all
    # of them into the machine.
    typed, why = b"", None
    for attempt in range(3):
        session, where = watching()
        at = {
            name: emulator.label_address(LISTING, name)
            for name in ("read_a_line", "line_done", "line_seen", "input_buffer")
        }
        try:
            session.command(f"write-memory-raw {at['line_done']} 00")
            if not jumped(session, at["read_a_line"], at["read_a_line"]):
                why = "the jump into read_line never landed"
                continue
            keystrokes.play(session, steps, events)
            if not session.wait_for(at["line_done"], 0xFF, timeout=10.0,
                                    every=0.2):
                why = "the line was never finished"
                continue
            why = None
            length = session.read(at["line_seen"], 2)[0]
            typed = session.read(at["input_buffer"], length)
        finally:
            session.close()
        if why is None:
            break
    assert why is None, f"{why}, three times over"

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
        assert jumped(session, at["read_a_line"], at["read_a_line"]), (
            "the jump into read_line never landed"
        )
        session.command(f"send-keys-event {code} 1")
        # Waited for by looking, like everything else in this file.  A new key
        # sets key_repeat to KEY_DELAY and the count goes down a frame at a
        # time, so a value up near the top is the press having been seen; a
        # sleep of a twentieth of a second is a guess that the machine got
        # there, and when it had not the count was still nought and the
        # measuring stopped before it began -- "only 0 frames were counted".
        #
        # Caught above COUNTING_FROM, which leaves well over the ten frames
        # this wants: the count only passes this way once, because at the
        # bottom it is set to KEY_EVERY and never climbs again.
        deadline = time.time() + emulator.longer(10.0)
        while session.read(at["key_repeat"], 1)[0] < COUNTING_FROM:
            assert time.time() < deadline, "the key was never seen"
            time.sleep(0.01)
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
