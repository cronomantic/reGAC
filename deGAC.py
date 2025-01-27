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

import sys
import os
import argparse
import gettext
import json

SEEKPOS = 0x1C1B  # Number of bytes to skip in the file
MEM_BASE = 0x5C00  # First address loaded
MEM_SIZE = 0xA400  # Number of bytes to load from it

PUNCTUATION_ADDR = 0xA1E5  # 8 possible phrase endings
NOUNS_ADDR = 0xA51F  # Words that GAC recognises as nouns
ADVERBS_ADDR = 0xA521  # Words that GAC recognises as adverbs
OBJECTS_ADDR = 0xA523  # Table of objects
ROOMS_ADDR = 0xA525  # Table of locations
HPCS_ADDR = 0xA527  # High-priority conditions
LCS_ADDR = 0xA529  # Local conditions
LPCS_ADDR = 0xA52B  # Low-priority conditions
MESSAGES_ADDR = 0xA52D  # Message text
GRAPHICS_ADDR = 0xA52F  # Room graphics
TOKENS_ADDR = 0xA531  # Tokens used to store all forms of text
STARTROOM_ADDR = 0xA54D  # Initial room
VERBS_ADDR = 0xA54F  # Words that GAC recognises as verbs
DBASE_ADDR = 0xA1E5  # Start of database
MINRAM = 0x4000  # Minimum RAM address
MAXRAM = 0xFFFF  # Maximum RAM address


def dir_path(string):
    """_summary_

    Args:
        string (_type_): _description_

    Raises:
        NotADirectoryError: _description_

    Returns:
        _type_: _description_
    """
    if os.path.isdir(string):
        return string
    else:
        raise NotADirectoryError(string)


def file_path(string):
    """_summary_

    Args:
        string (_type_): _description_

    Raises:
        FileNotFoundError: _description_

    Returns:
        _type_: _description_
    """
    if os.path.isfile(string):
        return string
    else:
        raise FileNotFoundError(string)


def valid_path(string):
    """_summary_

    Args:
        string (_type_): _description_

    Raises:
        NotADirectoryError: _description_

    Returns:
        _type_: _description_
    """
    if os.access(os.path.dirname(string), os.W_OK):
        return string
    else:
        raise NotADirectoryError(string)


def load_file(file_path):
    file_array = []
    with open(file_path, "rb") as file:
        file.seek(SEEKPOS)
        file_array = file.read()

    if len(file_array) != (49179 - SEEKPOS):
        sys.exit("Invalid file size")

    sysmem = [0] * MEM_BASE
    sysmem += file_array[0:MEM_SIZE]
    return sysmem


def peek1(sysram, addr):
    if addr < MINRAM:
        return 0xFF
    return sysram[addr]


def peek2(sysram, addr):
    if addr < MINRAM:
        return 0xFF
    return sysram[addr] + 256 * sysram[addr + 1]


def find_token(sysram, token):
    addr = peek2(sysram, TOKENS_ADDR)
    while token > 0:
        length = peek1(sysram, addr)
        addr += 1
        addr += length
        token -= 1
    return addr + 1


def get_message_len(sysram, addr, length):
    msg = []
    for n in range(0, length, 2):
        w = peek2(sysram, addr + n)
        top = (w >> 14) & 3
        if top == 3:
            a = (w >> 11) & 7  # The punctuation ending
            b = peek1(sysram, PUNCTUATION_ADDR + a)  #
            if b == 0:
                return msg  # End of string
            a = w & 0xFF
            while a > 0:
                msg += [b]
                a -= 1
        else:
            token = find_token(sysram, w & 0x7FF)
            do_loop = True
            while do_loop:
                if top == 0:
                    a = peek1(sysram, token)
                    top = 1
                elif top == 1:
                    a = peek1(sysram, token)
                    if (a & 0x40) != 0:
                        a |= 0x20
                elif top == 2:
                    a = peek1(sysram, token)
                msg += [(a & 0x7F)]
                token += 1
                do_loop = (a & 0x80) == 0
            a = (w >> 11) & 7
            b = peek1(sysram, PUNCTUATION_ADDR + a)
            if b == 0:
                return msg  # End of string
            msg += [b]
    return msg


def get_messages(sysram):
    result = {}
    msg_addr = peek2(sysram, MESSAGES_ADDR)
    id = peek1(sysram, msg_addr)
    while id != 0:
        length = peek1(sysram, msg_addr + 1)
        msg_addr += 2
        msg = get_message_len(sysram, msg_addr, length)
        result[id] = bytearray(msg).decode("ascii")
        msg_addr += length
        id = peek1(sysram, msg_addr)
    return result


