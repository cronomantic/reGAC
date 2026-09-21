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
"""The harness that drives the machines, checked without one.

What is in here is the part of `emulator.py` that is our own reasoning rather
than a conversation with ZEsarUX: it can be tried against a machine of paper,
in no time, and it is worth trying because when it is wrong the bill comes as
a test that fails once every few runs on a different drawing each time, which
is the dearest kind of bug there is.
"""

import contextlib
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import emulator  # noqa: E402

AT = 0x0100
FLAG = 0x9000


class Machine:
    """A machine of paper, and one that loses bytes.

    It keeps what is written to it, spoils one byte of the first so many
    builds it is given -- which is what a PCW does now and then, because with
    no disk in it the loader its keyboard gave it is still running and treads
    on what has just arrived -- and says it got going once its counter has
    been pointed somewhere.
    """

    # The real one, working on a machine of paper: start_code leans on it, and
    # so does everything else that writes a build into a machine.
    put = emulator.Session.put

    def __init__(self, spoils=0):
        self.memory = {}
        self.spoils = spoils
        self.builds = 0                 # how many times it was given the whole
        self.starts = 0                 # and how many times it was started

    @contextlib.contextmanager
    def held(self):
        yield self

    def command(self, order):
        words = order.split()
        if words[0] == "write-memory-raw":
            where, blob = int(words[1]), bytes.fromhex(words[2])
            if where == AT:             # the first piece of a build
                self.builds += 1
            for n, byte in enumerate(blob):
                self.memory[where + n] = byte
            if where == AT and self.builds <= self.spoils:
                self.memory[where + 3] ^= 0xFF
        elif words[0] == "set-register":
            self.starts += 1

    def read(self, at, length, zone=None):
        return bytes(self.memory.get(at + n, 0) for n in range(length))

    def wait_for(self, address, wanted, timeout=20.0, every=0.4):
        return self.starts > 0


def started(machine, blob, **rest):
    """start_code run against a machine of paper."""
    return emulator.Session.start_code(machine, blob, AT, FLAG, **rest)


def test_a_build_that_lands_whole_is_started_once():
    blob = bytes(range(256)) * 4
    machine = Machine()
    assert started(machine, blob)
    assert machine.builds == 1, "it wrote the build more than once for nothing"
    assert machine.starts == 1
    assert machine.read(AT, len(blob)) == blob


def test_a_build_that_loses_a_byte_is_written_again():
    """Which is the whole point: code with a byte changed can still run to its
    end and set the mark it was going to set, so waiting for the mark does not
    catch it.  What catches it is reading back what was written."""
    blob = bytes(range(256)) * 4
    machine = Machine(spoils=1)
    assert started(machine, blob)
    assert machine.builds == 2, "the build was never put back"
    assert machine.starts == 1, (
        "the processor was pointed at a build that had not been checked"
    )
    assert machine.read(AT, len(blob)) == blob


def test_a_machine_that_never_takes_it_whole_is_given_up_on():
    """And said so, rather than being started on something that is wrong."""
    blob = bytes(range(256)) * 4
    machine = Machine(spoils=99)
    assert not started(machine, blob, tries=3)
    assert machine.builds == 3, "it did not try as many times as it was told"
    assert machine.starts == 0, "it was started on a build known to be wrong"


def test_what_has_to_happen_while_it_is_held_waits_for_the_check():
    """`then` is for whatever must happen before the machine is let go again,
    and it only happens once what was written has been read back and found
    whole -- which is what keeps a processor from being pointed at a build
    with a byte astray."""
    blob = bytes(range(256)) * 4
    seen = []
    machine = Machine(spoils=1)
    assert machine.put(blob, AT, then=lambda: seen.append(machine.builds))
    assert seen == [2], f"it was done on the wrong attempt: {seen}"

    machine = Machine(spoils=99)
    assert not machine.put(blob, AT, tries=2, then=lambda: seen.append("never"))
    assert seen == [2], "it was done although the build never landed whole"
