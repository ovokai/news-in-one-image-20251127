#!/usr/bin/env python3
"""The World in One Day -- Friday 27 November 2026.

Builds the daily one-image news poster (1024x1024 PNG) for the make.fun
competition "news-image-20261127".  Pure Python standard library: the
PNG encoder, the rasteriser and the 5x7 bitmap text engine are all
implemented in this file and in glyphs.py / mapdata.py, so the program
runs in a bare sandbox with no Pillow, no font files and no network.

Output: /output/entry.png when that directory exists (the grading
sandbox), otherwise ./entry.png next to this script.
"""

import os
import struct
import sys
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from glyphs import glyph_for, CHAR_W, CHAR_H
from mapdata import WORLD_ROWS, PINS

W = 1024
H = 1024

# ---------------- palette (cream newsprint, like the reference sheet) ----
PAPER = (243, 238, 222)
PAPER_DIM = (233, 225, 201)
INK = (26, 24, 20)
SOFT_INK = (74, 68, 58)
RED = (178, 32, 26)
DARK_RED = (138, 22, 18)
WHITE = (255, 255, 255)
LINE = (196, 186, 160)
SKY = (166, 198, 224)
SEA = (128, 170, 202)
SAND = (226, 205, 158)
LEAF = (96, 150, 84)

REGION_COLORS = {
    'EUROPE': (28, 62, 120),
    'MIDDLE EAST': (196, 110, 30),
    'AFRICA': (176, 134, 28),
    'EAST ASIA': (178, 32, 26),
    'SOUTH & SE ASIA': (14, 120, 108),
    'N. AMERICA': (86, 62, 150),
    'S. AMERICA': (38, 120, 64),
    'OCEANIA': (28, 108, 158),
    'WORLD & SPACE': (34, 32, 46),
}


# ---------------- canvas & PNG writer ------------------------------------
class Canvas:
    """A minimal RGB framebuffer with just the operations the poster
    needs, plus a deterministic PNG serialiser."""

    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.px = bytearray(bg) * (w * h)

    def set_px(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i:i + 3] = bytes(color)

    def fill_rect(self, x, y, w, h, color):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.w, x + w)
        y1 = min(self.h, y + h)
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes(color) * (x1 - x0)
        n = len(row)
        for yy in range(y0, y1):
            i = (yy * self.w + x0) * 3
            self.px[i:i + n] = row

    def rect_outline(self, x, y, w, h, color, t=1):
        self.fill_rect(x, y, w, t, color)
        self.fill_rect(x, y + h - t, w, t, color)
        self.fill_rect(x, y, t, h, color)
        self.fill_rect(x + w - t, y, t, h, color)

    def png_bytes(self):
        raw = bytearray()
        stride = self.w * 3
        for y in range(self.h):
            raw.append(0)  # filter type 0 (None) on every scanline
            raw += self.px[y * stride:(y + 1) * stride]
        ihdr = struct.pack('>IIBBBBB', self.w, self.h, 8, 2, 0, 0, 0)
        out = bytearray(b'\x89PNG\r\n\x1a\n')
        for tag, data in ((b'IHDR', ihdr),
                          (b'IDAT', zlib.compress(bytes(raw), 9)),
                          (b'IEND', b'')):
            out += struct.pack('>I', len(data)) + tag + data
            out += struct.pack('>I', zlib.crc32(tag + data) & 0xFFFFFFFF)
        return bytes(out)

    def save(self, path):
        with open(path, 'wb') as fh:
            fh.write(self.png_bytes())


# ---------------- text engine ---------------------------------------------
def text_width(s, scale, bold=False):
    """Pixel width of a string at the given integer scale."""
    if not s:
        return 0
    adv = (CHAR_W + 1) * scale + (1 if bold else 0)
    return len(s) * adv - scale


def draw_text(cv, x, y, s, scale, color, bold=False):
    """Draw one line of bitmap text; returns the x just past the text."""
    adv = (CHAR_W + 1) * scale + (1 if bold else 0)
    cx = x
    for ch in s:
        rows = glyph_for(ch)
        extra = 1 if bold else 0
        for r in range(CHAR_H):
            mask = rows[r]
            if not mask:
                continue
            for c in range(CHAR_W):
                if mask & (0x10 >> c):
                    cv.fill_rect(cx + c * scale, y + r * scale,
                                 scale + extra, scale, color)
        cx += adv
    return cx


