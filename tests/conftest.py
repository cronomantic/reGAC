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
"""Running the tests several at a time.

Almost every test here drives a real emulator, so the suite is not slow
because of what it computes: it is slow because it waits.  That is exactly
the kind of work that goes several at a time, and the only two things in the
way are shared:

  - **the emulator's port.**  One ZEsarUX at a time answers on 10000, and two
    sessions on one port talk to the same machine.  `emulator.py` gives each
    worker a port of its own, taken from the name xdist gives it.
  - **what the assembler writes.**  Two tests that build `z80/spectrum/game.sna`
    would tread on each other's build halfway through it.  So the tests that
    write the same files are put in a group of their own here, and xdist's
    `--dist loadgroup` keeps every group inside one worker.  Tests that build
    nothing -- the compiler's, the source's, the formats' -- carry no group
    and go wherever there is room.

The map below is by what a test builds and not by what it is about, which is
why `test_markers_z80` and `test_tape_z80` sit together: both write
`z80/spectrum/game.*`.

And a handful of tests **measure time** -- how long a key takes to repeat, how
long an order holds the machine -- and a busy machine makes them fail.  Those
are marked `serial` and left out of the parallel run:

    pytest -n 4 --dist loadgroup -m "not serial"     # the bulk of it
    pytest -m serial                                 # and these on their own
"""

import pytest

# What each test module builds, so that the ones that build the same thing
# stay in the same worker.  A module that is not here builds nothing of its
# own.
GROUPS = {
    "spectrum-game": [
        "test_example", "test_game_z80", "test_markers_z80", "test_opcodes_z80",
        # it builds the same game and plays it beside the original's own
        "test_mirror_z80",
        "test_statements_z80", "test_latin", "test_spectrum",
        "test_media_plus3", "test_media_music_plus3", "test_tape_z80",
        "test_tape_music_z80", "test_textmode_z80", "test_game_music_z80",
        "test_music_source_z80",
        # it lays text out through test_markers_z80's own game
        "test_wrapping_z80",
    ],
    "spectrum-conditions": ["test_conditions_z80", "test_ink_z80"],
    "spectrum-conditions-music": ["test_music_ops_z80"],
    "spectrum-picture": ["test_all_pictures", "test_graphics_z80"],
    "spectrum-parser": ["test_parser_z80"],
    "spectrum-beep": ["test_beep_z80"],
    "spectrum-music": ["test_music_z80"],
    "spectrum-sound": ["test_sound_z80"],
    "spectrum-tunes": ["test_tunes_z80"],
    "spectrum-tape": ["test_save_z80"],
    "cpc-game": [
        "test_game_cpc", "test_game_music_cpc", "test_low_cpc",
        "test_textmode_cpc", "test_media_cpc", "test_media_music_cpc",
        # it saves and loads from the 6128 build, which test_media_cpc makes
        "test_save_cpc",
    ],
    "cpc-picture": ["test_all_pictures_cpc", "test_graphics_cpc"],
    "cpc-text": ["test_keyboard_cpc", "test_tape_cpc", "test_text_cpc"],
    "cpc-sound": ["test_sound_cpc"],
    "cpc-music": ["test_music_cpc"],
    "msx-game": ["test_game_msx", "test_game_music_msx", "test_tape_msx"],
    "msx-picture": ["test_all_pictures_msx", "test_graphics_msx"],
    "msx-text": ["test_keyboard_msx"],
    "msx-save": ["test_save_msx"],
    "msx-music": ["test_music_msx"],
    "next-game": ["test_game_next", "test_game_music_next", "test_textmode_next"],
    "next-picture": ["test_graphics_next"],
    "next-music": ["test_music_next"],
    "next-save": ["test_save_next"],
    "pcw-game": [
        "test_game_pcw", "test_textmode_pcw", "test_screen_pcw",
        "test_save_pcw", "test_boot_pcw",
    ],
    "pcw-text": ["test_keyboard_pcw", "test_text_pcw"],
    "pcw-picture": ["test_graphics_pcw"],
}

GROUP_OF = {module: group for group, modules in GROUPS.items()
            for module in modules}

# The ones that measure time rather than what came out.  Their own comments
# say it: a machine busy with the rest of the suite holds a key down a second
# too long, and the letter comes out twice.
SERIAL_MODULES = {
    "test_statements_z80", "test_keyboard_cpc", "test_keyboard_msx",
    "test_keyboard_pcw",
    # these load their game from a tape, which happens in the machine's own
    # time and not in ours: shared four ways they never get there, and they
    # were the only two that kept falling over in a parallel run while
    # passing on their own
    "test_game_cpc", "test_game_music_cpc", "test_tape_z80",
    # two emulators at once, typed at in turn: it holds one machine while it
    # types at the other, and a busy host would drop the letters anyway
    "test_mirror_z80",
}
SERIAL_TESTS = {"test_it_keeps_up_with_quick_typing_and_repeats_a_held_key"}


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "serial: measures time, so it runs on its own"
    )


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(items):
    for item in items:
        module = item.module.__name__.rsplit(".", 1)[-1] if item.module else ""
        group = GROUP_OF.get(module)
        if group:
            item.add_marker(pytest.mark.xdist_group(group))
        if module in SERIAL_MODULES or item.name in SERIAL_TESTS:
            item.add_marker(pytest.mark.serial)
