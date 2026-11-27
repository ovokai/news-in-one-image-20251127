# mapdata.py -- a hand-drawn ASCII world map for the poster's dot-matrix
# panel, plus the grid positions of the numbered story pins.
#
# WORLD_ROWS is a rough equirectangular sketch typed out by hand: '#'
# means land, ' ' means sea.  It is a schematic for a dot panel, not a
# survey -- coastlines are simplified to a few dozen characters each.
# main.py walks the rows and stamps one dot per land cell.
#
# PINS maps story numbers 1-13 (the three leads and ten feature cards)
# to (column, row) cells on this grid, matched to the drawn continents.

WORLD_ROWS = [
    "      #######                               ###############",
    "    ############     #####           ########################",
    "   ##############   ####          #############################",
    "    #############               # ##### ###################### #",
    "     ###########                ###### ################### #",
    "      #########                ####               ###############",
    "      ########                #####            ############    #",
    "       ######                 ####  #####        ########",
    "       ######                 ################# ########",
    "        ####                 ##########  ##  ####",
    "         ##                 #########    #    ####",
    "           #               #### #######           #####",
    "               #######           #######",
    "                ######              #####           #####",
    "                #####               #####",
    "                 ####               ###       #",
    "                 ###               ##",
    "                 ###                                   ######",
    "                  ##                                  ########",
    "                  #                                    #####",
    "                  #                                     ###",
    "                  ##                                            #",
    "                   #                                             #",
    "                   #",
]

# (column, row) of each numbered pin on the grid above.
PINS = {
    1: (44, 9),    # Hormuz Strait -- escorted tanker convoy
    2: (35, 5),    # Bonn -- climate talks
    3: (54, 7),    # Shenzhou-22 / Tiangong rendezvous
    4: (40, 8),    # Gaza -- Rafah aid convoy
    5: (40, 5),    # Kyiv -- prisoner exchange
    6: (43, 10),   # Riyadh -- port-blast inquiry
    7: (54, 9),    # Shenzhen -- Huawei chip launch
    8: (50, 9),    # Assam -- Brahmaputra floods
    9: (14, 7),    # Washington -- Federal Reserve decision
    10: (18, 20),  # Santiago -- Chile runoff count
    11: (60, 18),  # Brisbane -- Ashes day five
    12: (36, 12),  # Nigeria -- malaria vaccine rollout
    13: (62, 2),   # Low orbit -- Webb telescope finding
}