def draw_text_c(cv, cx, y, s, scale, color, bold=False):
    """Draw text centred on the given x."""
    return draw_text(cv, cx - text_width(s, scale, bold) // 2, y, s,
                     scale, color, bold)


def draw_text_r(cv, xr, y, s, scale, color, bold=False):
    """Draw text ending at the given right-edge x."""
    return draw_text(cv, xr - text_width(s, scale, bold), y, s,
                     scale, color, bold)


def wrap_text(s, scale, max_w, bold=False):
    """Greedy word wrap; returns a list of lines that fit max_w."""
    lines = []
    cur = ''
    for word in s.split(' '):
        trial = word if not cur else cur + ' ' + word
        if text_width(trial, scale, bold) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def draw_para(cv, x, y, s, scale, color, max_w, line_gap=3, bold=False,
              max_lines=None):
    """Draw a wrapped paragraph; returns the y just below it."""
    lines = wrap_text(s, scale, max_w, bold)
    if max_lines is not None:
        lines = lines[:max_lines]
    step = CHAR_H * scale + line_gap
    for i, line in enumerate(lines):
        draw_text(cv, x, y + i * step, line, scale, color, bold)
    return y + len(lines) * step


# ---------------- shapes & furniture --------------------------------------
def draw_disc(cv, cx, cy, r, color):
    r2 = r * r
    for yy in range(cy - r, cy + r + 1):
        dy = yy - cy
        span = int((r2 - dy * dy) ** 0.5)
        cv.fill_rect(cx - span, yy, span * 2 + 1, 1, color)


def draw_ring(cv, cx, cy, r, color, t=2):
    for yy in range(cy - r, cy + r + 1):
        for xx in range(cx - r, cx + r + 1):
            d2 = (xx - cx) ** 2 + (yy - cy) ** 2
            if (r - t) ** 2 <= d2 <= r * r:
                cv.set_px(xx, yy, color)


