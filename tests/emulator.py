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
"""Building and running the 8 bit interpreter, headless.

sjasmplus assembles it and ZEsarUX runs it, driven over its remote protocol,
so the tests can look at what the real code left in memory and on the screen
instead of taking the assembly on trust.  Both tools live under tools/.

The awkward parts, learned the hard way: the emulator needs a couple of
seconds to finish booting its ROM before a snapshot will load, and the run has
to be polled until the program counter is actually inside our code.
"""

import os
import re
import socket
import subprocess
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
PORT = 10000
BOOT_SECONDS = 2.5
CODE_START = 0x8000


def find_sjasmplus():
    path = os.path.join(TOOLS, "sjasmplus.exe")
    return path if os.path.isfile(path) else None


def find_zesarux():
    for entry in sorted(os.listdir(TOOLS)) if os.path.isdir(TOOLS) else []:
        path = os.path.join(TOOLS, entry, "zesarux.exe")
        if os.path.isfile(path):
            return path
    return None


def available():
    return bool(find_sjasmplus() and find_zesarux())


def assemble(source, listing=None, defines=()):
    """Assemble one file where it sits.  Returns the listing path.

    `defines` are handed to the assembler as it would be from a makefile,
    which is how a build says things that are not the adventure's business:
    whether there is a loading screen, for one."""
    sjasmplus = find_sjasmplus()
    if not sjasmplus:
        raise RuntimeError("sjasmplus is not in tools/")
    folder = os.path.dirname(os.path.abspath(source))
    listing = listing or os.path.join(folder, "out.lst")
    result = subprocess.run(
        [sjasmplus, f"--lst={listing}"]
        + [f"-D{name}" for name in defines]
        + [os.path.basename(source)],
        cwd=folder,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"sjasmplus failed:\n{result.stdout}\n{result.stderr}")
    return listing


def label_address(listing, label):
    """Where a label ended up, read out of the sjasmplus listing."""
    # A listing row is line number, address, the bytes assembled there, then
    # the source; a label may sit after its own data bytes.
    pattern = re.compile(
        r"^\s*\d+[+~]*\s+([0-9A-Fa-f]{4})\s+(?:[0-9A-Fa-f]{2}[.\s]+)*"
        + re.escape(label)
        + r":"
    )
    with open(listing, encoding="utf-8", errors="ignore") as f:
        for line in f:
            found = pattern.search(line)
            if found:
                return int(found.group(1), 16)
    raise KeyError(f"no label {label!r} in {listing}")


