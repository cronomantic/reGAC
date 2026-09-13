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

CPC = os.path.join(ROOT, "z80", "cpc")
SOURCE = os.path.join(CPC, "test_keyboard.asm")
BINARY = os.path.join(CPC, "keys.bin")
LISTING = os.path.join(CPC, "keys.lst")
DATABASE = os.path.join(CPC, "text.rgac")
LOADS_AT = 0x4000

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
    session.command(f"set-register PC={LOADS_AT:04X}H")
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


if __name__ == "__main__":
    test_it_reads_what_is_pressed()
    print("it reads what is pressed")
    test_every_key_of_a_word_arrives()
    print("every key of a word arrives")