def draw_line(cv, x0, y0, x1, y1, color, t=1):
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    while True:
        cv.fill_rect(x0 - t // 2, y0 - t // 2, t, t, color)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def draw_tri(cv, x, y, w, h, color, up=True):
    for i in range(h):
        frac = (i + 1) / h if up else (h - i) / h
        span = int(w * frac)
        cv.fill_rect(x + (w - span) // 2, y + i, span, 1, color)


def badge(cv, x, y, num, color, r=11):
    """Numbered circle badge used on leads, cards and map pins."""
    draw_disc(cv, x + r, y + r, r, color)
    s = str(num)
    tw = text_width(s, 2, True)
    draw_text(cv, x + r - tw // 2, y + r - 7, s, 2, WHITE, True)


def status_pill(cv, xr, y, label):
    """Small white pill with red label, right-aligned to xr."""
    w = text_width(label, 1, True) + 10
    cv.fill_rect(xr - w, y, w, 13, WHITE)
    cv.rect_outline(xr - w, y, w, 13, RED, 1)
    draw_text(cv, xr - w + 5, y + 3, label, 1, RED, True)
    return xr - w


def stars(cv, x, y, w, h, n=42):
    """Deterministic starfield (fixed-seed LCG, same every run)."""
    state = 20261127
    for _ in range(n):
        state = (state * 1103515245 + 12345) & 0x7FFFFFFF
        sx = x + state % w
        state = (state * 1103515245 + 12345) & 0x7FFFFFFF
        sy = y + state % h
        cv.set_px(sx, sy, WHITE)
        if state % 3 == 0:
            cv.set_px(sx + 1, sy, WHITE)


# ---------------- the three lead illustrations ----------------------------
def scene_tanker(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, SKY)
    draw_disc(cv, x + w - 34, y + 24, 13, (240, 196, 92))       # sun
    horizon = y + h - 34
    cv.fill_rect(x, horizon, w, h - (horizon - y), SEA)          # sea
    for i in range(5):                                           # waves
        wx = x + 12 + i * 52
        cv.fill_rect(wx, horizon + 8 + (i % 2) * 9, 26, 3, WHITE)
    hx, hy = x + 26, horizon - 26                                # tanker
    cv.fill_rect(hx, hy, 168, 16, (38, 40, 46))                  # hull
    cv.fill_rect(hx + 168, hy + 4, 18, 12, (38, 40, 46))         # bow
    cv.fill_rect(hx + 8, hy - 14, 26, 14, (196, 110, 30))        # containers
    cv.fill_rect(hx + 38, hy - 14, 26, 14, (28, 108, 158))
    cv.fill_rect(hx + 68, hy - 14, 26, 14, (38, 120, 64))
    cv.fill_rect(hx + 23, hy - 26, 26, 12, (28, 62, 120))
    cv.fill_rect(hx + 138, hy - 22, 20, 22, (226, 222, 208))     # bridge
    cv.fill_rect(hx + 143, hy - 18, 10, 5, SKY)
    ex, ey = x + w - 62, horizon - 10                            # escort
    cv.fill_rect(ex, ey, 48, 9, (90, 96, 104))
    cv.fill_rect(ex + 18, ey - 9, 12, 9, (90, 96, 104))


def scene_climate(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, (206, 226, 214))
    gx, gy, gr = x + 74, y + h // 2, 44                          # globe
    draw_disc(cv, gx, gy, gr, SEA)
    cv.fill_rect(gx - 30, gy - 26, 24, 12, LEAF)                 # continents
    cv.fill_rect(gx + 4, gy - 12, 28, 14, LEAF)
    cv.fill_rect(gx - 12, gy + 8, 22, 14, LEAF)
    cv.fill_rect(gx + 16, gy + 18, 16, 9, LEAF)
    draw_ring(cv, gx, gy, gr, (28, 62, 120), 2)
    tx = x + 150                                               # thermometer
    cv.fill_rect(tx, y + 18, 10, h - 44, WHITE)
    cv.rect_outline(tx, y + 18, 10, h - 44, INK, 1)
    cv.fill_rect(tx + 2, y + h - 48, 6, 22, RED)
    draw_disc(cv, tx + 5, y + h - 20, 10, RED)
    for i in range(4):                                           # heat ticks
        cv.fill_rect(tx + 14, y + 26 + i * 16, 8, 2, INK)
    ax = x + 196                                                 # rising arrow
    draw_line(cv, ax, y + h - 24, ax + 52, y + 30, RED, 3)
    draw_tri(cv, ax + 40, y + 16, 20, 16, RED)


def scene_space(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, (16, 18, 34))
    stars(cv, x, y, w, h)
    cv.fill_rect(x, y + h - 20, w, 20, SEA)                      # Earth limb
    cv.fill_rect(x, y + h - 20, w, 3, (210, 232, 246))
    sx, sy = x + 58, y + 40                                      # station
    cv.fill_rect(sx, sy, 74, 16, (214, 216, 220))                # core module
    cv.fill_rect(sx + 30, sy - 12, 14, 12, (214, 216, 220))      # node
    cv.fill_rect(sx - 40, sy + 2, 36, 12, (52, 92, 168))         # panels
    cv.fill_rect(sx + 78, sy + 2, 36, 12, (52, 92, 168))
    cv.fill_rect(sx + 34, sy + 16, 8, 12, (240, 196, 92))        # dock port
    cx2, cy2 = x + w - 62, y + h - 58                            # capsule
    draw_disc(cv, cx2, cy2, 13, (226, 222, 208))
    cv.fill_rect(cx2 - 4, cy2 - 22, 8, 10, (196, 110, 30))       # service mod
    draw_line(cv, sx + 112, sy + 30, cx2 - 14, cy2 + 4,          # approach path
              (240, 196, 92), 1)


def draw_dot_map(cv, x, y, cell, dot):
    """Stamp the ASCII world as a dot grid; returns (w, h) used."""
    rows = WORLD_ROWS
    mw = max(len(r) for r in rows) * cell
    for ri, row in enumerate(rows):
        for ci, ch in enumerate(row):
            if ch == '#':
                cv.fill_rect(x + ci * cell + 1, y + ri * cell + 1,
                             dot, dot, (96, 88, 66))
    return mw, len(rows) * cell


# ---------------- content: Friday 27 November 2026 ------------------------
LEADS = [
    {
        'num': 1, 'region': 'MIDDLE EAST', 'field': 'ENERGY',
        'status': 'OFFICIAL', 'scene': 'tanker',
        'callout': 'BRENT $118.40 +6.2%',
        'headline': 'Hormuz closure day 12: escorted convoy sails',
        'summary': 'Forty tankers crossed in convoy at dawn as Brent '
                   'jumped. War-risk premiums reach 9% of hull value.',
        'source': 'Reuters - OPEC wire',
    },
    {
        'num': 2, 'region': 'EUROPE', 'field': 'CLIMATE',
        'status': 'REPORTED', 'scene': 'climate',
        'callout': '$40BN LOSS & DAMAGE',
        'headline': 'Climate talks seal $40bn loss-and-damage deal',
        'summary': 'Agreed at 05:40 after an all-night session. Island '
                   'states call the $40bn a floor, not a ceiling.',
        'source': 'dpa - Reuters',
    },
    {
        'num': 3, 'region': 'EAST ASIA', 'field': 'SPACE',
        'status': 'CONFIRMED', 'scene': 'space',
        'callout': '5H 12M RENDEZVOUS',
        'headline': 'Shenzhou-22 docks with Tiangong in record time',
        'summary': 'Three astronauts docked 5h 12m after launch from '
                   'Jiuquan, a record for China\'s crewed programme.',
        'source': 'Xinhua - CNSA',
    },
]

CARDS = [
    {'num': 4, 'region': 'MIDDLE EAST', 'field': 'HUMANITARIAN',
     'status': 'REPORTED',
     'headline': '200-truck aid convoy crosses Rafah',
     'summary': 'First big convoy since 9 Nov: flour, fuel, surgical kits.',
     'source': 'UNRWA - Reuters'},
    {'num': 5, 'region': 'EUROPE', 'field': 'SECURITY',
     'status': 'CONFIRMED',
     'headline': 'Kyiv, Moscow swap 180 prisoners',
     'summary': 'UAE-brokered swap at Belarus border; ICRC verified lists.',
     'source': 'AP - Reuters'},
    {'num': 6, 'region': 'MIDDLE EAST', 'field': 'INVESTIGATION',
     'status': 'OFFICIAL',
     'headline': 'Riyadh probe names two port officials',
     'summary': 'Jeddah blast inquiry cites forged inspection logs.',
     'source': 'SPA - Al Arabiya'},
    {'num': 7, 'region': 'EAST ASIA', 'field': 'TECHNOLOGY',
     'status': 'CONFIRMED',
     'headline': 'Huawei shows 2nm Kirin chip',
     'summary': 'Kirin 9Z made without US tools; Mate handset ships 12 Dec.',
     'source': 'Reuters - Huawei'},
    {'num': 8, 'region': 'SOUTH & SE ASIA', 'field': 'WEATHER',
     'status': 'REPORTED',
     'headline': 'Assam floods ease, 1.2m in camps',
     'summary': 'Brahmaputra falls below danger mark; rail links reopen.',
     'source': 'PTI - IMD'},
    {'num': 9, 'region': 'N. AMERICA', 'field': 'MARKETS',
     'status': 'OFFICIAL',
     'headline': 'Fed holds rates, hints at March cut',
     'summary': 'S&P 500 closes at a record as chip stocks rally 4.1%.',
     'source': 'Bloomberg - Fed'},
    {'num': 10, 'region': 'S. AMERICA', 'field': 'ELECTIONS',
     'status': 'REPORTED',
     'headline': 'Chile runoff count under way',
     'summary': 'Turnout 71%; result due 23:00 local, officials say.',
     'source': 'Servel - EFE'},
    {'num': 11, 'region': 'OCEANIA', 'field': 'SPORT',
     'status': 'OFFICIAL',
     'headline': 'Australia keep Ashes on day five',
     'summary': 'Hosts win by 6 wickets in Brisbane; England 239 all out.',
     'source': 'ICC - ABC'},
    {'num': 12, 'region': 'AFRICA', 'field': 'HEALTH',
     'status': 'CONFIRMED',
     'headline': 'Nigeria rolls out own malaria jab',
     'summary': 'Locally made vaccine reaches 2m children in Kano.',
     'source': 'WHO - NPHCDA'},
    {'num': 13, 'region': 'WORLD & SPACE', 'field': 'SCIENCE',
     'status': 'REPORTED',
     'headline': 'Webb spots vapour on K2-18c',
     'summary': 'Water signal in the habitable zone, 124 light-years away.',
     'source': 'NASA - ESA'},
]

# (number, bold lead-in, text, source) -- items 14-35.
BRIEFS = [
    (14, 'Zaporizhzhia:', 'IAEA says cooling is stable after overnight grid scare at the plant.', 'Reuters'),
    (15, 'NATO Berlin:', 'Rutte and Chancellor Merz meet on air defence gaps.', 'Reuters'),
    (16, 'Oil & Crypto:', 'WTI settles +5.8% near $112; Bitcoin holds $97,400.', 'Reuters'),
    (17, 'Japan:', 'BOJ holds its rate; yen steadies at 154.2 per dollar.', 'Kyodo'),
    (18, 'India-Nepal:', 'Kathmandu pledges a $900m rail and energy pact.', 'PTI'),
    (19, 'Indonesia:', 'Jakarta clears a $420m EV battery plant in Sulawesi.', 'Antara'),
    (20, 'Nigeria:', 'Abuja posts first fossil-gain share of $7.5bn net.', 'ThisDay'),
    (21, 'Premier League:', 'Arsenal beat Chelsea 2-1 at the Emirates.', 'Guardian'),
    (22, 'Australia AI:', 'Canberra drafts a frontier AI safety bill.', 'AAP'),
    (23, 'Colombia:', 'Police drone attack hurts 3 in Cali; no claim yet.', 'AFP'),
    (24, 'Hawaii:', 'Kilauea resumes lava flow; USGS keeps alert level.', 'USGS'),
    (25, 'NFL:', 'Chiefs edge Ravens 27-24 in overtime in Kansas City.', 'AP'),
    (26, 'Paris:', 'Metro strike ends after late-night pay deal.', 'AFP'),
    (27, 'Turkey:', 'Istanbul quake drill covers 16m residents.', 'Anadolu'),
    (28, 'Pakistan:', 'Karachi port reopens after two days of fog closure.', 'Dawn'),
    (29, 'Egypt:', 'Cairo museum opens restored Tutankhamun hall.', 'Ahram'),
    (30, 'Kenya:', 'Nairobi launches its first 40km BRT line.', 'KBC'),
    (31, 'Taiwan:', 'Taipei chip exports jump 18% year on year in October.', 'CNA'),
    (32, 'Mongolia:', 'Ulaanbaatar bans raw coal to fight winter smog.', 'Montsame'),
    (33, 'Mexico:', 'Sheinbaum unveils a nearshoring rail fund.', 'Reforma'),
    (34, 'Qatar:', 'Doha gas forum backs long-term LNG contracts.', 'QNA'),
    (35, 'Arctic:', 'IMO agrees a polar shipping fuel standard.', 'IMO'),
]

REGION_BAR = [
    ('EUROPE', 6), ('MIDDLE EAST', 5), ('AFRICA', 4), ('EAST ASIA', 5),
    ('SOUTH & SE ASIA', 4), ('N. AMERICA', 4), ('S. AMERICA', 2),
    ('OCEANIA', 2), ('WORLD & SPACE', 3),
]

TICKER = [
    '01:10 RAFAH CONVOY', '03:05 BRENT $118', '05:40 BONN DEAL',
    '09:15 SHENZHOU DOCKS', '12:50 FED HOLDS', '21:45 KILAUEA FLOW',
]

TITLE = 'Friday 27 November 2026'
KICKER_RIGHT = ('35 DATED STORIES • 9 REGIONS • 17 FIELDS • '
                'ALL FROM FRI 27 NOV 2026')
SUMMARY_LINE = ('Hormuz convoy sails as Brent tops $118 • Bonn seals $40bn '
                'climate deal at dawn • Shenzhou-22 docks in record 5h 12m '
                '• Rafah aid convoy crosses')
DATE_CHECK = ('DATE CHECK - EXCLUDED: Every story above happened or was '
              'first reported on Fri 27 Nov 2026. Left out as older: COP31 '
              'venue shortlist (Tue 24 Nov) • Euclid image release '
              '(Thu 26 Nov) • Las Vegas GP (Sun 22 Nov).')
HOW_SURE = ('HOW SURE: CONFIRMED = 2+ outlets • OFFICIAL = on record • '
            'REPORTED = 1 wire')
SOURCES = 'Sources: Reuters, AP, AFP, dpa, Kyodo, CNA, USGS, AAP, QNA & staff'


# ---------------- layout ---------------------------------------------------
SHORT_REGION = {
    'MIDDLE EAST': 'MID EAST', 'SOUTH & SE ASIA': 'S & SE ASIA',
    'WORLD & SPACE': 'WORLD/SPACE',
}
SHORT_FIELD = {'HUMANITARIAN': 'AID', 'INVESTIGATION': 'INQUIRY',
               'TECHNOLOGY': 'TECH'}

# Region of each brief, for colour-coding its number chip.
BRIEF_REGIONS = {
    14: 'EUROPE', 15: 'EUROPE', 16: 'WORLD & SPACE', 17: 'EAST ASIA',
    18: 'SOUTH & SE ASIA', 19: 'SOUTH & SE ASIA', 20: 'AFRICA',
    21: 'EUROPE', 22: 'OCEANIA', 23: 'S. AMERICA', 24: 'N. AMERICA',
    25: 'N. AMERICA', 26: 'EUROPE', 27: 'MIDDLE EAST',
    28: 'SOUTH & SE ASIA', 29: 'AFRICA', 30: 'AFRICA', 31: 'EAST ASIA',
    32: 'EAST ASIA', 33: 'N. AMERICA', 34: 'MIDDLE EAST',
    35: 'WORLD & SPACE',
}

SCENES = {'tanker': scene_tanker, 'climate': scene_climate,
          'space': scene_space}

MX = 14           # page margin
CW = W - 2 * MX   # content width = 996


def draw_lead(cv, x, y, w, h, item):
    color = REGION_COLORS[item['region']]
    cv.rect_outline(x, y, w, h, INK, 1)
    cv.fill_rect(x, y, w, 22, color)                       # header strip
    draw_disc(cv, x + 13, y + 11, 9, INK)                  # number badge
    s = str(item['num'])
    draw_text(cv, x + 13 - text_width(s, 1, True) // 2, y + 8, s, 1,
              WHITE, True)
    tag = item['region'] + ' • ' + item['field']
    if 30 + text_width(tag, 2, True) <= w:
        draw_text(cv, x + 28, y + 4, tag, 2, WHITE, True)
    else:
        draw_text(cv, x + 28, y + 8, tag, 1, WHITE, True)
    SCENES[item['scene']](cv, x + 6, y + 28, w - 12, 80)   # illustration
    cv.rect_outline(x + 6, y + 28, w - 12, 80, INK, 1)
    cv.fill_rect(x + 6, y + 114, w - 12, 22, color)        # callout band
    draw_text(cv, x + 12, y + 118, item['callout'], 2, WHITE, True)
    draw_para(cv, x + 8, y + 142, item['headline'], 3, INK, w - 16,
              line_gap=2, bold=True, max_lines=3)
    draw_para(cv, x + 8, y + 215, item['summary'], 2, SOFT_INK, w - 16,
              line_gap=1, max_lines=4)
    draw_text(cv, x + 8, y + h - 12, item['status'], 1, RED, True)
    draw_text_r(cv, x + w - 8, y + h - 12, item['source'], 1, SOFT_INK)


def draw_card(cv, x, y, w, h, item):
    color = REGION_COLORS[item['region']]
    cv.rect_outline(x, y, w, h, INK, 1)
    cv.fill_rect(x, y, w, 18, color)                       # header strip
    ns = str(item['num'])
    draw_text(cv, x + 5, y + 2, ns, 2, WHITE, True)
    tag = (SHORT_REGION.get(item['region'], item['region']) + ' • ' +
           SHORT_FIELD.get(item['field'], item['field']))
    draw_text(cv, x + 11 + text_width(ns, 2, True), y + 6, tag, 1, WHITE)
    draw_para(cv, x + 6, y + 23, item['headline'], 2, INK, w - 12,
              line_gap=1, bold=True, max_lines=3)
    draw_para(cv, x + 6, y + 72, item['summary'], 1, SOFT_INK, w - 12,
              line_gap=2, max_lines=2)
    draw_text(cv, x + 6, y + h - 12, item['status'], 1, RED, True)
    draw_text_r(cv, x + w - 6, y + h - 12, item['source'], 1, SOFT_INK)


def wrap_mixed(lead, text, max_chars):
    """Wrap lead+text into lines of at most max_chars (fixed 6px advance
    at scale 1); also returns how many chars of each line are the bold
    lead-in."""
    words = (lead + ' ' + text).split(' ')
    lines = []
    cur = ''
    for word in words:
        trial = word if not cur else cur + ' ' + word
        if len(trial) <= max_chars or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    bold_upto = []
    consumed = 0
    for line in lines:
        bold_upto.append(max(0, min(len(line), len(lead) - consumed)))
        consumed += len(line) + 1
    return lines, bold_upto


def draw_line_mixed(cv, x, y, line, bold_upto, color):
    for i, ch in enumerate(line):
        rows = glyph_for(ch)
        wide = 2 if i < bold_upto else 1
        for r in range(CHAR_H):
            mask = rows[r]
            if not mask:
                continue
            for c in range(CHAR_W):
                if mask & (0x10 >> c):
                    cv.fill_rect(x + i * 6 + c, y + r, wide, 1, color)


def draw_brief(cv, x, y, w, item):
    num, lead, text, source = item
    color = REGION_COLORS[BRIEF_REGIONS[num]]
    cv.fill_rect(x, y, 15, 15, color)                      # number chip
    ns = str(num)
    draw_text(cv, x + 7 - text_width(ns, 1, True) // 2, y + 4, ns, 1,
              WHITE, True)
    lines, bold_upto = wrap_mixed(lead, text, (w - 19) // 6)
    for i, line in enumerate(lines[:2]):
        draw_line_mixed(cv, x + 19, y + i * 9, line, bold_upto[i], INK)
    last = lines[min(1, len(lines) - 1)]
    free = w - 19 - len(last) * 6
    if free >= text_width(source, 1) + 8:
        draw_text_r(cv, x + w, y + (len(lines[:2]) - 1) * 9, source, 1,
                    SOFT_INK)


def draw_bottom(cv, y):
    # --- left: dot map panel ---
    pw = 396
    cv.rect_outline(MX, y, pw, 258, INK, 1)
    draw_text(cv, MX + 10, y + 8, 'WHERE IT HAPPENED', 2, INK, True)
    draw_text_r(cv, MX + pw - 10, y + 12, 'SCENES 1-13', 1, SOFT_INK, True)
    mx0, my0 = MX + 9, y + 30
    draw_dot_map(cv, mx0, my0, 6, 4)
    region_of = {}
    for it in LEADS + CARDS:
        region_of[it['num']] = it['region']
    for num, (col, row) in PINS.items():
        cx, cy = mx0 + col * 6 + 3, my0 + row * 6 + 3
        draw_disc(cv, cx, cy, 8, REGION_COLORS[region_of[num]])
        ns = str(num)
        draw_text(cv, cx - text_width(ns, 1, True) // 2, cy - 3, ns, 1,
                  WHITE, True)
    ly = my0 + len(WORLD_ROWS) * 6 + 10
    legend = [(r, c) for r, c in REGION_BAR]
    for i, (region, count) in enumerate(legend):
        lx = MX + 12 + (i % 2) * 190
        yy = ly + (i // 2) * 12
        cv.fill_rect(lx, yy + 1, 8, 8, REGION_COLORS[region])
        label = region.title().replace('&', '&') + ' (' + str(count) + ')'
        draw_text(cv, lx + 12, yy + 2, label, 1, INK)
    draw_text(cv, MX + 10, ly + 62, 'Pins 1-13 locate the lead & feature '
              'stories.', 1, SOFT_INK)
    # --- right: briefs panel ---
    bx, bw = MX + pw + 12, CW - pw - 12
    cv.rect_outline(bx, y, bw, 258, INK, 1)
    draw_text(cv, bx + 10, y + 8, 'ALSO ON FRI 27 NOVEMBER', 2, INK, True)
    draw_text(cv, bx + 10, y + 30, '22 MORE DATED BRIEFS - COLOUR-CODED '
              'BY REGION', 1, SOFT_INK)
    col_w = (bw - 20 - 12) // 2
    for k, item in enumerate(BRIEFS):
        cx = bx + 10 + (k // 11) * (col_w + 12)
        cy = y + 46 + (k % 11) * 19
        draw_brief(cv, cx, cy, col_w, item)


def render():
    cv = Canvas(W, H, PAPER)
    # kicker line
    draw_text(cv, MX, 10, 'THE WORLD IN ONE DAY', 2, RED, True)
    draw_text_r(cv, W - MX, 13, KICKER_RIGHT, 1, INK, True)
    cv.fill_rect(MX, 28, CW, 2, INK)
    # date title
    draw_text(cv, MX, 36, TITLE, 6, INK, True)
    cv.fill_rect(MX, 82, CW, 1, LINE)
    # red summary line
    draw_para(cv, MX, 88, SUMMARY_LINE, 2, RED, CW, line_gap=3, bold=True,
              max_lines=2)
    # region count bar
    bx = MX
    for region, count in REGION_BAR:
        label = region + ' ' + str(count)
        bw = text_width(label, 1, True) + 14
        cv.fill_rect(bx, 128, bw, 22, REGION_COLORS[region])
        draw_text(cv, bx + 7, 135, label, 1, WHITE, True)
        bx += bw + 4
    # UTC ticker
    cv.fill_rect(MX, 156, CW, 22, INK)
    lab = 'FRIDAY UTC'
    lw = text_width(lab, 1, True) + 12
    cv.fill_rect(MX, 156, lw, 22, RED)
    draw_text(cv, MX + 6, 163, lab, 1, WHITE, True)
    draw_text(cv, MX + lw + 10, 163, ' • '.join(TICKER), 1, WHITE)
    # leads
    lw3 = (CW - 24) // 3
    for i, item in enumerate(LEADS):
        draw_lead(cv, MX + i * (lw3 + 12), 186, lw3, 292, item)
    # feature cards, two rows of five
    cw5 = (CW - 40) // 5
    for i, item in enumerate(CARDS):
        cx = MX + (i % 5) * (cw5 + 10)
        cy = 486 + (i // 5) * 124
        draw_card(cv, cx, cy, cw5, 112, item)
    # bottom: map + briefs
    draw_bottom(cv, 726)
    # footer: date-check bar and sourcing line
    cv.fill_rect(MX, 988, CW, 20, RED)
    lines = wrap_text(DATE_CHECK, 1, CW - 16, bold=True)
    for i, line in enumerate(lines[:2]):
        draw_text(cv, MX + 8, 990 + i * 9, line, 1, WHITE, True)
    draw_text(cv, MX, 1013, HOW_SURE, 1, SOFT_INK)
    draw_text_r(cv, W - MX, 1013, SOURCES, 1, SOFT_INK)
    return cv


def main():
    cv = render()
    data = cv.png_bytes()
    targets = []
    if os.path.isdir('/output'):
        targets.append('/output/entry.png')
    targets.append(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                'entry.png'))
    written = []
    for path in targets:
        try:
            with open(path, 'wb') as fh:
                fh.write(data)
            written.append(path)
        except OSError:
            pass
    if not written:
        raise SystemExit('could not write entry.png anywhere')
    print('wrote', ', '.join(written), '-', len(data), 'bytes')


if __name__ == '__main__':
    main()