class Session:
    """A running ZEsarUX, talked to over its remote protocol."""

    def __init__(self, machine="48k", port=PORT, extra=()):
        emulator = find_zesarux()
        if not emulator:
            raise RuntimeError("ZEsarUX is not in tools/")
        self.process = subprocess.Popen(
            [
                emulator, "--noconfigfile", "--machine", machine,
                "--vo", "null", "--ao", "null",
                "--enable-remoteprotocol", "--remoteprotocol-port", str(port),
            ] + list(extra),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.socket = None
        for _ in range(40):
            try:
                self.socket = socket.create_connection(("127.0.0.1", port), timeout=1.0)
                break
            except OSError:
                time.sleep(0.25)
        if self.socket is None:
            self.close()
            raise RuntimeError("ZEsarUX never opened its remote protocol port")
        self.socket.settimeout(8.0)
        self.__drain()

    def __drain(self):
        data = b""
        while True:
            try:
                chunk = self.socket.recv(65536)
            except socket.timeout:
                break
            if not chunk:
                break
            data += chunk
            if data.endswith(b"command> "):
                break
        return data.decode("latin-1")

    def command(self, text):
        self.socket.sendall(text.encode("latin-1") + b"\n")
        return self.__drain()

    def load(self, path):
        # The ROM has to finish booting or the snapshot will not take.
        time.sleep(BOOT_SECONDS)
        return self.command(f"smartload {os.path.abspath(path)}")

    def pc(self):
        reply = self.command("get-registers")
        found = re.search(r"PC=([0-9A-Fa-f]{4})", reply)
        return int(found.group(1), 16) if found else None

    def read(self, address, length):
        out = bytearray()
        while length:
            piece = min(length, 1024)
            reply = self.command(f"read-memory {address} {piece}")
            digits = "".join(re.findall(r"[0-9A-Fa-f]{2}", reply.split("\n", 1)[0]))
            out += bytes.fromhex(digits[: piece * 2])
            address += piece
            length -= piece
        return bytes(out)

    def start_code(self, blob, at, flag, wanted=0xFF, tries=3, timeout=25.0):
        """Put a build in memory, start it, and say whether it got going.

        Writing straight into a running machine is how the Amstrads and the
        PCW are driven, and on the PCW it is now and then too early: with no
        disk in it that machine is still busy with the loader its keyboard
        gave it, and once in a while that treads on what has just been
        written.  So this looks at whether the build reached the mark it was
        going to reach, and puts it back if it did not.
        """
        for attempt in range(tries):
            for offset in range(0, len(blob), 512):
                piece = blob[offset:offset + 512]
                self.command(
                    f"write-memory-raw {at + offset} " + piece.hex().upper()
                )
            self.command(f"set-register PC={at:04X}H")
            if self.wait_for(flag, wanted, timeout=timeout, every=0.2):
                return True
        return False

    def wait_for(self, address, wanted, timeout=20.0, every=0.4):
        """Run until a byte in memory takes a value, and say whether it did.
        Look often when what happens after the wait is being measured, because
        whatever runs between the end and the next look is counted too."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            time.sleep(every)
            if self.pc() and self.read(address, 1)[0] == wanted:
                return True
        return False

    # Where each key sits in the Spectrum matrix: which half row, which bit.
    KEY_MATRIX = {}
    for _row, _keys in enumerate([
        ".ZXCV", "ASDFG", "QWERT", "12345", "09876", "POIUY",
        "@LKJH", " .MNB",
    ]):
        for _bit, _key in enumerate(_keys):
            if _key != ".":
                # "@" stands for enter, which has no printable character
                KEY_MATRIX[chr(13) if _key == "@" else _key] = (_row, _bit)

    # The two shifts, which have no character of their own, and the marks
    # that need one held with them.  A full stop on a Spectrum is symbol
    # shift and M together.
    SYMBOL_SHIFT = (7, 1)
    CAPS_SHIFT = (0, 0)
    SYMBOLS = {".": "M", ",": "N", "-": "J", "!": "1", "?": "C", ":": "Z"}

    def hold(self, row=None, bit=None):
        """Hold one key down, or let everything go when given nothing."""
        rows = ["FF"] * 8
        if row is not None:
            rows[row] = f"{0xFF ^ (1 << bit):02X}"
        return self.command("set-ui-io-ports " + "".join(rows) + "00")

    def hold_both(self, first, second):
        """Hold two keys at once, which is how a mark is typed."""
        rows = [0xFF] * 8
        for row, bit in (first, second):
            rows[row] ^= 1 << bit
        return self.command(
            "set-ui-io-ports " + "".join(f"{r:02X}" for r in rows) + "00"
        )

    def type(self, text, hold_for=0.12):
        """Type at the keyboard, one key at a time, letting each go before the
        next.  Driving the matrix directly keeps the timing ours rather than
        the emulator's, which drops keys when they are sent in a stream."""
        for char in text.upper():
            with_shift = self.SYMBOLS.get(char)
            if with_shift:
                self.hold_both(self.SYMBOL_SHIFT, self.KEY_MATRIX[with_shift])
            else:
                where = self.KEY_MATRIX.get(char)
                if where is None:
                    continue
                self.hold(*where)
            time.sleep(hold_for)
            self.hold()
            time.sleep(hold_for)

    # Most of the emulator's key numbers are the ASCII of what is printed on
    # the key, but not all: these are the ones that are not.
    EVENT_KEYS = {chr(13): 129, chr(10): 129, chr(8): 132, ".": 183}

    # The marks that share a key with something else need shift held down,
    # and the emulator counts shift as a key of its own; 133 is one of the
    # three numbers that behave as one.  The pairs are an Amstrad's, which is
    # where this is needed: typing LOAD"NAME at its BASIC wants a quote.
    SHIFT_KEY = 133
    SHIFTED = {'"': "2", "!": "1", "#": "3", "$": "4", "%": "5", "&": "6",
               "'": "7", "(": "8", ")": "9", "=": "-", "*": ":", "+": ";",
               "<": ",", ">": ".", "?": "/"}

    def type_keys(self, text, hold_for=0.06):
        """Type at a keyboard the matrix cannot be reached through, which is
        every machine here but the Spectrum.  The emulator will press and
        release a key on demand, which comes to the same thing and keeps the
        timing ours: sending a whole string at it drops letters.  The codes
        are ASCII, a letter in lower case, and enter is 129."""
        last = None
        for char in text:
            with_shift = self.SHIFTED.get(char)
            base = with_shift or char
            code = self.EVENT_KEYS.get(base, ord(base.lower()))
            if code == last:
                # The same key twice running needs a gap between them or the
                # machine takes it for one long press: "&3FFF" comes out as
                # "&3FF" without this.
                time.sleep(hold_for * 2)
            if with_shift:
                self.command(f"send-keys-event {self.SHIFT_KEY} 1")
                time.sleep(hold_for)
            self.command(f"send-keys-event {code} 1")
            time.sleep(hold_for)
            self.command(f"send-keys-event {code} 0")
            if with_shift:
                self.command(f"send-keys-event {self.SHIFT_KEY} 0")
            last = code
            time.sleep(hold_for)

    def keys(self, text, pause=100):
        """Type something, as if at the keyboard.  The pause is how long each
        key is held, in milliseconds."""
        return self.command(f"send-keys-string {pause} {text}")

    def enter(self, pause=100):
        return self.command(f"send-keys-ascii {pause} 13")

    def close(self):
        try:
            if self.socket:
                self.command("quit")
                self.socket.close()
        except OSError:
            pass
        try:
            self.process.terminate()
            self.process.wait(timeout=5)
        except Exception:
            self.process.kill()


def run(snapshot, listing, flag="done_flag", flag_value=0xFF, reads=(), machine="48k"):
    """Load a snapshot, wait for the program to say it finished, and read
    memory.  `reads` is a list of (address, length)."""
    session = Session(machine=machine)
    try:
        session.load(snapshot)
        address = label_address(listing, flag)
        finished = session.wait_for(address, flag_value)
        return finished, [session.read(start, size) for start, size in reads]
    finally:
        session.close()
