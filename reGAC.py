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
import random
import platform

if platform.system() == "Windows":
    import time
    import msvcrt
else:
    from select import select


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


class IoInterfaceCallbackGAC:
    def __init__(self):
        self.width = 0
        self.separators = []

    def print(self, string):
        print(string)

    def input(self):
        return input()

    def set_width(self, w):
        self.width = w

    def set_separators(self, l):
        self.separators += l


class DatabaseGAC:

    # Standard message numbers
    ASK = 240
    CANTDO = 241
    NOTUNDERSTAND = 242
    RESTART = 243
    YOUSURE = 244
    ALREADYHAVE = 245
    DONTHAVE = 246
    CANTSEE = 247
    TOOMUCH = 248
    YOURSCORE = 249
    YOUTOOK = 250
    ITSDARK = 251
    CANTFIND = 252
    OBJHERE = 253
    OKAY = 254
    TURNS = 255

    NOTHING_LOC = 0
    CARRIED_LOC = 255

    TURN_CNT_H = 127
    TURN_CNT_L = 126
    SCORE_CNT = 0

    FLAG_ROOM_DESC = 0
    LIGHTING_FLAG = 1
    LAMP_FLAG = 2
    SCORE_DIS_FLAG = 3

    def __init__(self, ddb, io):
        self.ddb = ddb
        self.counters = [0 for x in range(0, 128)]
        self.flags = [False for x in range(0, 256)]
        self.current_loc = 0
        self.stack = []
        self.io = io
        self.font = None
        self.verbs = None
        self.nouns = None
        self.adverbs = None
        self.messages = None
        self.objects = None
        self.locations = None
        self.hpcs = None
        self.lpcs = None
        self.lcs = None
        self.model = None
        self.gfx = None
        self.separators = None
        self.pronouns = None
        self.punctuation = None
        self.init_loc = 0
        self.verb = 0
        self.adverb = 0
        self.noun1 = 0
        self.noun2 = 0
        self.max_weight = 0
        self.ready = False
        self.show_exits = False
        self.old_noun = 0

    def __wait_key_or_timeout(self, timeout_frames):
        timeout = timeout_frames / 50
        if platform.system() == "Windows":
            start_time = time.time()
            while True:
                if msvcrt.kbhit():
                    inp = msvcrt.getch()
                    break
                elif time.time() - start_time > timeout:
                    break
        else:
            rlist, wlist, xlist = select([sys.stdin], [], [], timeout)

    def __check_ddb(ddb):
        default_keys = set(
            [
                "font",
                "verbs",
                "nouns",
                "adverbs",
                "messages",
                "objects",
                "locations",
                "hpcs",
                "lpcs",
                "lcs",
                "model",
                "gfx",
                "separators",
                "pronouns",
                "punctuation",
                "init_loc",
            ]
        )
        if not isinstance(ddb, dict):
            return False
        if set(ddb.keys()) != default_keys:
            return False
        for k in default_keys:
            v = ddb[k]
            if k == "font":
                if isinstance(v, list):
                    if len(v) > 0:
                        if len(v) != 768:
                            return False
                        elif not isinstance(v[0], int):
                            return False
                        elif not all(type(x) == type(v[0]) for x in v):
                            return False
                else:
                    return False
            elif k == "verbs":
                if isinstance(v, dict):
                    for k2, v2 in v.items():
                        if not isinstance(k2, str) or not isinstance(v2, int):
                            return False
                else:
                    return False
            elif k == "nouns":
                if isinstance(v, dict):
                    for k2, v2 in v.items():
                        if not isinstance(k2, str) or not isinstance(v2, int):
                            return False
                else:
                    return False
            elif k == "adverbs":
                if isinstance(v, dict):
                    for k2, v2 in v.items():
                        if not isinstance(k2, str) or not isinstance(v2, int):
                            return False
                else:
                    return False
            elif k == "messages":
                if isinstance(v, dict):
                    for k2, v2 in v.items():
                        if (
                            not isinstance(k2, str)
                            or not isinstance(v2, str)
                            or not k2.isnumeric()
                        ):
                            return False
                else:
                    return False
            elif k == "objects":
                if isinstance(v, dict):
                    for k2, v2 in v.items():
                        if (
                            not isinstance(k2, str)
                            or not isinstance(v2, dict)
                            or not k2.isnumeric()
                        ):
                            return False
                        else:
                            for k3, v3 in v2.items():
                                if k3 not in set(["weight", "initial_loc", "name"]):
                                    return False
                                elif k3 == "weight":
                                    if not isinstance(v3, int):
                                        return False
                                elif k3 == "initial_loc":
                                    if not isinstance(v3, int):
                                        return False
                                elif k3 == "name":
                                    if not isinstance(v3, str):
                                        return False
                                else:
                                    return False
                else:
                    return False
            elif k == "locations":
                if isinstance(v, dict):
                    for k2, v2 in v.items():
                        if (
                            not isinstance(k2, str)
                            or not isinstance(v2, dict)
                            or not k2.isnumeric()
                        ):
                            return False
                        else:
                            for k3, v3 in v2.items():
                                if k3 not in set(["graphic_id", "desc", "exits"]):
                                    return False
                                elif k3 == "graphic_id":
                                    if not isinstance(v3, int):
                                        return False
                                elif k3 == "desc":
                                    if not isinstance(v3, str):
                                        return False
                                elif k3 == "exits":
                                    if not isinstance(v3, list):
                                        return False
                                    for v4 in v3:
                                        if not isinstance(v4, dict):
                                            return False
                                        for k5, v5 in v4.items():
                                            if k5 not in set(["dir", "dest"]):
                                                return False
                                            elif k5 == "dir":
                                                if not isinstance(v5, int):
                                                    return False
                                            elif k5 == "dest":
                                                if not isinstance(v5, int):
                                                    return False
                                            else:
                                                return False
                                else:
                                    return False
                else:
                    return False
            elif k == "hpcs":
                if not isinstance(v, list) or not all([isinstance(x, list) for x in v]):
                    return False
            elif k == "lpcs":
                if not isinstance(v, list) or not all([isinstance(x, list) for x in v]):
                    return False
            elif k == "lcs":
                if isinstance(v, dict):
                    for k2, v2 in v.items():
                        if (
                            not isinstance(k2, str)
                            or not isinstance(v2, list)
                            or not k2.isnumeric()
                        ):
                            return False
                        elif not isinstance(v2[0], list):
                            return False
                        elif not all([isinstance(x, list) for x in v2]):
                            return False
                else:
                    return False
            elif k == "gfx":
                if isinstance(v, dict):
                    for k2, v2 in v.items():
                        if (
                            not isinstance(k2, str)
                            or not isinstance(v2, list)
                            or not k2.isnumeric()
                        ):
                            return False
                        elif not isinstance(v2[0], list):
                            return False
                        elif not all([isinstance(x, list) for x in v2]):
                            return False
                else:
                    return False
            elif k == "punctuation":
                if not isinstance(v, list):
                    return False
                elif not all([isinstance(x, str) for x in v]):
                    return False
            elif k == "separators":
                if not isinstance(v, list):
                    return False
                elif not all([isinstance(x, str) for x in v]):
                    return False
            elif k == "pronouns":
                if not isinstance(v, list):
                    return False
                elif not all([isinstance(x, str) for x in v]):
                    return False
            elif k == "init_loc":
                if not isinstance(v, int):
                    return False
            elif k == "model":
                if not isinstance(v, str):
                    return False
                elif v not in ["SPECTRUM"]:
                    return False
            else:
                return False
        return True

    def __parse_database(self):
        self.font = self.ddb["font"]
        self.verbs = self.ddb["verbs"]
        self.nouns = self.ddb["nouns"]
        self.adverbs = self.ddb["adverbs"]
        self.messages = {int(k): v for (k, v) in self.ddb["messages"].items()}
        self.objects = {int(k): v for (k, v) in self.ddb["objects"].items()}
        self.locations = {int(k): v for (k, v) in self.ddb["locations"].items()}
        self.hpcs = self.ddb["hpcs"]
        self.lpcs = self.ddb["lpcs"]
        self.lcs = {int(k): v for (k, v) in self.ddb["lcs"].items()}
        self.model = self.ddb["model"]
        self.gfx = {int(k): v for (k, v) in self.ddb["gfx"].items()}
        self.separators = self.ddb["separators"]
        self.punctuation = self.ddb["punctuation"]
        self.pronouns = [x.upper() for x in self.ddb["pronouns"]]
        self.init_loc = self.ddb["init_loc"]

    def start_adventure(self):
        if not self.io or not self.ddb:
            return False
        if not DatabaseGAC.__check_ddb(self.ddb):
            return False
        if not hasattr(self.io, "set_width"):
            return False
        if not hasattr(self.io, "set_separators"):
            return False
        if not hasattr(self.io, "print"):
            return False
        if not hasattr(self.io, "input"):
            return False
        self.__parse_database()
        if self.init_loc == 0:
            return False
        self.io.set_width(32)  # For now...
        self.io.set_separators(self.punctuation)
        self.counters = [0 for x in range(0, 128)]
        self.flags = [False for x in range(0, 256)]
        self.current_loc = self.ddb["init_loc"]
        self.stack = []
        self.verb = 0
        self.adverb = 0
        self.noun1 = 0
        self.noun2 = 0
        self.old_noun = 0
        self.max_weight = 255
        self.ready = True
        # Set light on
        self.flags[1] = True
        # set objects to initial locations
        objs = dict()
        for k, v in self.objects.items():
            v["loc"] = v["initial_loc"]
            objs[k] = v
        self.objects = objs
        return True

    def __find_word(self, word_dictionary, word):
        # The real interpreter cuts the found words until it finds a match
        l = len(word)
        for k, v in word_dictionary.items():
            k = k.upper()
            if len(k) > l:
                k = k[0:l]
            if k == word:
                return v
        return 0

    def __get_location_objects(self, loc_id):
        res = {}
        for k, v in self.objects.items():
            if v["loc"] == loc_id:
                res[k] = v
        return res

    def __display_room(self, loc):
        # Check whether there's light
        if not self.flags[self.LIGHTING_FLAG] and not self.flags[self.LAMP_FLAG]:
            self.io.print(self.messages[self.ITSDARK])
        else:
            self.io.print(self.locations[loc]["desc"])
            objs = self.__get_location_objects(loc)
            if len(objs) > 0:
                str_obj = self.messages[self.OBJHERE]
                top = False
                for v in objs.values():
                    if top:
                        str_obj += ","
                    str_obj += v["name"]
                    top = True
                self.io.print(str_obj)
            if self.show_exits:
                exits = self.locations[loc]["exits"]
                top = False
                if len(exits) > 0:
                    str_exits = "\nYou can go "
                    for v in exits:
                        if not top:
                            str_obj += ","
                        dir = v["dir"]
                        for k2, v2 in self.verbs:
                            if v2 == dir:
                                str_exits += k2
                                break
                        top = True
                    self.io.print(str_exits)

    def __parse_input(self, input_string):
        self.verb = 0
        self.adverb = 0
        self.noun1 = 0
        self.noun2 = 0
        input_string = input_string.upper()
        words = input_string.split()
        while len(words) > 0:
            word = words.pop(0)
            matched = False
            if word == "*QUIT":
                return (True, True)
            if self.verb == 0 and not matched:
                self.verb = self.__find_word(self.verbs, word)
                matched = self.verb != 0
            # check noun1 in case the word is duplicated in adverbs and nouns
            if self.noun1 == 0 and not matched:
                self.noun1 = self.__find_word(self.nouns, word)
                if self.noun1 != 0:
                    self.old_noun = self.noun1
                elif word in self.pronouns:
                    self.noun1 = self.old_noun
                matched = self.noun1 != 0
            if self.adverb == 0 and not matched:
                self.adverb = self.__find_word(self.adverbs, word)
                matched = self.adverb != 0
            if self.noun2 == 0 and self.noun2 != 0 and not matched:
                self.noun2 = self.__find_word(self.nouns, word)
                matched = self.noun2 != 0
        return (self.verb != 0 or self.noun1 != 0, False)

    # TODO: It pronoun

    def __perfom_conditions(self, cond_list, exit_if_done):
        # reset stack
        self.stack = []
        skip = False
        pos = 0
        done = False
        finished = False
        if_true = False
        while pos < len(cond_list) and not (done and exit_if_done):
            instruction = cond_list[pos]
            pos += 1
            cmd = instruction[0]
            if not skip or (skip and cmd == "END"):
                if cmd == "PUSH":
                    self.stack.append(instruction[1])
                elif cmd == "OP0":
                    pass
                elif cmd == "AND":
                    s0 = self.stack.pop()
                    s1 = self.stack.pop()
                    s0 = s0 & s1
                    self.stack.append(s0)
                elif cmd == "OR":
                    s0 = self.stack.pop()
                    s1 = self.stack.pop()
                    s0 = s0 | s1
                    self.stack.append(s0)
                elif cmd == "XOR":
                    s0 = self.stack.pop()
                    s1 = self.stack.pop()
                    s0 = s0 ^ s1
                    self.stack.append(s0)
                elif cmd == "NOT":
                    s0 = self.stack.pop()
                    if s0 == 0:
                        s0 = 1
                    else:
                        s0 = 0
                    self.stack.append(s0)
                elif cmd == "HOLD":
                    s0 = self.stack.pop()
                    self.__wait_key_or_timeout(s0)
                elif cmd == "GET":
                    s0 = self.stack.pop()
                    if s0 in self.objects.keys():
                        obj = self.objects[s0]
                        # First check object is present
                        if obj["loc"] == self.current_loc:
                            playerweight = 0
                            for v in self.objects.values():
                                if v["loc"] == self.CARRIED_LOC:
                                    playerweight += v["weight"]
                            if playerweight + obj["weight"] > self.max_weight:
                                self.io.print(self.messages[self.TOOMUCH] + "\n")
                            else:
                                obj["loc"] = self.CARRIED_LOC
                        else:
                            self.io.print(self.messages[self.CANTSEE] + "\n")
                elif cmd == "DROP":
                    s0 = self.stack.pop()
                    if s0 in self.objects.keys():
                        obj = self.objects[s0]
                        if s0 not in self.objects.keys():
                            self.io.print(self.messages[self.DONTHAVE] + "\n")
                        else:
                            obj = self.objects[s0]
                            if obj["loc"] == self.CARRIED_LOC:
                                obj["loc"] = self.current_loc
                            else:
                                self.io.print(self.messages[self.DONTHAVE] + "\n")
                elif cmd == "SWAP":
                    s0 = self.stack.pop()
                    s1 = self.stack.pop()
                    if s0 in self.objects.keys() and s1 in self.objects.keys():
                        l0 = self.objects[s0]["loc"]
                        l1 = self.objects[s1]["loc"]
                        self.objects[s0]["loc"] = l1
                        self.objects[s1]["loc"] = l0
                elif cmd == "TO":
                    r = self.stack.pop()
                    o = self.stack.pop()
                    if o in self.objects.keys():
                        self.objects[o]["loc"] = r
                elif cmd == "OBJ":
                    o = self.stack.pop()
                    if o in self.objects.keys():
                        self.io.print(self.objects[o]["name"] + "\n")
                elif cmd == "SET":
                    f = self.stack.pop()
                    if f in range(0, len(self.flags)):
                        self.flags[f] = True
                elif cmd == "RESE":
                    f = self.stack.pop()
                    if f in range(0, len(self.flags)):
                        self.flags[f] = False
                elif cmd == "SET?":
                    f = self.stack.pop()
                    if f in range(0, len(self.flags)):
                        if self.flags[f]:
                            self.stack.append(1)
                        else:
                            self.stack.append(0)
                    else:
                        self.stack.append(0)
                elif cmd == "RES?":
                    f = self.stack.pop()
                    if f in range(0, len(self.flags)):
                        if self.flags[f]:
                            self.stack.append(0)
                        else:
                            self.stack.append(1)
                    else:
                        self.stack.append(1)
                elif cmd == "CSET":
                    s0 = self.stack.pop()
                    s1 = self.stack.pop()
                    if s0 in range(0, len(self.counters)):
                        self.counters[s0] = s1 & 0xFF
                elif cmd == "CTR":
                    s0 = self.stack.pop()
                    val = 0
                    if s0 in range(0, len(self.counters)):
                        val = self.counters[s0]
                    self.stack.append(val)
                elif cmd == "INCR":
                    s0 = self.stack.pop()
                    if s0 in range(0, len(self.counters)):
                        if self.counters[s0] < 255:
                            self.counters[s0] += 1
                elif cmd == "DECR":
                    s0 = self.stack.pop()
                    if s0 in range(0, len(self.counters)):
                        if self.counters[s0] > 0:
                            self.counters[s0] -= 1
                elif cmd == "EQU?":
                    s0 = self.stack.pop()
                    s1 = self.stack.pop()
                    if s0 in range(0, len(self.counters)):
                        if self.counters[s0] == s1:
                            self.stack.append(1)
                        else:
                            self.stack.append(0)
                    else:
                        self.stack.append(0)
                elif cmd == "DESC":
                    r = self.stack.pop()
                    if r in self.locations.keys():
                        self.__display_room(r)
                elif cmd == "LOOK":
                    if self.current_loc in self.locations.keys():
                        self.__display_room(self.current_loc)
                elif cmd == "MESS":
                    m = self.stack.pop()
                    if m in self.messages.keys():
                        self.io.print(self.messages[m])
                elif cmd == "PRIN":
                    m = self.stack.pop()
                    self.io.print(f"{m}")
                elif cmd == "RAND":
                    m = self.stack.pop()
                    self.stack.append(random.randint(0, m))
                elif cmd == "<":
                    s0 = self.stack.pop()
                    s1 = self.stack.pop()
                    if s1 < s0:
                        self.stack.append(1)
                    else:
                        self.stack.append(0)
                elif cmd == ">":
                    s0 = self.stack.pop()
                    s1 = self.stack.pop()
                    if s1 > s0:
                        self.stack.append(1)
                    else:
                        self.stack.append(0)
                elif cmd == "=":
                    s0 = self.stack.pop()
                    s1 = self.stack.pop()
                    if s1 == s0:
                        self.stack.append(1)
                    else:
                        self.stack.append(0)
                elif cmd == "HERE":
                    s0 = self.stack.pop()
                    if s0 in self.objects.keys():
                        obj = self.objects[s0]
                        if obj["loc"] == self.current_loc:
                            self.stack.append(1)
                        else:
                            self.stack.append(0)
                    else:
                        self.stack.append(0)
                elif cmd == "CARR":
                    s0 = self.stack.pop()
                    if s0 in self.objects.keys():
                        obj = self.objects[s0]
                        if obj["loc"] == self.CARRIED_LOC:
                            self.stack.append(1)
                        else:
                            self.stack.append(0)
                    else:
                        self.stack.append(0)
                elif cmd == "AVAIL":
                    s0 = self.stack.pop()
                    if s0 in self.objects.keys():
                        obj = self.objects[s0]
                        if (
                            obj["loc"] == self.current_loc
                            or obj["loc"] == self.CARRIED_LOC
                        ):
                            self.stack.append(1)
                        else:
                            self.stack.append(0)
                    else:
                        self.stack.append(0)
                elif cmd == "+":
                    s0 = self.stack.pop()
                    s1 = self.stack.pop()
                    self.stack.append(s1 + s0)
                elif cmd == "-":
                    s0 = self.stack.pop()
                    s1 = self.stack.pop()
                    self.stack.append(s1 - s0)
                elif cmd == "TURN":
                    self.stack.append(
                        (self.counters[self.TURN_CNT_H] * 256)
                        + self.counters[self.TURN_CNT_L]
                    )
                elif cmd == "AT":
                    r = self.stack.pop()
                    if r == self.current_loc:
                        self.stack.append(1)
                    else:
                        self.stack.append(0)
                elif cmd == "OP28":
                    self.io.print("ILLEGAL COMMAND OP28")
                elif cmd == "OP29":
                    self.io.print("ILLEGAL COMMAND OP29")
                elif cmd == "OKAY":
                    self.io.print(self.messages[self.OKAY] + "\n")
                    done = True
                elif cmd == "WAIT":
                    done = True
                elif cmd == "QUIT":
                    self.io.print(self.messages[self.YOUSURE])
                    res = self.io.input()
                    if res.upper() in ["YES", "Y", "SI", "S"]:
                        finished = True
                elif cmd == "EXIT":
                    finished = True
                elif cmd == "ROOM":
                    self.stack.append(self.current_loc)
                elif cmd == "NOUN":
                    r = self.stack.pop()
                    res = 0
                    if r == self.noun1 or r == self.noun2:
                        res = 1
                    self.stack.append(res)
                elif cmd == "VERB":
                    r = self.stack.pop()
                    res = 0
                    if r == self.verb:
                        res = 1
                    self.stack.append(res)
                elif cmd == "ADVE":
                    r = self.stack.pop()
                    res = 0
                    if r == self.adverb:
                        res = 1
                    self.stack.append(res)
                elif cmd == "GOTO":
                    r = self.stack.pop()
                    self.current_loc = r
                    if r in self.locations.keys():
                        self.__display_room(self.current_loc)
                elif cmd == "NO1":
                    self.stack.append(self.noun1)
                elif cmd == "NO2":
                    self.stack.append(self.noun2)
                elif cmd == "VBNO":
                    self.stack.append(self.verb)
                elif cmd == "LIST":
                    r = self.stack.pop()
                    for o in self.objects.values():
                        if o["loc"] == r:
                            self.io.print(o["name"] + "\n")
                elif cmd == "CONN":
                    d = self.stack.pop()
                    res = 0
                    if self.current_loc in self.locations.keys():
                        loc = self.locations[self.current_loc]
                        for v in loc["exits"]:
                            if v["dir"] == d:
                                res = v["dest"]
                                break
                    self.stack.append(res)
                elif cmd == "WEIG":
                    s0 = self.stack.pop()
                    res = 0
                    if s0 in self.objects.keys():
                        res = self.objects[s0]["weight"]
                    self.stack.append(res)
                elif cmd == "WITH":
                    self.stack.append(self.CARRIED_LOC)
                elif cmd == "STRE":
                    s0 = self.stack.pop()
                    self.max_weight = s0
                elif cmd == "LF":
                    self.io.print("\n")
                elif cmd == "END":
                    skip = False
                    self.stack = []
                elif cmd == "IF":
                    s0 = self.stack.pop()
                    if s0 == 0:
                        skip = True
                    else:
                        if_true = True
                        skip = False
                elif cmd == "PICT":
                    # TODO
                    pass
                elif cmd == "TEXT":
                    # TODO
                    pass
                elif cmd == "SAVE":
                    # TODO
                    pass
                elif cmd == "LOAD":
                    # TODO
                    pass
                else:
                    self.io.print(f"INVALID OPCODE {cmd}.\n")
        return (finished, done, if_true)

    def run_adventure(self):
        if not self.ready:
            return
        finished = False
        new_room = True
        if_true = False
        statements = []
        while not finished:
            # print current location
            if new_room:
                self.__display_room(self.current_loc)
                new_room = False

            # Increment turn
            if self.counters[self.TURN_CNT_L] < 255:
                self.counters[self.TURN_CNT_L] += 1
            elif self.counters[self.TURN_CNT_H] < 255:
                self.counters[self.TURN_CNT_L] = 0
                self.counters[self.TURN_CNT_H] += 1

            # High priority conditions
            finished, done, if_true = self.__perfom_conditions(self.hpcs, False)
            if finished:
                break

            if not new_room and len(statements) == 0:
                input_str = ""
                while len(input_str) == 0:
                    self.io.print("\n" + self.messages[self.ASK])
                    input_str = self.io.input()
                # Separate statements
                separators = filter(
                    lambda x: x != " ", self.separators + self.punctuation
                )
                for sep in separators:
                    input_str = input_str.replace(sep, ".")
                statements = input_str.split(".")
                self.old_noun = 0  # Delete after new text input

            # Process player input
            while len(statements) > 0:
                input_str = statements.pop(0)
                valid_input, finished = self.__parse_input(input_str)
                if finished:
                    break
                elif valid_input:
                    # Check connection table
                    for exit in self.locations[self.current_loc]["exits"]:
                        if exit["dir"] == self.verb:
                            self.current_loc = exit["dest"]
                            new_room = True
                            break
                    if new_room or valid_input:
                        break

            if new_room or finished:
                continue

            # Local conditions
            done = False
            if_true = False
            if self.current_loc in self.lcs.keys():
                finished, done, if_true = self.__perfom_conditions(
                    self.lcs[self.current_loc], True
                )
            if new_room or done:
                continue

            # Low priority conditions
            finished, done, if_true_lcp = self.__perfom_conditions(self.lpcs, True)
            if new_room or done:
                continue

            if not if_true and not if_true_lcp:
                if self.verb == 0:
                    self.io.print(self.messages[self.NOTUNDERSTAND] + "\n")
                else:
                    self.io.print(self.messages[self.CANTDO] + "\n")