def get_objects(sysram):
    result = {}
    objects = peek2(sysram, OBJECTS_ADDR)
    id = peek1(sysram, objects)
    while id != 0:
        obj = {}
        length = peek1(sysram, objects + 1)
        objects += 2
        obj["weight"] = peek1(sysram, objects)
        obj["initial_loc"] = peek2(sysram, objects + 1)
        name = get_message_len(sysram, objects + 3, length - 3)
        obj["name"] = bytearray(name).decode("ascii")
        result[id] = obj
        objects += length
        id = peek1(sysram, objects)
    return result


def get_rooms(sysram):
    result = {}
    rooms = peek2(sysram, ROOMS_ADDR)
    id = peek2(sysram, rooms)
    while id != 0:
        room = {}
        length = peek2(sysram, rooms + 2)
        rooms += 4
        base = rooms
        room["graphic_id"] = peek2(sysram, rooms)
        rooms += 2
        exits = []
        while peek1(sysram, rooms) != 0:
            dir = peek1(sysram, rooms)
            dest = peek2(sysram, rooms + 1)
            exits.append({"dir": dir, "dest": dest})
            rooms += 3
        room["exits"] = exits
        rooms += 1
        desc = get_message_len(sysram, rooms, length - (rooms - base))
        room["desc"] = bytearray(desc).decode("ascii")
        result[id] = room
        rooms = base + length
        id = peek2(sysram, rooms)
    return result


def get_graphics(sysram):
    result = {}
    gfx = peek2(sysram, GRAPHICS_ADDR)
    id = peek2(sysram, gfx)
    while id != 0:
        length = peek2(sysram, gfx + 2)
        if length <= 4:  # No valid record has a length of <= 4, so bail out
            return result
        gfx += 4
        length -= 4
        base = gfx
        num_inst = peek1(sysram, gfx)
        gfx += 1
        inst = []
        while num_inst > 0:
            cmd = peek1(sysram, gfx)
            gfx += 1
            num_inst -= 1
            param = []
            param.append(peek1(sysram, gfx + 0))
            param.append(peek1(sysram, gfx + 1))
            param.append(peek1(sysram, gfx + 2))
            param.append(peek1(sysram, gfx + 3))
            if cmd == 0x01:
                inst.append(
                    (
                        "BORDER",
                        param[0],
                    )
                )
                gfx += 1
            elif cmd == 0x02:
                inst.append(
                    (
                        "PLOT",
                        param[0],
                        param[1],
                    )
                )
                gfx += 2
            elif cmd == 0x03:
                inst.append(
                    (
                        "ELLIPSE",
                        param[0],
                        param[1],
                        param[2],
                        param[3],
                    )
                )
                gfx += 4
            elif cmd == 0x04:
                inst.append(
                    (
                        "FILL",
                        param[0],
                        param[1],
                    )
                )
                gfx += 2
            elif cmd == 0x05:
                inst.append(
                    (
                        "BGFILL",
                        param[0],
                        param[1],
                    )
                )
                gfx += 2
            elif cmd == 0x06:
                inst.append(
                    (
                        "SHADE",
                        param[0],
                        param[1],
                    )
                )
                gfx += 2
            elif cmd == 0x07:
                inst.append(
                    (
                        "CALL",
                        param[1] * 256 + param[0],
                    )
                )
                gfx += 2
            elif cmd == 0x08:
                inst.append(
                    (
                        "RECT",
                        param[0],
                        param[1],
                        param[2],
                        param[3],
                    )
                )
                gfx += 4
            elif cmd == 0x09:
                inst.append(
                    (
                        "LINE",
                        param[0],
                        param[1],
                        param[2],
                        param[3],
                    )
                )
                gfx += 4
            elif cmd == 0x10:
                inst.append(
                    (
                        "INK",
                        param[0],
                    )
                )
                gfx += 1
            elif cmd == 0x11:
                inst.append(
                    (
                        "PAPER",
                        param[0],
                    )
                )
                gfx += 1
            elif cmd == 0x12:
                inst.append(
                    (
                        "BRIGHT",
                        param[0],
                    )
                )
                gfx += 1
            elif cmd == 0x13:
                inst.append(
                    (
                        "FLASH",
                        param[0],
                    )
                )
                gfx += 1
            else:
                inst.append(("UNKNOWN", cmd))
        result[id] = inst
        gfx = base + length
        id = peek2(sysram, gfx)
    return result


