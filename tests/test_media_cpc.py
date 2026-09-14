"""The disk and the tape an Amstrad really loads.

Three checks, cheapest first.  The records we write are compared against the
ones on a real tape, rebuilt from their own fields, which pins the format down
to the byte without turning anything on.  Then a disk is put in a 6128 and
started the way a person would, with RUN and the name.  And then the tape,
which is the same thing but takes minutes of tape time, so it only runs when
asked for.
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
from regac import cdt  # noqa: E402
from regac.binary import Database  # noqa: E402
from regac.media import cpc_disk, cpc_tape  # noqa: E402
from test_game_cpc import glyph_table, wait_screen  # noqa: E402

CPC = os.path.join(ROOT, "z80", "cpc")
SOURCE = os.path.join(CPC, "game.asm")
DATABASE = os.path.join(CPC, "game.rgac")
BINARY = os.path.join(CPC, "game.bin")
LISTING = os.path.join(CPC, "game.lst")
ADVENTURE = os.path.join(ROOT, "snapshots", "megacorp2.json")
REAL_TAPE = os.path.join(ROOT, "juegos", "megacorp_ams.zip")

if pytest is not None:
    needs_tools = pytest.mark.skipif(
        not emulator.available() or not os.path.exists(ADVENTURE),
        reason="sjasmplus and ZEsarUX must be in tools/, with a decompiled adventure",
    )
    needs_real_tape = pytest.mark.skipif(
        not os.path.exists(REAL_TAPE),
        reason="the Amstrad tape of Megacorp must be in juegos/",
    )
    is_slow = pytest.mark.skipif(
        not os.environ.get("REGAC_SLOW"),
        reason="set REGAC_SLOW=1: a tape takes tape time",
    )
else:

    def needs_tools(func):
        return func

    needs_real_tape = is_slow = needs_tools


def records(image):
    """Every record of a tape image, in order, as the bytes on the tape."""
    assert image[:7] == b"ZXTape!"
    at, found = 10, []
    while at < len(image):
        kind, at = image[at], at + 1
        if kind == 0x11:
            head, at = image[at:at + 0x12], at + 0x12
            length = head[0x0F] | head[0x10] << 8 | head[0x11] << 16
            found.append(image[at:at + length])
            at += length
        elif kind == 0x20:
            at += 2
        elif kind == 0x30:
            at += 1 + image[at]
        else:
            break
    return found


def built():
    """The interpreter with an adventure in it, as the assembler leaves it."""
    subprocess.run(
        [sys.executable, "-m", "regac", "build", ADVENTURE, DATABASE, "-m", "cpc"],
        cwd=ROOT, check=True, capture_output=True,
    )
    emulator.assemble(SOURCE, listing=LISTING)
    with open(BINARY, "rb") as f:
        return f.read()


def asking(ddb):
    """What the adventure says when it wants an order."""
    return ddb["messages"]["240"].strip()[:3]


@needs_real_tape
def test_our_records_are_the_ones_a_real_tape_carries():
    """Megacorp's own loader, taken off its tape and written again from its
    own fields, comes out the same byte for byte: the name, the block, the
    checksums and the tail."""
    import zipfile

    with zipfile.ZipFile(REAL_TAPE) as archive:
        inside = [n for n in archive.namelist() if n.lower().endswith(".cdt")][0]
        theirs = records(archive.read(inside))
    header, data = theirs[0], theirs[1]
    declared = header[1:65]
    name = declared[:16].rstrip(b"\x00").decode("ascii")
    length = declared[19] | declared[20] << 8
    load = declared[21] | declared[22] << 8
    payload = data[1:1 + length]

    file = cdt.File(name, payload, kind=declared[18], load=load)
    assert cdt.record(cdt.HEADER_SYNC,
                      cdt.header(file, 1, 0, length, True)) == header
    assert cdt.record(cdt.DATA_SYNC, payload) == data


@needs_tools
def test_the_disk_starts_the_game(tmp_path):
    with open(ADVENTURE, encoding="utf-8") as f:
        ddb = json.load(f)
    path = str(tmp_path / "juego.dsk")
    with open(path, "wb") as f:
        f.write(cpc_disk(built()))
    glyphs = glyph_table(Database(ddb))

    session = emulator.Session(
        machine="CPC6128", extra=["--enable-dsk", "--dsk-file", path]
    )
    try:
        time.sleep(4.0)
        session.type_keys('run"juego' + chr(13))
        screen = wait_screen(session, glyphs, asking(ddb), timeout=90.0)
    finally:
        session.close()
    assert any(asking(ddb) in line for line in screen if line), (
        f"the adventure never got going: {screen}"
    )


@is_slow
@needs_tools
def test_the_tape_starts_the_game(tmp_path):
    """The same, off a tape, which is a quarter of an hour: twenty eight
    kilobytes at the speed the firmware reads them, on an emulator that runs
    at about half the speed of the machine.  Measured at ten and a half
    minutes, so the wait is fifteen."""
    with open(ADVENTURE, encoding="utf-8") as f:
        ddb = json.load(f)
    path = str(tmp_path / "juego.cdt")
    with open(path, "wb") as f:
        f.write(cpc_tape(built()))
    glyphs = glyph_table(Database(ddb))

    session = emulator.Session(
        machine="CPC464", extra=["--fastautoload", "--simulaterealloadfast"]
    )
    try:
        time.sleep(2.5)
        session.command("smartload " + path)
        screen = wait_screen(session, glyphs, asking(ddb), timeout=900.0)
    finally:
        session.close()
    assert any(asking(ddb) in line for line in screen if line), (
        f"the adventure never got going: {screen}"
    )


if __name__ == "__main__":
    test_our_records_are_the_ones_a_real_tape_carries()
    print("our records are the ones a real tape carries")