class IoCallbackGAC(IoInterfaceCallbackGAC):
    def __init__(self):
        self.line_remain = 0
        super().__init__()

    def set_width(self, w):
        super().set_width(w)
        self.line_remain = w

    def print(self, string):
        # This method replicates the 8bit mechanism. No much python-correctness is expected
        separators = self.separators + ["\n"]
        pos = 0
        while pos < len(string):
            pos_w = pos
            while pos_w < (len(string) - 1) and string[pos_w] not in separators:
                pos_w += 1
            substring = string[pos : pos_w + 1]
            if len(substring) > self.line_remain:
                sys.stdout.write("\n")
                self.line_remain = self.width
            if string[pos_w] == "\n":
                self.line_remain = self.width
            self.line_remain -= len(substring)
            pos = pos_w + 1
            sys.stdout.write(substring)

    def input(self):
        self.line_remain = self.width
        return input()


def main():
    if sys.version_info[0] < 3:  # Python 2
        sys.exit(_("ERROR: Invalid python version"))

    version = "1.0.0"
    program = "reGAC" + version
    exec = "reGAC"

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
        help=_("JSON database file"),
    )

    try:
        args = arg_parser.parse_args()
    except FileNotFoundError as f1:
        sys.exit(_("ERROR: File not found:") + f"{f1}")
    except NotADirectoryError as f2:
        sys.exit(_("ERROR: Not a valid path:") + f"{f2}")

    with open(args.input_path) as f:
        ddb = json.load(f)

    io = IoCallbackGAC()
    ddb = DatabaseGAC(ddb, io)

    if not ddb.start_adventure():
        sys.exit("Invalid Database")
    else:
        ddb.run_adventure()


if __name__ == "__main__":
    main()
