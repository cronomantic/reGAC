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
"""The Amstrad the other way round, for an adventure that does not fit.

A 464 has no banks and its database has to sit in one stretch, so the two
parts of the Quijote -- 21115 and 20984 bytes -- did not fit at all: the
interpreter takes the bottom of the memory from $4000 and the firmware stops
everything at $B100.  They fit now because the two change places.  The
interpreter goes into the sixteen kilobytes under $4000, which are RAM like
any other once both ROMs are out of the way, and the database has everything
from $4000 to the island below the firmware: 27392 bytes instead of the eight
and a half thousand that were left over the code.

Two things there are worth watching, and they are what is checked here: that
the adventure plays at all in that shape, and that the tape a person really
loads carries it.  What the island is for -- the tape routines, which cannot
be under $4000 while they run because the lower ROM is back for as long as
they take -- is watched in test_tape_cpc.py.
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
from regac.binary import Database  # noqa: E402
from regac.media import (CPC_LOW_CODE_AT, CPC_LOW_DATABASE_AT,  # noqa: E402
                         CPC_LOW_ISLAND_AT, CPC_LOW_MUSIC_AT, CPC_LOW_ROOM,
                         MUSIC_LOADS_AT, cpc_low_tape, low_loader, low_room)
from test_game_cpc import glyph_table, wait_screen  # noqa: E402

CPC = os.path.join(ROOT, "z80", "cpc")
SOURCE = os.path.join(CPC, "game.asm")
DATABASE = os.path.join(CPC, "game.rgac")
BINARY = os.path.join(CPC, "game.bin")
LISTING = os.path.join(CPC, "game.lst")
ADVENTURE = os.path.join(ROOT, "snapshots", "quijote1.json")
LANDS_ROOM = 1                  # where its own condition sends the player

if pytest is not None:
    needs_tools = pytest.mark.skipif(
        not emulator.available() or not os.path.exists(ADVENTURE),
        reason="sjasmplus and ZEsarUX must be in tools/, with the Quijote",
    )
    is_slow = pytest.mark.skipif(
        not os.environ.get("REGAC_SLOW"),
        reason="set REGAC_SLOW=1: a tape takes tape time",
    )
else:

    def needs_tools(func):
        return func

    is_slow = needs_tools


def built():
    """The Quijote for a 464, laid out the other way round: the file the
    loader brings in, and the database that goes behind it."""
    with open(ADVENTURE, encoding="utf-8") as f:
        ddb = json.load(f)
    data = Database(ddb, machine="cpc").build()
    with open(DATABASE, "wb") as f:
        f.write(data)
    emulator.assemble(SOURCE, listing=LISTING, defines=("LOW_CODE",))
    with open(BINARY, "rb") as f:
        code = f.read()
    return ddb, code, data


def started(session, code, data):
    """What the loader does: the interpreter's file at $4000, its mover
    called, the database over the top of it, and then the starter the mover
    left at the island."""
    assert session.put(code, CPC_LOW_DATABASE_AT), (
        "the interpreter never landed whole"
    )
    session.jump(CPC_LOW_DATABASE_AT)
    time.sleep(0.5)
    # The mover has come back to whatever was behind it and the machine is
    # running that, so this one is written with it held as well -- and read
    # back, because what it is running could have been anything.
    assert session.put(data, CPC_LOW_DATABASE_AT), (
        "the database never landed whole"
    )
    session.jump(CPC_LOW_ISLAND_AT)


@needs_tools
def test_it_plays_with_the_interpreter_under_the_database():
    """The adventure that did not fit, playing: it describes the room it
    starts in, which means the database was read from where it now lives and
    the code ran from under it."""
    ddb, code, data = built()
    assert len(code) + len(data) > 0xB100 - CPC_LOW_DATABASE_AT, (
        "this adventure fits the usual way round: it proves nothing here"
    )
    assert len(data) <= CPC_LOW_ROOM
    glyphs = glyph_table(Database(ddb))
    # The room it opens in is its title, and that one is never described: its
    # own high priority condition waits for a key there and sends the player
    # to the library, which is the room to look for.  The interpreter looks at
    # that table before paying a new room its description, the way the
    # original does -- see doc/pendiente.md.
    where = ddb["locations"][str(LANDS_ROOM)]["desc"].split()[0]

    session = emulator.Session(machine="CPC464")
    try:
        time.sleep(3.0)
        started(session, code, data)
        # Its title has to be all the way out before a key is pressed at it.
        # The interpreter looks at the keyboard only when it stops to ask, so
        # a space pressed while the title is still going is a space nobody
        # hears -- and then it waits for one that never comes again.  The last
        # word of the title is what says it has finished.
        wait_screen(session, glyphs,
                    ddb["locations"][str(ddb["init_loc"])]["desc"].split()[-1],
                    timeout=60.0)
        for _ in range(4):
            session.type_keys(" ")
            time.sleep(2.0)
        lines = wait_screen(session, glyphs, where, timeout=120.0)
    finally:
        session.close()
    assert any(where in line for line in lines if line), (
        f"the room it opens into was never described: {lines}"
    )


@needs_tools
def test_the_loader_says_where_everything_goes():
    """The BASIC lines, which are the whole of what a person runs: keep out of
    everything from $4000 up, bring the interpreter in there, call the mover,
    load the database over it, and call the starter."""
    lines = low_loader("!")
    for number in (10, 30, 40, 50, 60):
        assert bytes([number, 0]) in lines, f"no line {number} in the loader"
    assert bytes([0x1C]) + (CPC_LOW_DATABASE_AT - 1).to_bytes(2, "little") in lines
    assert bytes([0x1C]) + CPC_LOW_ISLAND_AT.to_bytes(2, "little") in lines
    assert bytes([0x1C]) + CPC_LOW_CODE_AT.to_bytes(2, "little") not in lines, (
        "BASIC cannot call the interpreter itself: at that moment $0400 is ROM"
    )


@needs_tools
def test_a_database_that_does_not_even_fit_this_way_is_refused():
    """Which is the only thing left to say no to: there is no third layout."""
    try:
        cpc_low_tape(b"code", bytes(CPC_LOW_ROOM + 1))
    except ValueError as complaint:
        assert "fit" in str(complaint)
    else:
        raise AssertionError("a database too big for this layout was allowed")


@needs_tools
def test_the_music_goes_up_under_the_island_and_the_loader_carries_it():
    """A low build may have music, which the interpreter's own place forbade
    for a long time: the music used to live at $0300 and that is where the
    interpreter is in a build of this shape.

    It goes to the other end instead, into the five kilobytes under the
    island, so what it costs comes off the end of the database rather than out
    of the room the interpreter has to grow into.  Above the interpreter was
    tried first and left a hundred and eighty three bytes between the two.
    See the map at the top of z80/cpc/game.asm."""
    assert CPC_LOW_MUSIC_AT < CPC_LOW_ISLAND_AT, (
        "the music would land on the island"
    )
    assert low_room(b"tune") < low_room() == CPC_LOW_ROOM, (
        "the database was not told that the music is now above it"
    )

    lines = low_loader("!", None, "!")
    for number in (22, 24):
        assert bytes([number, 0]) in lines, (
            f"no line {number} in the loader: the music is never brought in"
        )
    assert bytes([0x1C]) + MUSIC_LOADS_AT.to_bytes(2, "little") in lines, (
        "the loader never calls the mover that carries the music up"
    )
    # And it is asked for before the database is loaded over $4000, which is
    # where both movers read from.
    assert lines.index(bytes([24, 0])) < lines.index(bytes([50, 0]))

    # The database that fits is smaller by exactly what the music was given.
    tape = cpc_low_tape(b"code", bytes(low_room(b"tune")), music=b"tune")
    assert tape
    try:
        cpc_low_tape(b"code", bytes(low_room(b"tune") + 1), music=b"tune")
    except ValueError as complaint:
        assert "music" in str(complaint)
    else:
        raise AssertionError("a database that reaches the music was allowed")


@is_slow
@needs_tools
def test_the_tape_starts_the_quijote(tmp_path):
    """The whole of it off a tape, which is what a person does with a 464:
    twenty nine kilobytes at the speed the firmware reads them."""
    ddb, code, data = built()
    path = str(tmp_path / "quijote.cdt")
    with open(path, "wb") as f:
        f.write(cpc_low_tape(code, data))
    glyphs = glyph_table(Database(ddb))
    where = ddb["locations"][str(ddb["init_loc"])]["desc"]

    session = emulator.Session(
        machine="CPC464", extra=["--fastautoload", "--simulaterealloadfast"]
    )
    try:
        time.sleep(2.5)
        session.command("smartload " + path)
        wait_screen(session, glyphs, ddb["messages"]["240"].strip()[:3],
                    timeout=1200.0)
        for _ in range(4):
            session.type_keys(" ")
            time.sleep(2.0)
        lines = wait_screen(session, glyphs, where.split()[0], timeout=120.0)
    finally:
        session.close()
    assert any(where.split()[0] in line for line in lines if line), (
        f"the tape never got the adventure going: {lines}"
    )


if __name__ == "__main__":
    test_it_plays_with_the_interpreter_under_the_database()
    print("the Quijote plays on a 464")
