# MIT License
#
# Copyright (c) 2025 Cronomantic
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
"""ReGAC: convert between the JSON database and the editable source format."""

import argparse
import json
import os
import sys

from .devices import DEVICES, device_for, make
from .gfx import Renderer
from .png import save_picture
from .srcgen import generate
from .srcparse import SourceError, parse

VERSION = "0.1.0"


def read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path, ddb):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(ddb, f, indent=1, ensure_ascii=False)


def cmd_decompile(args):
    ddb = read_json(args.input)
    name = os.path.splitext(os.path.basename(args.input))[0]
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(generate(ddb, name))
    print(f"{args.input} -> {args.output}")


def cmd_compile(args):
    name = os.path.basename(args.input)
    with open(args.input, encoding="utf-8") as f:
        source = f.read()
    try:
        ddb = parse(source, name)
    except SourceError as e:
        sys.exit(f"ERROR: {e}")
    write_json(args.output, ddb)
    print(f"{args.input} -> {args.output}")


def cmd_check(args):
    """Decompile and recompile a database, reporting any loss."""
    original = read_json(args.input)
    name = os.path.basename(args.input)
    try:
        rebuilt = json.loads(json.dumps(parse(generate(original, name), name)))
    except SourceError as e:
        sys.exit(f"ERROR: {e}")
    if rebuilt == original:
        print(f"{name}: round trip exact")
        return
    differing = sorted(
        k for k in set(original) | set(rebuilt) if original.get(k) != rebuilt.get(k)
    )
    sys.exit(f"{name}: round trip differs in {', '.join(differing)}")


def cmd_render(args):
    """Draw one picture of an adventure, or all of them, as PNG files."""
    gfx = read_json(args.input)["gfx"]
    machine = args.machine
    if args.picture is not None:
        wanted = [str(args.picture)]
    else:
        wanted = sorted(gfx, key=int)
    if not os.path.isdir(args.output) and len(wanted) > 1:
        sys.exit(f"ERROR: {args.output} must be a directory for more than one picture")
    for pid in wanted:
        if pid not in gfx:
            sys.exit(f"ERROR: there is no picture {pid}")
        picture = Renderer(gfx, device_for(machine, gfx, pid)).run(int(pid))
        if os.path.isdir(args.output):
            path = os.path.join(args.output, f"{pid}.png")
        else:
            path = args.output
        save_picture(path, picture, scale=args.scale)
        print(f"picture {pid} -> {path}")


def cmd_checkgfx(args):
    """Compare the pictures on a target machine against the Spectrum.

    A fill spreads until the outlines stop it, so a change of resolution can
    let one escape through a gap the scaling opened, or strand its starting
    point on the wrong side of a line.  Comparing how much of the screen each
    fill reaches on each machine catches exactly that.
    """
    gfx = read_json(args.input)["gfx"]
    name = os.path.basename(args.input)
    suspect = 0
    for pid in sorted(gfx, key=int):
        reference = Renderer(gfx, make("spectrum"))
        reference.run(int(pid))
        target = Renderer(gfx, device_for(args.machine, gfx, pid))
        target.run(int(pid))
        ref_area = reference.device.width * reference.device.height
        out_area = target.device.width * target.device.height
        if len(reference.fill_coverage) != len(target.fill_coverage):
            print(f"  picture {pid}: the two runs filled a different number of times")
            suspect += 1
            continue
        for n, (a, b) in enumerate(
            zip(reference.fill_coverage, target.fill_coverage), 1
        ):
            share_a = a / ref_area
            share_b = b / out_area
            if abs(share_a - share_b) > args.tolerance:
                print(
                    f"  picture {pid}, fill {n}: covers {share_a:.0%} of the screen "
                    f"on the spectrum but {share_b:.0%} on the {args.machine}"
                )
                suspect += 1
    if suspect:
        sys.exit(f"{name}: {suspect} fills differ on the {args.machine}")
    print(f"{name}: every fill covers the same ground on the {args.machine}")


def main():
    parser = argparse.ArgumentParser("regac", description=f"ReGAC {VERSION}")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("decompile", help="JSON database -> .gac source")
    p.add_argument("input", help="JSON database")
    p.add_argument("output", help="source file to write")
    p.set_defaults(func=cmd_decompile)

    p = sub.add_parser("compile", help=".gac source -> JSON database")
    p.add_argument("input", help="source file")
    p.add_argument("output", help="JSON database to write")
    p.set_defaults(func=cmd_compile)

    p = sub.add_parser("render", help="draw the pictures of an adventure as PNG")
    p.add_argument("input", help="JSON database")
    p.add_argument("output", help="PNG file, or a directory for several")
    p.add_argument("-p", "--picture", type=int, help="one picture id (default: all)")
    p.add_argument("-s", "--scale", type=int, default=2, help="pixel scale")
    p.add_argument(
        "-m",
        "--machine",
        default="spectrum",
        choices=sorted(DEVICES),
        help="which machine to draw for (default: spectrum)",
    )
    p.set_defaults(func=cmd_render)

    p = sub.add_parser(
        "checkgfx", help="compare the pictures on a machine against the Spectrum"
    )
    p.add_argument("input", help="JSON database")
    p.add_argument("-m", "--machine", required=True, choices=sorted(DEVICES))
    p.add_argument(
        "-t",
        "--tolerance",
        type=float,
        default=0.05,
        help="how much of the screen a fill may differ by (default: 0.05)",
    )
    p.set_defaults(func=cmd_checkgfx)

    p = sub.add_parser("check", help="verify that a database survives a round trip")
    p.add_argument("input", help="JSON database")
    p.set_defaults(func=cmd_check)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
