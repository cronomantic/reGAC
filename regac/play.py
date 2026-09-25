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
"""An adventure played from a file of orders, to say whether it can be won.

`regac play aventura.gac solucion.txt` types the orders of the file, one a
line, at the interpreter in Python -- runGAC.py, the same one `python
runGAC.py` plays by hand -- and writes out what the game said.  It says at the
end whether the game ended, or whether the orders ran out with it still
asking; and with `--expect` whether it said what winning says.  So the
solution of an adventure is kept beside it and played after every change,
which is a test an author can run without a machine or an emulator.

A line of the file that is empty, or starts with `;`, is not an order.  A HOLD
waits for nothing, and a question the game asks -- QUIT's -- is answered by
the next line, as a player at the keyboard would.
"""

import contextlib
import importlib.util
import io
import os

from .i18n import _


def interpreter_class():
    """runGAC is a program rather than a module, beside this package, so it
    is loaded by hand."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    spec = importlib.util.spec_from_file_location(
        "rungac", os.path.join(root, "runGAC.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.GAC_Interpreter


def orders_of(text):
    return [line.strip() for line in text.splitlines()
            if line.strip() and not line.strip().startswith(";")]


def play(ddb, orders):
    """Play the orders and give back (whether the game ended, what it said)."""
    base = interpreter_class()
    ran_out = []

    class Scripted(base):
        def input(self):
            self.line_remain = self.width
            if not orders:
                ran_out.append(True)
                return None
            order = orders.pop(0)
            print(order)                    # the echo a keyboard would give
            return order

        def wait_key_or_timeout(self, timeout_frames):
            return True

    orders = list(orders)
    said = io.StringIO()
    with contextlib.redirect_stdout(said):
        game = Scripted(ddb)
        if not game.start_adventure():
            raise ValueError(_("the interpreter would not start this "
                               "adventure"))
        while not game.main_loop():
            pass
        if not ran_out:
            game.tell_the_score()
    return not ran_out, said.getvalue()
