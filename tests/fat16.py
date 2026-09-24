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
"""Reading a file off a card, which is what a Spectrum Next keeps its games on.

Only reading, and only what a card image as ZEsarUX ships it is: one FAT16
partition, found in the partition table, short names.  That is enough to say
whether a file a test's machine wrote is there and what is in it.
"""

import struct

SECTOR = 512


class Card:
    def __init__(self, path):
        with open(path, "rb") as f:
            self.image = f.read()
        start = struct.unpack_from("<I", self.image, 0x1BE + 8)[0] * SECTOR
        (per_sector, per_cluster, reserved, fats, roots, _, _,
         per_fat) = struct.unpack_from("<HBHBHHBH", self.image, start + 11)
        fat_at = start + reserved * per_sector
        self.fat = self.image[fat_at:fat_at + per_fat * per_sector]
        self.root_at = fat_at + fats * per_fat * per_sector
        self.data_at = self.root_at + roots * 32
        self.cluster = per_cluster * per_sector

    def _chain(self, cluster):
        out = []
        while 2 <= cluster < 0xFFF8:
            at = self.data_at + (cluster - 2) * self.cluster
            out.append(self.image[at:at + self.cluster])
            cluster = struct.unpack_from("<H", self.fat, cluster * 2)[0]
        return b"".join(out)

    @staticmethod
    def _entries(raw):
        for at in range(0, len(raw), 32):
            entry = raw[at:at + 32]
            if entry[0] == 0:
                return
            if entry[0] == 0xE5 or entry[11] == 0x0F:     # gone, or a long name
                continue
            name = entry[:8].decode("latin-1").rstrip()
            ext = entry[8:11].decode("latin-1").rstrip()
            yield ((name + "." + ext) if ext else name,
                   struct.unpack_from("<H", entry, 26)[0],
                   struct.unpack_from("<I", entry, 28)[0])

    def read(self, path):
        """The file at `path`, folders parted by /, or None if it is not
        there."""
        raw = self.image[self.root_at:self.data_at]
        parts = [part.upper() for part in path.split("/") if part]
        for n, part in enumerate(parts):
            for name, cluster, size in self._entries(raw):
                if name.upper() == part:
                    raw = self._chain(cluster)
                    if n == len(parts) - 1:
                        return raw[:size]
                    break
            else:
                return None
        return None
