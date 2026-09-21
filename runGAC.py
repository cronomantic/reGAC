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
import sys
import os
import argparse
import gettext
import json
import random
import platform

from regac.text import expand, plain, typed


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


class GAC_Interpreter:

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

    def __init__(self, ddb, width=80):
        self.ddb = ddb
        self.counters = [0 for x in range(0, 128)]
        self.flags = [False for x in range(0, 256)]
        self.current_loc = 0
        self.stack = []
        self.width = width
        self.line_remain = width
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
        self.max_weight = 250
        self.weight = 0
        self.ready = False
        self.show_exits = False
        self.old_noun = 0
        self.finished = False
        self.new_room = True
        self.graphics = True
        self.statements = []

    def draw_picture(self, graphic_id):
        """Show the picture of a location.

        The text only interpreter has nowhere to draw it, so this does nothing.
        Frontends with a screen override it.
        """
        return

    def clear_picture(self):
        """Take the picture off the screen and give the text all of it, which
        is what TEXT asks for.  Text only interpreters have nothing to do."""
        return

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
                "no_objs_msg",
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
                        if len(v) != 128 * 8:
                            return False
                        elif not isinstance(v[0], int):
                            return False
                        elif not all(type(x) == type(v[0]) for x in v):
                            return False
                else:
                    return False
            elif k == "no_objs_msg":
                if not isinstance(v, str):
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
        self.no_objs_msg = self.ddb["no_objs_msg"]

    def start_adventure(self):
        if not self.ddb:
            return False
        if not GAC_Interpreter.__check_ddb(self.ddb):
            return False
        self.__parse_database()
        if self.init_loc == 0:
            return False
        self.counters = [0 for x in range(0, 128)]
        self.flags = [False for x in range(0, 256)]
        self.current_loc = self.ddb["init_loc"]
        self.stack = []
        self.verb = 0
        self.adverb = 0
        self.noun1 = 0
        self.noun2 = 0
        self.old_noun = 0
        # What can be carried at once, and what is being carried.  The
        # original starts every game with a strength of 250 and keeps the
        # count itself, adding in GET and taking away in DROP and nowhere
        # else, so an object moved out of the hand by TO or SWAP leaves the
        # count where it was.
        self.max_weight = 250
        self.weight = 0
        self.ready = True
        # Set light on
        self.flags[1] = True
        # set objects to initial locations
        objs = dict()
        for k, v in self.objects.items():
            v["loc"] = v["initial_loc"]
            objs[k] = v
        self.objects = objs
        self.finished = False
        self.new_room = True
        self.statements = []
        return True

    def __find_word(self, word_dictionary, word):
        # Typing the start of a word is enough, which is what the original
        # does: EX at MegaCorp makes it ask what to examine, and EXAMINAR, one
        # letter more than the word it holds, means nothing to it.  So a typed
        # word matches an entry it is the start of, never one shorter than
        # itself.  Taking them in order means the shortest of the entries a
        # word starts wins, which is what the 8 bit side does too.
        #
        # The marks come off both sides before they are compared, because
        # that is what the 8 bit side holds: no keyboard there has a key for
        # an accent, so a vocabulary that says ARAÑA is stored as ARANA and
        # answers to it.  See regac/text.py.
        word = typed(word)
        for k in sorted(word_dictionary):
            if typed(k.upper()).startswith(word):
                return word_dictionary[k]
        return 0

    def __get_location_objects(self, loc_id):
        res = {}
        for k, v in self.objects.items():
            if v["loc"] == loc_id:
                res[k] = v
        return res

    def __display_room(self, loc):
        # Check whether there's light.  In the dark the picture goes off the
        # screen with everything else, and the marker that says a room has
        # just been described is left alone, because none has: measured on
        # the original, see doc/pendiente.md.
        if not self.flags[self.LIGHTING_FLAG] and not self.flags[self.LAMP_FLAG]:
            self.clear_picture()
            self.print(self.messages[self.ITSDARK])
        else:
            self.flags[self.FLAG_ROOM_DESC] = True
            if self.graphics:
                self.draw_picture(self.locations[loc]["graphic_id"])
            self.print(self.locations[loc]["desc"])
            objs = self.__get_location_objects(loc)
            if len(objs) > 0:
                str_obj = self.messages[self.OBJHERE]
                top = False
                for v in objs.values():
                    if top:
                        str_obj += ","
                    str_obj += v["name"]
                    top = True
                self.print(str_obj)
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
                    self.print(str_exits)

    def __parse_input(self, input_string):
        """A word is tried as a verb, then as an adverb, then as a noun, and
        a noun goes into whichever slot is empty.  That order is the
        original's, read in its code; a word of no kind at all is passed
        over.  A pronoun stands for the last noun the order before named --
        the second when it named two -- which is worked out here, just before
        the slots are cleared, as the original does it.
        """
        if self.noun2 != 0:
            self.old_noun = self.noun2
        elif self.noun1 != 0:
            self.old_noun = self.noun1
        self.verb = 0
        self.adverb = 0
        self.noun1 = 0
        self.noun2 = 0
        words = input_string.upper().split()
        while len(words) > 0:
            word = words.pop(0)
            if word == "*QUIT":
                return (True, True)
            if self.verb == 0:
                self.verb = self.__find_word(self.verbs, word)
                if self.verb != 0:
                    continue
            if self.adverb == 0:
                self.adverb = self.__find_word(self.adverbs, word)
                if self.adverb != 0:
                    continue
            if self.noun2 != 0:
                continue                        # both of them named already
            found = self.__find_word(self.nouns, word)
            if found == 0 and word in self.pronouns:
                found = self.old_noun
            if found == 0:
                continue
            if self.noun1 == 0:
                self.noun1 = found
            else:
                self.noun2 = found
        return (self.verb != 0 or self.noun1 != 0, False)

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
                    if not self.wait_key_or_timeout(s0):
                        finished = True
                elif cmd == "GET":
                    # The order of the three refusals is the original's -- the
                    # hand, then the room, then the weight -- and every one of
                    # them ends the turn, and with it the table.  It refuses
                    # when the total *reaches* the strength, measured on it:
                    # with a strength of three it carries two things of one.
                    s0 = self.stack.pop()
                    if s0 in self.objects.keys():
                        obj = self.objects[s0]
                        if obj["loc"] == self.CARRIED_LOC:
                            self.print(self.messages[self.ALREADYHAVE] + "\n")
                            done = True
                        elif obj["loc"] != self.current_loc:
                            self.print(self.messages[self.CANTSEE] + "\n")
                            done = True
                        elif self.weight + obj["weight"] >= self.max_weight:
                            self.print(self.messages[self.TOOMUCH] + "\n")
                            done = True
                        else:
                            self.weight += obj["weight"]
                            obj["loc"] = self.CARRIED_LOC
                elif cmd == "DROP":
                    s0 = self.stack.pop()
                    if s0 in self.objects.keys():
                        obj = self.objects[s0]
                        if obj["loc"] == self.CARRIED_LOC:
                            obj["loc"] = self.current_loc
                            self.weight -= obj["weight"]
                        else:
                            self.print(self.messages[self.DONTHAVE] + "\n")
                            done = True
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
                elif cmd == "BRIN":
                    # Bring the object here.  What is already in the hand and
                    # what is nowhere at all each get their own message, and
                    # the turn ends there: read in the original and measured.
                    o = self.stack.pop()
                    if o in self.objects.keys():
                        loc = self.objects[o]["loc"]
                        if loc == self.CARRIED_LOC:
                            self.print(self.messages[self.ALREADYHAVE] + "\n")
                            done = True
                        elif loc == self.NOTHING_LOC:
                            self.print(self.messages[self.CANTFIND] + "\n")
                            done = True
                        else:
                            self.objects[o]["loc"] = self.current_loc
                elif cmd == "FIND":
                    # Move the player to the object, ignoring the connections.
                    # About what is in the hand it says nothing; what is
                    # nowhere gets 252 and ends the turn.
                    o = self.stack.pop()
                    if o in self.objects.keys():
                        loc = self.objects[o]["loc"]
                        if loc == self.CARRIED_LOC:
                            pass
                        elif loc == self.NOTHING_LOC:
                            self.print(self.messages[self.CANTFIND] + "\n")
                            done = True
                        elif loc in self.locations.keys():
                            self.current_loc = loc
                            self.__display_room(self.current_loc)
                elif cmd == "OBJ":
                    o = self.stack.pop()
                    if o in self.objects.keys():
                        self.print(self.objects[o]["name"] + "\n")
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
                        self.print(self.messages[m])
                elif cmd == "PRIN":
                    m = self.stack.pop()
                    self.print(f"{m}")
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
                elif cmd in ("AVAI", "AVAIL"):
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
                elif cmd == "IN":
                    r = self.stack.pop()
                    o = self.stack.pop()
                    if o in self.objects.keys() and self.objects[o]["loc"] == r:
                        self.stack.append(1)
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
                    self.print("ILLEGAL COMMAND OP28")
                elif cmd == "OP29":
                    self.print("ILLEGAL COMMAND OP29")
                elif cmd == "OKAY":
                    self.print(self.messages[self.OKAY] + "\n")
                    done = True
                elif cmd == "WAIT":
                    done = True
                elif cmd == "QUIT":
                    # The original reads one key and takes anything that is
                    # not an N for a yes -- measured on it by answering with
                    # an X, which ended the game.  A line is read here, so it
                    # is the first letter that speaks.
                    self.print(self.messages[self.YOUSURE])
                    res = self.input()
                    if not isinstance(res, str):
                        finished = True
                    elif not res.strip().upper().startswith("N"):
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
                    # One line, commas between, nothing after: what the
                    # original writes for LLEVAS UN LIBRO,UNA CAMISA.
                    r = self.stack.pop()
                    named = [o["name"] for o in self.objects.values()
                             if o["loc"] == r]
                    self.print(",".join(named) if named else self.no_objs_msg)
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
                    self.print("\n")
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
                    self.graphics = True
                elif cmd == "TEXT":
                    self.graphics = False
                    self.clear_picture()
                elif cmd == "SAVE":
                    # TODO
                    pass
                elif cmd == "LOAD":
                    # TODO
                    pass
                elif cmd in ("MUSIC", "SOUND"):
                    # There is no sound here, but the number they were given
                    # has to come off the stack whether anybody plays it or
                    # not: an adventure has the same shape on every machine,
                    # and this is one of them.
                    self.stack.pop()
                elif cmd == "QUIET":
                    pass
                else:
                    self.print(f"INVALID OPCODE {cmd}.\n")
        return (finished, done, if_true)

    def main_loop(self):
        # print current location
        if self.new_room:
            self.__display_room(self.current_loc)
            self.new_room = False

        # High priority conditions
        # The high priority table stops at a WAIT like the others: measured
        # on the original, two conditions of our own written over the start of
        # MegaCorp's, of which only the first ever spoke.
        self.finished, done, if_true = self.__perfom_conditions(self.hpcs, True)

        # And only now the turn is counted.  Which side of the table this
        # falls on matters: MegaCorp sets its whole game up in a condition
        # guarded by the count still being zero, and counting first leaves
        # that condition unreachable and the player dead on the opening move.
        if self.counters[self.TURN_CNT_L] < 255:
            self.counters[self.TURN_CNT_L] += 1
        elif self.counters[self.TURN_CNT_H] < 255:
            self.counters[self.TURN_CNT_L] = 0
            self.counters[self.TURN_CNT_H] += 1

        if self.finished:
            return self.finished

        if not self.new_room and len(self.statements) == 0:
            input_str = ""
            while len(input_str) == 0:
                self.print("\n" + self.messages[self.ASK])
                input_str = self.input()
                if not isinstance(input_str, str):
                    self.finished = True
                    return self.finished
            # Separate statements
            self.statements = self.__cut_into_orders(input_str)

        # Process player input
        while len(self.statements) > 0:
            input_str = self.statements.pop(0)
            valid_input, self.finished = self.__parse_input(input_str)
            if self.finished:
                break
            elif valid_input:
                # Check connection table
                for exit in self.locations[self.current_loc]["exits"]:
                    if exit["dir"] == self.verb:
                        self.current_loc = exit["dest"]
                        self.new_room = True
                        break
                if self.new_room or valid_input:
                    break

        if self.new_room or self.finished:
            return self.finished

        # Local conditions
        done = False
        if_true = False
        if self.current_loc in self.lcs.keys():
            self.finished, done, if_true = self.__perfom_conditions(
                self.lcs[self.current_loc], True
            )
        if self.new_room or done:
            return self.finished

        # Low priority conditions
        self.finished, done, if_true_lcp = self.__perfom_conditions(self.lpcs, True)
        if self.new_room or done:
            return self.finished

        if not if_true and not if_true_lcp:
            if self.verb == 0:
                self.print(self.messages[self.NOTUNDERSTAND] + "\n")
            else:
                self.print(self.messages[self.CANTDO] + "\n")

        return self.finished

    def __cut_into_orders(self, line):
        """One typed line into the orders it holds.

        The original cuts at four marks -- a comma, a full stop, a semicolon
        and an exclamation mark -- and at two words, THEN and AND: XYZZY THEN
        SUR makes MegaCorp complain about the first word and then walk south,
        where XYZZY SUR simply walks south.  Those two live in the original's
        interpreter; here they live in the database, put there by the
        decompiler, so that the words belong to the adventure and its author
        rather than to us.  They are matched whole, so ANDAR is not a joining
        word with a tail.

        The adventure's own table of punctuation is not what cuts: the
        original uses it to part words, and nothing else.  Measured on it,
        COGE-MATA is one order where COGE,MATA is two.
        """
        for mark in self.punctuation:
            if mark not in (" ", "") and mark not in ",.;!":
                line = line.replace(mark, " ")
        for mark in ",;!":
            line = line.replace(mark, ".")
        parting = {w.upper() for w in self.separators}
        orders = []
        for piece in line.split("."):
            taken = []
            for word in piece.split(" "):
                if word.upper() in parting:
                    orders.append(" ".join(taken))
                    taken = []
                else:
                    taken.append(word)
            orders.append(" ".join(taken))
        return orders

    def run(self):
        if not self.ready:
            return
        self.finished = False
        while not self.finished:
            self.main_loop()
        self.tell_the_score()

    def tell_the_score(self):
        """What the game was worth and how long it took, unless the adventure
        would rather not say: that is what the fourth marker is for."""
        if self.flags[self.SCORE_DIS_FLAG]:
            return
        turns = (self.counters[self.TURN_CNT_H] * 256
                 + self.counters[self.TURN_CNT_L])
        self.print("\n" + self.messages[self.YOURSCORE]
                   + str(self.counters[self.SCORE_CNT])
                   + self.messages[self.YOUTOOK] + str(turns)
                   + self.messages[self.TURNS] + "\n")

    def print(self, string):
        # A change of ink is written inside the text of a message and is not
        # text: this screen has one colour, so it comes out here the way it is
        # ignored on a machine that cannot colour anything either.
        string = plain(expand(string))
        # This follows what the original's $778A does, the same way the
        # machines do in z80/common/textout.asm: a word is held until what
        # ends it arrives, because only then is it known whether it fits, and
        # what ends it is held in turn, because where the line breaks depends
        # on whether a separator came before it.  One that ends a word stays
        # where it is and the word goes down alone; one out of a run of them
        # goes down with the word, and shows at the head of the line.  That is
        # what centres text in the original.  See doc/pendiente.md.
        separators = self.punctuation + ["\n"]

        def put(text):
            for char in text:
                sys.stdout.write(char)
                self.line_remain -= 1
                if self.line_remain <= 0:
                    self.line_remain = self.width

        def new_line():
            sys.stdout.write("\n")
            self.line_remain = self.width

        def word(sep, run, in_run):
            crowded = len(sep) + len(run) >= self.line_remain
            if sep and not in_run:
                put(sep)
                sep = ""
            if crowded and self.line_remain != self.width:
                new_line()
            put(sep + run)

        run, sep, in_run = "", "", False
        for char in string:
            if char not in separators:
                run += char
                continue
            if run:
                word(sep, run, in_run)
                run, in_run = "", False
            elif sep:
                put(sep)
                if self.line_remain == 1:
                    new_line()
                in_run = True
            else:
                in_run = False
            if char == "\n":
                sep, in_run = "", False
                new_line()
            else:
                sep = char
        if run:
            word(sep, run, in_run)
        elif sep:
            put(sep)

    def input(self):
        self.line_remain = self.width
        return input()

    def wait_key_or_timeout(self, timeout_frames):
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
        return True


def main():
    if sys.version_info[0] < 3:  # Python 2
        sys.exit(_("ERROR: Invalid python version"))

    version = "1.0.0"
    program = "runGAC" + version
    exec = "runGAC"

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

    ddb = GAC_Interpreter(ddb, 32)
    if not ddb.start_adventure():
        sys.exit("Invalid Database")
    else:
        ddb.run()


if __name__ == "__main__":
    main()
