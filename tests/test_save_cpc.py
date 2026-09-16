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
"""Saving a game on a 6128, which means writing sectors nobody else will.

The 6128's interpreter may not call the firmware -- a call brings the lower
ROM back over the resident half of the database -- so it cannot save through
AMSDOS or the tape.  It does what the PCW does: the builder makes the file, an
ordinary one, the right size and empty, and writes where it starts into three
bytes at the front of the interpreter; the interpreter writes those sectors
itself and never touches the directory.

What is checked is both halves of that: that the builder writes into the
interpreter what the disk's own directory says, and that a block written to
that file comes back the same on a machine, off a disk -- and that a build
nobody told where to save says it could not, rather than pretending.  And then
the whole way round, the way a player would do it: an adventure started off
its own disk, a game saved, a step taken, and the game loaded back.
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

import disk as reader  # noqa: E402
import emulator  # noqa: E402
from regac.binary import Database, Reader  # noqa: E402
from regac.dsk import Disk  # noqa: E402
from regac.media import (  # noqa: E402
    CPC6128_SAVE_SECTORS,
    CPC6128_SAVE_WHERE,
    banks_of,
    cpc6128_disk,
    told_where_to_save,
)
from test_game_cpc import glyph_table, screen, wait_screen  # noqa: E402
from test_media_cpc import (  # noqa: E402
    BINARY_6128,
    DATABASE_6128,
    DEFS_6128,
    LISTING_6128,
    SOURCE_6128,
    asking,
)

CPC = os.path.join(ROOT, "z80", "cpc")
SOURCE = os.path.join(CPC, "test_save.asm")
LISTING = os.path.join(CPC, "save.lst")
BINARY = os.path.join(CPC, "save.bin")
LOADS_AT = 0x8000
SAVE = "JUEGO.SAV"
# La guerra de las vajillas, because it is the one of the eight whose first
# room has a way out of it: the rest start at a password or a title.  It saves
# with SAVE and loads with LOAD, and NORTE takes it from room one to room four.
VAJILLAS = os.path.join(ROOT, "snapshots", "vajillas1.json")

if pytest is not None:
    needs_tools = pytest.mark.skipif(
        not emulator.available(), reason="sjasmplus and ZEsarUX must be in tools/"
    )
else:

    def needs_tools(func):
        return func


def where_on_the_disk(image, name):
    """Where a file starts, worked out again from the outside: find it in the
    directory, take the first block it was given, and turn that into a track
    and a record of a data disk."""
    listing = reader.directory(reader.data_area(image))
    first = min(listing[name])[2][0]
    track, record = divmod(first * 2, 9)        # two sectors to a block
    return track, 0xC1 + record


def test_the_builder_tells_the_interpreter_where_its_game_goes():
    code = bytes((0x18, 3, 0, 0, 0)) + bytes(range(64))
    image = cpc6128_disk(code, b"resident", [b"a bank"], name="JUEGO")
    area = reader.data_area(image)
    listing = reader.directory(area)
    assert SAVE in listing, f"no saved game on the disk: {sorted(listing)}"
    saved = reader.contents(area, listing[SAVE])
    assert saved == bytes(CPC6128_SAVE_SECTORS * 512), (
        "the saved game should be the right size and empty"
    )
    carried = reader.contents(area, listing["JUEGO.BIN"])[128:]
    told = tuple(carried[CPC6128_SAVE_WHERE:CPC6128_SAVE_WHERE + 3])
    assert told == where_on_the_disk(image, SAVE) + (CPC6128_SAVE_SECTORS,), (
        f"the interpreter was told {told}, which is not where the file is"
    )
    assert carried[CPC6128_SAVE_WHERE + 3:CPC6128_SAVE_WHERE + 3 + 64] == \
        bytes(range(64)), "the rest of the interpreter was touched"


def test_a_binary_without_the_three_bytes_is_refused():
    try:
        told_where_to_save(bytes((0xF3, 0x31, 0, 0xBF)), (0, 0xC5))
    except ValueError:
        return
    raise AssertionError("a binary with nowhere to say it was written into")


def run_the_harness(tmp_path, told=True, protected=False):
    """The harness on a 6128 with a disk in it that holds only the saved game,
    told where that is or not, and with the disk's tab over or not.  What each
    of its flags said at the end, and the disk image as it was left: the
    emulator is asked to write what the machine wrote back into the file, so
    that where it went can be read off the disk from outside."""
    listing = emulator.assemble(SOURCE, listing=LISTING)
    where = {name: emulator.label_address(listing, name)
             for name in ("started_flag", "saved_flag", "loaded_flag",
                          "done_flag")}
    disk = Disk("cpc-data")
    disk.add(SAVE, bytes(CPC6128_SAVE_SECTORS * 512))
    path = str(tmp_path / "guarda.dsk")
    with open(path, "wb") as f:
        f.write(disk.image())
    with open(BINARY, "rb") as f:
        blob = f.read()
    if told:
        blob = told_where_to_save(blob, disk.where(SAVE))

    extra = ["--enable-dsk", "--dsk-file", path, "--dsk-persistent-writes"]
    if protected:
        extra.append("--dsk-write-protection")
    session = emulator.Session(machine="CPC6128", extra=extra)
    try:
        time.sleep(4.0)
        assert session.start_code(blob, LOADS_AT, where["started_flag"], 1), (
            "the harness never got going"
        )
        deadline = time.time() + 90.0
        while time.time() < deadline:
            if session.read(where["done_flag"], 1)[0]:
                break
            time.sleep(0.2)
        flags = {name: session.read(at, 1)[0] for name, at in where.items()}
    finally:
        session.close()
    time.sleep(1.0)                             # for the file to be written
    with open(path, "rb") as f:
        return flags, f.read()


BLOCK = bytes((n + 1) & 255 for n in range(1000))    # what the harness makes


@needs_tools
def test_a_game_written_to_the_disk_comes_back(tmp_path):
    flags, image = run_the_harness(tmp_path)
    assert flags["saved_flag"] == 1, f"saving said it did not go: {flags}"
    assert flags["loaded_flag"] == 1, f"loading said it did not come: {flags}"
    assert flags["done_flag"] == 0xFF, (
        f"what came back is not what went down: {flags}"
    )
    # And it went where AMSDOS would look for that file, not to some sectors
    # the two ends merely agree on: read off the disk, the file is the block,
    # and the rest of what was set aside is the nought it was padded with.
    area = reader.data_area(image)
    saved = reader.contents(area, reader.directory(area)[SAVE])
    assert saved[:len(BLOCK)] == BLOCK, (
        f"the saved game file does not hold the block: {saved[:16].hex()}"
    )
    assert saved[len(BLOCK):] == bytes(len(saved) - len(BLOCK))


@needs_tools
def test_a_disk_that_will_not_be_written_says_so(tmp_path):
    """With the tab over, the controller refuses and says why, and saving
    comes back saying it did not go instead of pretending it did."""
    flags, image = run_the_harness(tmp_path, protected=True)
    # It has to have got to the end at all: a flag that starts at nought
    # says nothing about a machine that is still waiting on the controller,
    # which is how this first came out.
    assert flags["done_flag"], f"it never finished with a locked disk: {flags}"
    assert flags["saved_flag"] == 0, f"it said it saved to a locked disk: {flags}"
    area = reader.data_area(image)
    saved = reader.contents(area, reader.directory(area)[SAVE])
    assert saved == bytes(len(saved)), "a locked disk was written to"


@needs_tools
def test_a_build_nobody_told_where_to_save_says_so(tmp_path):
    """Nought sectors to save into: both say they could not, and the disk is
    not touched, so what was rubbed out stays rubbed out."""
    flags, _ = run_the_harness(tmp_path, told=False)
    assert flags["saved_flag"] == 0, f"it said it saved to nowhere: {flags}"
    assert flags["loaded_flag"] == 0, f"it said it loaded from nowhere: {flags}"
    assert flags["done_flag"] == 0xEE, f"something came back from nowhere: {flags}"


def the_6128_disk_of(adventure):
    """An adventure's disk for a 6128, made the way release makes it, and the
    listing of the interpreter on it, to know where to look."""
    subprocess.run(
        [sys.executable, "-m", "regac", "build", adventure, DATABASE_6128,
         "-m", "cpc", "-b", "16k", "--defs", DEFS_6128],
        cwd=ROOT, check=True, capture_output=True,
    )
    listing = emulator.assemble(SOURCE_6128, listing=LISTING_6128)
    with open(BINARY_6128, "rb") as f:
        code = f.read()
    with open(DATABASE_6128, "rb") as f:
        image = f.read()
    resident = image[:Reader(image).resident_size]
    return cpc6128_disk(code, resident, banks_of(image), name="JUEGO"), listing


def room(session, at):
    low, high = session.read(at, 2, zone=session.RAM)
    return low | high << 8


def comes_to(session, at, wanted, glyphs, prompt, timeout):
    """Whether the player gets to room `wanted` and is asked for the next order
    before the time is up.  The asking matters as much as the room: the room
    changes the moment the order is obeyed, and then the new one is drawn and
    described, and the keyboard is not looked at while that goes on.  An order
    typed in the middle of it is lost, which is how this test first failed.

    And asked afresh: the last line has to be the question with nothing after
    it but the cursor.  The line the order was typed on starts with the same
    question, and taking that for an answer is how it failed the second time.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        if room(session, at) == wanted:
            lines = [line for line in screen(session, glyphs)
                     if line and line.strip("? ")]
            if lines and lines[-1].rstrip("? ") == prompt:
                return True
        time.sleep(0.5)
    return False


