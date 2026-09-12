import sys
import os

# from os import environ
# environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame
import threading
import queue
import argparse
import gettext
import json

from regac.devices import SpectrumDevice
from regac.gfx import SOURCE_ROWS as PICTURE_ROWS
from regac.gfx import Renderer

GFX_CHAR_WIDTH = SpectrumDevice.char_width
from runGAC import GAC_Interpreter


class GAC_Interpreter_Pygame(GAC_Interpreter):

    SPECTRUM_PALETTE = [
        0x000000,
        0x0100CE,
        0xCF0100,
        0xCF01CE,
        0x00CF15,
        0x01CFCF,
        0xCFCF15,
        0xCFCFCF,
        0x000000,
        0x0200FD,
        0xFF0201,
        0xFF02FD,
        0x00FF1C,
        0x02FFFF,
        0xFFFF1D,
        0xFFFFFF,
    ]

    WINDOW_WIDTH = 360
    WINDOW_HEIGHT = 240

    SCREEN_WIDTH = 256
    SCREEN_HEIGHT = 192

    CHAR_WIDTH = SCREEN_WIDTH >> 3
    CHAR_HEIGHT = SCREEN_HEIGHT >> 3

    SCREEN_START_X = (WINDOW_WIDTH - SCREEN_WIDTH) >> 1
    SCREEN_START_Y = (WINDOW_HEIGHT - SCREEN_HEIGHT) >> 1

    # A picture takes the top sixteen character rows, text lives below it.
    PICTURE_CHAR_ROWS = PICTURE_ROWS >> 3

    def __init__(self, ddb):
        self.print_att = 0x07
        self.pxl_screen = [0 for x in range(self.CHAR_WIDTH * self.SCREEN_HEIGHT)]
        self.att_screen = [
            self.print_att for x in range(self.CHAR_WIDTH * self.CHAR_HEIGHT)
        ]
        self.flash_counter = 0
        self.flash = False
        self.border = 0
        self.cx = 0
        self.cy = 0
        self.scx = 0
        self.scy = 0
        self.input_mode = False
        self.waitkey_mode = False
        self.frame_count = 0
        self.input_txt = ""
        self.text_top = 0  # first character row the text may use

        self.cmd_queue = queue.Queue()
        self.resp_queue = queue.Queue()

        self.th_interpreter = threading.Thread(target=self.__interpreter_task)

        super().__init__(ddb, self.CHAR_WIDTH)

        pygame.init()
        self._screen = pygame.display.set_mode(
            (self.WINDOW_WIDTH, self.WINDOW_HEIGHT), pygame.HWSURFACE
        )
        self._clock = pygame.time.Clock()
        self._active_screen = pygame.Surface((self.SCREEN_WIDTH, self.SCREEN_HEIGHT))
        self._running = True

    def __scroll_up(self):
        """Scroll the text window, leaving any picture above it untouched."""
        first_pxl = self.text_top * 8 * self.CHAR_WIDTH
        first_att = self.text_top * self.CHAR_WIDTH
        self.pxl_screen[first_pxl:] = self.pxl_screen[
            first_pxl + (self.CHAR_WIDTH * 8) :
        ] + [0 for x in range(self.CHAR_WIDTH * 8)]
        self.att_screen[first_att:] = self.att_screen[first_att + self.CHAR_WIDTH :] + [
            self.print_att for x in range(self.CHAR_WIDTH)
        ]

    def set_cursor(self, x=0, y=0):
        self.cx = x
        self.cy = y

    def __toggle_cursor(self, enable):
        pos_att = self.cx + (self.cy * self.CHAR_WIDTH)
        if enable:
            self.att_screen[pos_att] |= 0x80
        else:
            self.att_screen[pos_att] &= 0x7F

    def cls(self):
        """Clear the text window.  A picture on screen stays where it is."""
        self.cx = 0
        self.cy = self.text_top
        first_pxl = self.text_top * 8 * self.CHAR_WIDTH
        first_att = self.text_top * self.CHAR_WIDTH
        self.pxl_screen[first_pxl:] = [
            0 for x in range(len(self.pxl_screen) - first_pxl)
        ]
        self.att_screen[first_att:] = [
            self.print_att for x in range(len(self.att_screen) - first_att)
        ]

    def newline(self):
        self.cx = 0
        if self.cy < self.text_top:
            self.cy = self.text_top
            return
        if self.cy == self.CHAR_HEIGHT - 1:
            self.__scroll_up()
            if self.scy > 0:
                self.scy -= 1
        else:
            self.cy += 1

    def put_char(self, ch):
        if self.font:
            pos_pxl = self.cx + ((self.cy << 3) * self.CHAR_WIDTH)
            pos_att = self.cx + (self.cy * self.CHAR_WIDTH)
            pos_font = (ch & 0xFF) << 3
            for i in range(8):
                self.pxl_screen[pos_pxl + (i * self.CHAR_WIDTH)] = self.font[
                    pos_font + i
                ]
            self.att_screen[pos_att] = self.print_att

    def print_char(self, ch):
        if self.input_mode:
            self.__toggle_cursor(False)
        ch &= 0x7F
        if ch >= 32:
            self.put_char(ch)
            if self.cx == self.CHAR_WIDTH - 1:
                self.newline()
            else:
                self.cx += 1
        elif ch == 10:
            self.newline()
        if self.input_mode:
            self.__toggle_cursor(True)

    def backspace(self):
        if self.input_mode:
            self.__toggle_cursor(False)
        self.put_char(32)
        if self.cx == 0:
            if self.cy > 0:
                self.cx = self.CHAR_WIDTH - 1
                self.cy -= 1
            else:
                self.cx = 0
                self.cy = 0
        else:
            self.cx -= 1
        self.put_char(32)
        if self.input_mode:
            self.__toggle_cursor(True)

    def __show_picture(self, graphic_id):
        """Draw a picture into the top of the screen and put the text window
        underneath it."""
        picture = Renderer(self.gfx).run(graphic_id)
        for row in range(PICTURE_ROWS):
            start = row * self.CHAR_WIDTH
            self.pxl_screen[start : start + self.CHAR_WIDTH] = list(
                picture.pixels[row * GFX_CHAR_WIDTH : (row + 1) * GFX_CHAR_WIDTH]
            )
        for row in range(self.PICTURE_CHAR_ROWS):
            start = row * self.CHAR_WIDTH
            self.att_screen[start : start + self.CHAR_WIDTH] = list(
                picture.attrs[row * GFX_CHAR_WIDTH : (row + 1) * GFX_CHAR_WIDTH]
            )
        self.border = picture.border
        self.text_top = self.PICTURE_CHAR_ROWS
        self.cls()

    def draw_picture(self, graphic_id):
        self.cmd_queue.put((0x07, graphic_id))

    def clear_picture(self):
        self.cmd_queue.put((0x08,))

    def print_txt(self, st):
        chars = list(st.encode("ascii"))
        for c in chars:
            self.print_char(c)

    def on_draw(self):
        pxl_array = pygame.PixelArray(self._active_screen)
        for y in range(self.SCREEN_HEIGHT):
            for x in range(self.CHAR_WIDTH):
                pxl = self.pxl_screen[(y * self.CHAR_WIDTH) + x]
                att = self.att_screen[((y >> 3) * self.CHAR_WIDTH) + x]
                fg = att & 0x07 | ((att >> 3) & 0x08)
                bk = (att >> 3) & 0x0F
                for i in range(8):
                    px = (x << 3) + i
                    pxl_en = (pxl << i) & 0x80 != 0
                    if (att & 0x80 != 0) and self.flash:
                        pxl_en = not pxl_en
                    if pxl_en:
                        pxl_array[px, y] = self.SPECTRUM_PALETTE[fg]
                    else:
                        pxl_array[px, y] = self.SPECTRUM_PALETTE[bk]
        del pxl_array
        self._screen.fill(self.SPECTRUM_PALETTE[self.border & 0x07])
        self._screen.blit(
            self._active_screen, (self.SCREEN_START_X, self.SCREEN_START_Y)
        )

    def on_cleanup(self):
        pygame.quit()
        sys.exit()

    def run(self):
        self.th_interpreter.start()
        while self._running:
            self.on_update()
            self.on_draw()
            pygame.display.flip()
            self._clock.tick(50)  # limits FPS to 50
        print(self.th_interpreter.is_alive())
        self.th_interpreter.join()
        self.on_cleanup()

    def on_update(self):
        self.flash_counter += 1
        if self.flash_counter > 16:
            self.flash_counter = 0
            self.flash = not self.flash

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._running = False
            if event.type == pygame.KEYDOWN:
                if self.waitkey_mode:
                    self.resp_queue.put("")
                    self.waitkey_mode = False
                    self.frame_count = 0
                elif self.input_mode:
                    if event.key == pygame.K_BACKSPACE:
                        if not (self.cx == self.scx and self.cy == self.scy):
                            self.backspace()
                            self.input_txt = self.input_txt[:-1]
                    else:
                        char = event.unicode
                        if char == "\r" or char == "\n":
                            self.__toggle_cursor(False)
                            self.input_mode = False
                            self.print_txt("\n")
                            self.resp_queue.put(self.input_txt)
                        else:
                            self.print_txt(char)
                            self.input_txt += char

        if self.waitkey_mode:
            if self.frame_count == 0:
                self.resp_queue.put("")
                self.waitkey_mode = False
            else:
                self.frame_count -= 1
        elif not self.input_mode:
            try:
                rx_data = self.cmd_queue.get_nowait()
                self.cmd_queue.task_done()
            except:
                rx_data = None

            if isinstance(rx_data, tuple):
                cmd = rx_data[0]
                if cmd == 0x00:  # Quit
                    self._running = False
                elif cmd == 0x01:  # Print txt
                    self.print_txt(rx_data[1])
                elif cmd == 0x02:  # Input
                    self.input_mode = True
                    self.input_txt = ""
                    self.scx = self.cx
                    self.scy = self.cy
                    self.__toggle_cursor(True)
                elif cmd == 0x03:  # Clear screen
                    self.cls()
                elif cmd == 0x04:  # New line
                    self.newline()
                elif cmd == 0x05:  # wait for key or timeout
                    self.waitkey_mode = True
                    self.frame_count = rx_data[1]
                elif cmd == 0x06:  # pos cursor
                    self.set_cursor(rx_data[1], rx_data[2])
                elif cmd == 0x07:  # draw the picture of a location
                    self.__show_picture(rx_data[1])
                elif cmd == 0x08:  # drop the picture, text takes the screen
                    self.text_top = 0
                    self.cls()

    def __interpreter_task(self):
        if not self.ready:
            return
        self.finished = False
        while not self.finished:
            self.main_loop()

    def print(self, txt):
        # This method replicates the 8bit mechanism. No much python-correctness is expected
        separators = self.punctuation + ["\n"]
        pos = 0
        final_str = ""
        while pos < len(txt):
            pos_w = pos
            while pos_w < (len(txt) - 1) and txt[pos_w] not in separators:
                pos_w += 1
            subtxt = txt[pos : pos_w + 1]
            if len(subtxt) > self.line_remain:
                self.cmd_queue.put((0x01, "\n"))
                self.line_remain = self.width
            if txt[pos_w] == "\n":
                self.line_remain = self.width
            self.line_remain -= len(subtxt)
            pos = pos_w + 1
            self.cmd_queue.put((0x01, subtxt))

    def __get_response_data(self):
        val = None
        while val is None:
            try:
                val = self.resp_queue.get_nowait()
                self.resp_queue.task_done()
            except:
                val = None
        return val

    def input(self):
        self.line_remain = self.width
        self.cmd_queue.put((0x02,))
        txt = self.__get_response_data()
        return txt

    def wait_key_or_timeout(self, timeout_frames):
        self.cmd_queue.put((0x05, timeout_frames))
        val = self.__get_response_data()

    def quit(self):
        self.cmd_queue.put((0x00,))


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


if __name__ == "__main__":

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

    ddb = GAC_Interpreter_Pygame(ddb)
    if not ddb.start_adventure():
        sys.exit("Invalid Database")
    else:
        ddb.run()