def get_cond(sysram, cond):
    result = []
    while True:
        bt = peek1(sysram, cond)
        if bt == 0:
            return (cond + 1, result)
        if (bt & 0x80) != 0:
            s0 = (bt & 0x7F) * 256 + peek1(sysram, cond + 1)
            result.append(("PUSH", s0))
            cond += 2
        else:
            cond += 1
            bt = bt & 0x3F
            if bt == 0x00:
                result.append(("OP0",))
                return (cond, result)
            elif bt == 0x01:
                result.append(("AND",))
            elif bt == 0x02:
                result.append(("OR",))
            elif bt == 0x03:
                result.append(("NOT",))
            elif bt == 0x04:
                result.append(("XOR",))
            elif bt == 0x05:
                result.append(("HOLD",))
            elif bt == 0x06:
                result.append(("GET",))
            elif bt == 0x07:
                result.append(("DROP",))
            elif bt == 0x08:
                result.append(("SWAP",))
            elif bt == 0x09:
                result.append(("TO",))
            elif bt == 0x0A:
                result.append(("OBJ",))
            elif bt == 0x0B:
                result.append(("SET",))
            elif bt == 0x0C:
                result.append(("RESE",))
            elif bt == 0x0D:
                result.append(("SET?",))
            elif bt == 0x0E:
                result.append(("RES?",))
            elif bt == 0x0F:
                result.append(("CSET",))
            elif bt == 0x10:
                result.append(("CTR",))
            elif bt == 0x11:
                result.append(("DECR",))
            elif bt == 0x12:
                result.append(("INCR",))
            elif bt == 0x13:
                result.append(("EQU?",))
            elif bt == 0x14:
                result.append(("DESC",))
            elif bt == 0x15:
                result.append(("LOOK",))
            elif bt == 0x16:
                result.append(("MESS",))
            elif bt == 0x17:
                result.append(("PRIN",))
            elif bt == 0x18:
                result.append(("RAND",))
            elif bt == 0x19:
                result.append(("<",))
            elif bt == 0x1A:
                result.append((">",))
            elif bt == 0x1B:
                result.append(("=",))
            elif bt == 0x1C:
                result.append(("SAVE",))
            elif bt == 0x1D:
                result.append(("LOAD",))
            elif bt == 0x1E:
                result.append(("HERE",))
            elif bt == 0x1F:
                result.append(("CARR",))
            elif bt == 0x20:
                result.append(("CARR",))
            elif bt == 0x21:
                result.append(("+",))
            elif bt == 0x22:
                result.append(("-",))
            elif bt == 0x23:
                result.append(("TURN",))
            elif bt == 0x24:
                result.append(("AT",))
            elif bt == 0x25:
                result.append(("BRIN",))
            elif bt == 0x26:
                result.append(("FIND",))
            elif bt == 0x27:
                result.append(("IN",))
            # 0x28 and 0x29 are no-ops */
            elif bt in (0x28, 0x29):
                result.append(("NOP",))
            elif bt == 0x2A:
                result.append(("OKAY",))
            elif bt == 0x2B:
                result.append(("WAIT",))
            elif bt == 0x2C:
                result.append(("QUIT",))
            elif bt == 0x2D:
                result.append(("EXIT",))
            elif bt == 0x2E:
                result.append(("ROOM",))
            elif bt == 0x2F:
                result.append(("NOUN",))
            elif bt == 0x30:
                result.append(("VERB",))
            elif bt == 0x31:
                result.append(("ADVE",))
            elif bt == 0x32:
                result.append(("GOTO",))
            elif bt == 0x33:
                result.append(("NO1",))
            elif bt == 0x34:
                result.append(("NO2",))
            elif bt == 0x35:
                result.append(("VBNO",))
            elif bt == 0x36:
                result.append(("LIST",))
            elif bt == 0x37:
                result.append(("PICT",))
            elif bt == 0x38:
                result.append(("TEXT",))
            elif bt == 0x39:
                result.append(("CONN",))
            elif bt == 0x3A:
                result.append(("WEIG",))
            elif bt == 0x3B:
                result.append(("WITH",))
            elif bt == 0x3C:
                result.append(("STRE",))
            elif bt == 0x3D:
                result.append(("LF",))
            elif bt == 0x3E:
                result.append(("IF",))
            elif bt == 0x3F:
                result.append(("END",))
            else:
                result.append(("UNKNOWN", bt))


def get_hpcs(sysram):
    cond = peek2(sysram, HPCS_ADDR)
    cond, result = get_cond(sysram, cond)
    return result


def get_lpcs(sysram):
    cond = peek2(sysram, LPCS_ADDR)
    cond, result = get_cond(sysram, cond)
    return result


def get_lcs(sysram):
    cond = peek2(sysram, LCS_ADDR)
    result = {}
    room = peek2(sysram, cond)
    while room != 0:
        cond, res = get_cond(sysram, cond + 2)
        result[room] = res
        room = peek2(sysram, cond)
    return result


def mirror_byte(c):
    o = 0
    for n in range(0, 8):
        o = o << 1
        o |= c & 1
        c = c >> 1
    return o & 0xFF


