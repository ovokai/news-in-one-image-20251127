"""Dot-matrix world map for the "where it happened" panel.

The map is a hand-drawn 72 x 40 grid in a plain equirectangular
layout: one character per cell, "." for ocean and a region letter
for land. The shapes are deliberately stylised; at a ~4 px dot
pitch only the silhouette has to read as the world.

Region letters: N = North America, L = South America,
E = Europe, M = Middle East, F = Africa, S = East Asia,
H = South & SE Asia, O = Oceania.

PINS maps each numbered story (1-13) to the (column, row) of its
pin, picked so every pin lands on or just beside its landmass,
with the crowded Europe and Middle East clusters spread apart
so no two pins hide each other.
"""

COLS = 72
ROWS = 40

GRID = [
    "...........NNN.............NN..........E....................EE..........",
    "........NNNNNNNNNNNNNNN...NNNNN.......EEE.................EEEEE.........",
    "....NNNNNNNNNNNNNNNNNNNNN.NNNNN......EEEEEEEE.EEEEEEEEEEEEEEEEEEEEEEEEE.",
    "...NNNNNNNNNNNNNNNNNNNNNNN.NNN........EEEEEE...EEEEEEEEEEEEEEEEEEEEEEEEE",
    "....NNNNNNNNNNNNNNNNNNNNN.............EEEEE...EEEEEEEEEEEEEEEEEEEEEEEEE.",
    ".....NNNNNNNNNNNNNNNNNNN............EEEEEE...EEEEEEEEEEEEEEEEEEEEEEEEE..",
    "......NNNNNNNNNNNNNNNNN............EEEEEEE..EEEEEEEEEEEEEEEEEEEEEEEEE...",
    "........NNNNNNNNNNNNNN............EEEEEEEEE.EEEEEEEEEEEEEEEEEEEEEEE.....",
    ".........NNNNNNNNNNNN............EEEEEEEEEEE.EEEEEEEEEEEEEEEEEEEE.......",
    "..........NNNNNNNNNNN............EEEEEEEEEE..EEEEEEEEEEEEEEEEEEESSSS......",
    "...........NNNNNNNNNNN............EEEEEEEE.EEEEEE.SSSSSSSSSSSSSSS.......",
    "............NNNNNNNNN..............EEEEEE...MMMMMSSSSSSSSSSSSSSS........",
    ".............NNNNNNNNN..............EEEE...MMMMMMMSSSSSSSSSSSSS.........",
    "..............NNNN...............FFFFFFFFFFFFFMMMM..HHHHSSSSSS..........",
    "..............NNNN...............FFFFFFFFFFFFFFMMMM.HHHHHSSSSSS.........",
    "...............NNN...............FFFFFFFFFFFFFFMMMM..HHHH.SSSS..........",
    "...............NNN................FFFFFFFFFFFFFF.....HHHH.SSS...........",
    "................NNN................FFFFFFFFFFFFF.....HHHH.SSS...........",
    ".................NNN................FFFFFFFFFFFF....HHHHH.SSS...........",
    "..................NNN................FFFFFFFFFFF....HHHHH..SSS..........",
    "....................LLLL..............FFFFFFFFFF......HH....SSS.........",
    "....................LLLLLL.............FFFFFFFFF.......HH....SSS........",
    ".....................LLLLLL.............FFFFFFFF........HHH...OOO.......",
    ".....................LLLLLLL............FFFFFFFF........HHHHH..OOOO.....",
    ".....................LLLLLLLL............FFFFFFF.........HHH..OOOO......",
    "......................LLLLLLLL...........FFFFFFF..............OOOOO.....",
    "......................LLLLLLLL............FFFFF..............OOOOOOO....",
    "......................LLLLLLLL............FFFFF..............OOOOOOO....",
    ".......................LLLLLLL............FFFFF..............OOOOOOO....",
    ".......................LLLLLL.............FFFF................OOOOOO....",
    ".......................LLLLLL.............FFFF................OOOOO.....",
    ".......................LLLLL...............FFF.................OOOO.....",
    ".......................LLLL................FF...................OOO.....",
    ".......................LLL.......................................OO.....",
    ".......................LL.............................................OO",
    ".......................LL.............................................OO",
    ".......................LL...............................................",
    ".......................LL...............................................",
    ".......................L................................................",
    "........................................................................",
]

PINS = {
    1: (49, 16),    # Strait of Hormuz (Gulf of Oman, beside the strait)
    2: (35, 9),     # London markets
    3: (39, 8),     # Kyiv
    4: (61, 12),    # Seoul
    5: (46, 13),    # Riyadh
    6: (16, 13),    # Washington
    7: (43, 10),    # Antalya, COP31
    8: (56, 11),    # Jiuquan, Shenzhou-24
    9: (42, 15),    # Cairo talks
    10: (53, 18),   # Mumbai
    11: (21, 12),   # New York
    12: (64, 31),   # Adelaide
    13: (31, 12),   # Cornwall (Atlantic, beside the coast)
}
