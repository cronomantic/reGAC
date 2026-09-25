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
"""What the tools say, in English or in Spanish.

Decided by the user: the tools speak the language of the system, English or
Spanish.  Every message is written in the code in English, through `_`, with
its numbers and names as named holes -- `_("there is no picture {n}", n=12)`
-- and the English is what is looked up in the Spanish catalogue, es.py.  A
message the catalogue has not got comes out in English, and a test makes sure
there is none.

Which language: REGAC_LANG, `es` or `en`, if it is set; otherwise the
system's -- on Windows the language of its interface, elsewhere LANGUAGE,
LC_ALL, LC_MESSAGES and LANG, the way gettext looks at them -- and Spanish if
that is Spanish, English for anything else.
"""

import os
import sys

SPANISH = "es"
ENGLISH = "en"

_chosen = None


def system_language():
    """Spanish or English, as the system is set up."""
    if sys.platform == "win32":
        try:
            import ctypes

            primary = ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0x3FF
            return SPANISH if primary == 0x0A else ENGLISH
        except (AttributeError, OSError):
            pass
    for name in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        said = os.environ.get(name)
        if said:
            return SPANISH if said.lower().startswith("es") else ENGLISH
    return ENGLISH


def language():
    """The language the tools speak now."""
    global _chosen
    if _chosen is None:
        asked = os.environ.get("REGAC_LANG", "").lower()[:2]
        _chosen = asked if asked in (SPANISH, ENGLISH) else system_language()
    return _chosen


def speak(which):
    """Speak `which` from now on, whatever the system says: for the tests."""
    global _chosen
    _chosen = which


def N_(message):
    """A message marked for the catalogue where it is written, and said with
    `_` where it is used: for the ones kept in a table."""
    return message


def _(message, /, **holes):
    """A message in the language of the tools, its holes filled in."""
    if language() == SPANISH:
        from .es import SAID

        message = SAID.get(message, message)
    return message.format(**holes) if holes else message


# What argparse says of its own -- the headings of the help, and its errors --
# which it asks gettext for.  Written as argparse has them, holes and all.
ARGPARSE = (
    N_("usage: "),
    N_("positional arguments"),
    N_("options"),
    N_("show this help message and exit"),
    N_(" (default: %(default)s)"),
    N_("%(prog)s: error: %(message)s\n"),
    N_("argument %(argument_name)s: %(message)s"),
    N_("the following arguments are required: %s"),
    N_("one of the arguments %s is required"),
    N_("unrecognized arguments: %s"),
    N_("not allowed with argument %s"),
    N_("ambiguous option: %(option)s could match %(matches)s"),
    N_("expected one argument"),
    N_("expected at most one argument"),
    N_("expected at least one argument"),
    N_("invalid %(type)s value: %(value)r"),
    N_("invalid choice: %(value)r (choose from %(choices)s)"),
)


def argparse_speaks():
    """Have argparse say its own words through `_` too, from now on."""
    import argparse

    argparse._ = lambda message: _(message)
