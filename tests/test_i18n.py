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
"""What the tools say, in English or in Spanish: see regac/i18n.py.

Decided by the user: in the language of the system.  What is held here is
that every message the code says through `_` has its Spanish, with the same
holes, and that the catalogue has nothing nobody says any more; and that the
language is chosen the way i18n.py says."""

import ast
import os
import string
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from regac import i18n  # noqa: E402
from regac.es import SAID  # noqa: E402

PROGRAMS = ["runGAC.py", "runGAC_pygame.py", "deGAC.py", "disk.py", "grab.py"]


def sources():
    folder = os.path.join(ROOT, "regac")
    for name in sorted(os.listdir(folder)):
        if name.endswith(".py"):
            yield os.path.join(folder, name)
    for name in PROGRAMS:
        yield os.path.join(ROOT, name)


def said_in_code():
    """Every message given to `_` as it is written: {message: where}."""
    out = {}
    for path in sources():
        with open(path, encoding="utf-8") as f:
            tree = ast.parse(f.read(), path)
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id in ("_", "N_") and node.args
                    and isinstance(node.args[0], ast.Constant)
                    and isinstance(node.args[0].value, str)):
                out.setdefault(node.args[0].value,
                               f"{os.path.relpath(path, ROOT)}:{node.lineno}")
    return out


def holes(text):
    return {name for _, name, _, _ in string.Formatter().parse(text) if name}


def test_every_message_has_its_spanish():
    missing = {m: where for m, where in said_in_code().items() if m not in SAID}
    assert not missing, "no Spanish for:\n" + "\n".join(
        f"  {where}: {m!r}" for m, where in sorted(missing.items(),
                                                   key=lambda x: x[1]))


def test_the_catalogue_has_nothing_nobody_says():
    left = sorted(set(SAID) - set(said_in_code()))
    assert not left, f"said by nobody any more: {left}"


def test_the_holes_are_the_same_in_both():
    for english, spanish in SAID.items():
        assert holes(english) == holes(spanish), (english, spanish)


def test_the_language_is_the_one_asked_for_or_the_systems(monkeypatch):
    for asked, wanted in (("es", "es"), ("ES_es", "es"), ("en", "en")):
        monkeypatch.setenv("REGAC_LANG", asked)
        monkeypatch.setattr(i18n, "_chosen", None)
        assert i18n.language() == wanted
    monkeypatch.delenv("REGAC_LANG")
    monkeypatch.setattr(i18n, "_chosen", None)
    monkeypatch.setattr(i18n.sys, "platform", "linux")
    for variables, wanted in (({"LANG": "es_ES.UTF-8"}, "es"),
                              ({"LANG": "de_DE.UTF-8"}, "en"),
                              ({"LANGUAGE": "en", "LANG": "es_ES"}, "en"),
                              ({}, "en")):
        for name in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
            monkeypatch.delenv(name, raising=False)
        for name, value in variables.items():
            monkeypatch.setenv(name, value)
        assert i18n.system_language() == wanted, variables


def test_a_tool_speaks_spanish_when_asked():
    said = subprocess.run(
        [sys.executable, "-m", "regac", "render", "nada.json", "salida.png"],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
        env=dict(os.environ, REGAC_LANG="es", PYTHONIOENCODING="utf-8"))
    help_said = subprocess.run(
        [sys.executable, "-m", "regac", "-h"], cwd=ROOT, capture_output=True,
        text=True, encoding="utf-8",
        env=dict(os.environ, REGAC_LANG="es", PYTHONIOENCODING="utf-8"))
    assert "fuente" in help_said.stdout, help_said.stdout
    assert said.returncode != 0


def test_no_function_that_speaks_hides_the_word_it_speaks_with():
    """`_` is also the name Python gives to what is thrown away -- `key, _,
    value = ...` -- and a function that does that and then says something
    calls the thing it threw away.  In a comprehension it is harmless, as it
    has a scope of its own; in the body of the function it is not."""
    found = []
    for path in sources():
        with open(path, encoding="utf-8") as f:
            tree = ast.parse(f.read(), path)
        for function in ast.walk(tree):
            if not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            stores, calls = False, False
            todo = list(function.body)
            while todo:
                node = todo.pop()
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                                     ast.Lambda, ast.ListComp, ast.SetComp,
                                     ast.DictComp, ast.GeneratorExp)):
                    continue            # a scope of its own
                if (isinstance(node, ast.Name) and node.id == "_"
                        and isinstance(node.ctx, ast.Store)):
                    stores = True
                if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                        and node.func.id == "_"):
                    calls = True
                todo.extend(ast.iter_child_nodes(node))
            if stores and calls:
                found.append(f"{os.path.relpath(path, ROOT)}:{function.lineno} "
                             f"{function.name}")
    assert not found, "these throw `_` away and then speak with it: " + ", ".join(found)