def get_font(sysram):
    font = []
    fontbase = peek2(sysram, 23606) + 256
    if fontbase < 0x5B00:  # Using ROM font
        return font
    for n in range(0, 96):
        for m in range(0, 8):
            font.append(peek1(sysram, fontbase + (8 * n) + m))
    return font


def get_words(sysram, addr):
    words = {}
    while True:
        word = []
        id = peek1(sysram, addr)
        if id == 0:
            return words
        addr += 1
        token = find_token(sysram, 0x7FF & peek2(sysram, addr))
        do_loop = True
        while do_loop:
            a = peek1(sysram, token)
            word.append(a & 0x7F)
            token += 1
            do_loop = (a & 0x80) == 0
        addr += 2
        word = bytearray(word).decode("ascii")
        words[word] = id


def get_verbs(sysram):
    addr = VERBS_ADDR
    return get_words(sysram, addr)


def get_nouns(sysram):
    addr = peek2(sysram, NOUNS_ADDR)
    return get_words(sysram, addr)


def get_adverbs(sysram):
    addr = peek2(sysram, ADVERBS_ADDR)
    return get_words(sysram, addr)


def get_database(sysram):
    database = {}

    font = get_font(sysram)
    verbs = get_verbs(sysram)
    nouns = get_nouns(sysram)
    adverbs = get_adverbs(sysram)
    messages = get_messages(sysram)
    objects = get_objects(sysram)
    rooms = get_rooms(sysram)
    hpcs = get_hpcs(sysram)
    lpcs = get_lpcs(sysram)
    lcs = get_lcs(sysram)
    gfx = get_graphics(sysram)

    database["font"] = [0 for x in range(8 * 32)] + font
    database["verbs"] = verbs
    database["nouns"] = {}
    database["pronouns"] = []
    for k, v in nouns.items():
        if v == 255:  # Pronoun detected
            database["pronouns"].append(v)
        else:
            database["nouns"][k] = v
    database["adverbs"] = adverbs
    database["messages"] = messages
    database["objects"] = objects
    database["locations"] = rooms
    database["hpcs"] = hpcs
    database["lpcs"] = lpcs
    database["lcs"] = lcs
    database["gfx"] = gfx
    database["model"] = "SPECTRUM"
    database["punctuation"] = list("\0 .,-!?:")
    database["separators"] = ["then", "and"]
    database["init_loc"] = peek2(sysram, STARTROOM_ADDR)
    database["no_objs_msg"] = "Nothing"

    print(f"font {len(font)}")
    print(f"verbs {len(verbs)}")
    print(f"nouns {len(nouns)}")
    print(f"adverbs {len(adverbs)}")
    print(f"messages {len(messages)}")
    print(f"objects  {len(objects)}")
    print(f"locations {len(rooms)}")
    print(f"hpcs {len(hpcs)}")
    print(f"lpcs {len(lpcs)}")
    print(f"lcs {len(lcs)}")
    print(f"gfx {len(gfx)}")

    return database


def main():
    if sys.version_info[0] < 3:  # Python 2
        sys.exit(_("ERROR: Invalid python version"))

    version = "1.0.0"
    program = "GAC decoder " + version
    exec = "deGAC"

    gettext.bindtextdomain(
        exec, os.path.join(os.path.abspath(os.path.dirname(__file__)), "locale")
    )
    gettext.textdomain(exec)
    _ = gettext.gettext

    arg_parser = argparse.ArgumentParser(sys.argv[0], description=program)
    arg_parser.add_argument(
        "input_path",
        type=file_path,
        metavar=_("INPUT_FILE"),
        help=_("sna file"),
    )
    arg_parser.add_argument(
        "output_path",
        type=valid_path,
        metavar=_("OUTPUT PATHS"),
        help=_("json database file"),
    )

    try:
        args = arg_parser.parse_args()
    except FileNotFoundError as f1:
        sys.exit(_("ERROR: File not found:") + f"{f1}")
    except NotADirectoryError as f2:
        sys.exit(_("ERROR: Not a valid path:") + f"{f2}")

    print(f"Processing file {args.input_path}...")

    sysram = load_file(args.input_path)

    # The 8 bytes that should be at PUNCTUATION. UnGAC uses this as a magic number  to detect a GAC database.
    punc_magic = list("\0 .,-!?:".encode(encoding="ascii"))
    if (sysram[PUNCTUATION_ADDR : PUNCTUATION_ADDR + len(punc_magic)]) != punc_magic:
        sys.exit("Magic characters not found")

    ddb = get_database(sysram)
    ddb_json = json.dumps(ddb)

    with open(args.output_path, "w") as file:
        file.write(ddb_json)


if __name__ == "__main__":
    main()