@needs_tools
def test_a_game_saved_and_loaded_at_the_keyboard(tmp_path):
    if not os.path.exists(VAJILLAS):
        if pytest is not None:
            pytest.skip("La guerra de las vajillas has to be in snapshots/")
        return
    with open(VAJILLAS, encoding="utf-8") as f:
        ddb = json.load(f)
    start = ddb["init_loc"]
    north = [e["dest"] for e in ddb["locations"][str(start)]["exits"]
             if e["dir"] == ddb["verbs"]["NORTE"]][0]
    image, listing = the_6128_disk_of(VAJILLAS)
    path = str(tmp_path / "juego.dsk")
    with open(path, "wb") as f:
        f.write(image)
    where = emulator.label_address(listing, "vm_location")
    glyphs = glyph_table(Database(ddb))

    session = emulator.Session(
        machine="CPC6128",
        extra=["--enable-dsk", "--dsk-file", path, "--dsk-persistent-writes"],
    )
    try:
        time.sleep(4.0)
        session.type_keys('run"juego' + chr(13))
        shown = wait_screen(session, glyphs, asking(ddb), timeout=120.0)
        assert any(asking(ddb) in line for line in shown if line), (
            f"the adventure never asked for an order: {shown}"
        )
        assert room(session, where) == start, "it did not start where it says"

        prompt = ddb["messages"]["240"].strip()     # the whole question
        session.type_keys("SAVE" + chr(13))
        # The motor, the head wound back to track nought, and four sectors:
        # a few seconds, during which the keyboard is not being looked at.
        # It has not moved, so asking is the only sign it is done.
        assert comes_to(session, where, start, glyphs, prompt, 60.0), (
            "it never asked for another order after SAVE"
        )
        session.type_keys("NORTE" + chr(13))
        assert comes_to(session, where, north, glyphs, prompt, 60.0), (
            f"NORTE did not take it from {start} to {north}: it is in "
            f"{room(session, where)}"
        )
        session.type_keys("LOAD" + chr(13))
        assert comes_to(session, where, start, glyphs, prompt, 60.0), (
            f"LOAD did not bring it back to {start}: it is in "
            f"{room(session, where)}"
        )
    finally:
        session.close()

    # And the game really is in the file on the disk, the room first.
    time.sleep(1.0)
    with open(path, "rb") as f:
        left = f.read()
    area = reader.data_area(left)
    saved = reader.contents(area, reader.directory(area)[SAVE])
    assert saved[0] | saved[1] << 8 == start, (
        f"the saved game on the disk does not start in room {start}: "
        f"{saved[:8].hex()}"
    )


if __name__ == "__main__":
    import pathlib
    import tempfile

    test_the_builder_tells_the_interpreter_where_its_game_goes()
    test_a_binary_without_the_three_bytes_is_refused()
    test_a_game_written_to_the_disk_comes_back(pathlib.Path(tempfile.mkdtemp()))
    test_a_disk_that_will_not_be_written_says_so(pathlib.Path(tempfile.mkdtemp()))
    test_a_build_nobody_told_where_to_save_says_so(
        pathlib.Path(tempfile.mkdtemp()))
    test_a_game_saved_and_loaded_at_the_keyboard(pathlib.Path(tempfile.mkdtemp()))
    print("a game saved on a 6128 comes back")
