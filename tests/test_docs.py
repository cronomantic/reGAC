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
"""The documentation for people who use reGAC, in Spanish and in English.

Decided by the user: the README, the manual, the language, the source format
and the project file in both.  What is checked is what a reader trips on: a
link that goes nowhere, and a page in one language without the way to the
other."""

import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Each page and the one that says the same in the other language.
PAIRS = [
    ("README.md", "LEEME.md"),
    ("doc/en/manual.md", "doc/manual.md"),
    ("doc/en/gac.md", "doc/gac.md"),
    ("doc/en/source-format.md", "doc/formato-fuente.md"),
    ("doc/en/project.md", "doc/proyecto.md"),
]
LINK = re.compile(r"\]\(([^)#\s]+)(?:#[^)]*)?\)")


def links_of(page):
    with open(os.path.join(ROOT, page), encoding="utf-8") as f:
        text = f.read()
    return [target for target in LINK.findall(text)
            if not target.startswith(("http://", "https://"))]


def test_no_link_goes_nowhere():
    for pair in PAIRS:
        for page in pair:
            folder = os.path.dirname(os.path.join(ROOT, page))
            for target in links_of(page):
                assert os.path.exists(os.path.normpath(os.path.join(folder, target))), (
                    f"{page} links to {target}, which is not there")


def test_every_page_leads_to_the_other_language():
    for english, spanish in PAIRS:
        for page, other in ((english, spanish), (spanish, english)):
            folder = os.path.dirname(os.path.join(ROOT, page))
            reached = {os.path.normpath(os.path.join(folder, t)) for t in links_of(page)}
            assert os.path.normpath(os.path.join(ROOT, other)) in reached, (
                f"{page} does not lead to {other}")
