#!/usr/bin/env python3
"""The World in One Day -- Friday 27 November 2026.

A dense broadsheet front page that sums up one day of fictional
world news into a single 1024 x 1024 PNG: three illustrated lead
stories, ten numbered feature cards, a dot-matrix world map with
pins, and a tail of one-line briefs -- 35 dated stories in all.

The program is fully self-contained. It uses only the Python
standard library, reads no input files except the glyph bitmaps
in glyphs.py and the map grid in mapdata.py (both plain sibling
modules, imported normally), and never touches the network.
Lettering is stamped from glyph bitmaps rendered at build time
from DejaVu Sans and Liberation Sans. Every picture element is
rasterised by hand into a pixel buffer and the PNG is packed with
zlib and struct. No randomness, no clock: two runs give
byte-identical output.
"""

import base64
import os
import struct
import sys
import zlib
from math import cos, pi, sin, sqrt

# The sibling data modules live next to this file. Under
# `python -P` the script's own directory is not on sys.path,
# so add it explicitly (from __file__, nothing dynamic) before
# the plain static imports below.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import glyphs
import mapdata

# ---------------------------------------------------------------------------
# Sheet geometry and the ink palette
# ---------------------------------------------------------------------------
SHEET = 1024                    # the page is square
PAD = 30                        # outer margin on every side
FAR = SHEET - PAD               # right edge of the printed area
WIDTH = FAR - PAD               # printed width (964)

STOCK = (247, 243, 234)         # warm off-white paper
CARD = (255, 253, 247)          # card fill, a touch lighter
INK = (26, 26, 26)              # body black
FAINT = (74, 70, 62)            # secondary text
RED = (179, 32, 42)             # the paper's accent red
NAVY = (27, 42, 66)             # bars, badges, pills
GOLD = (198, 148, 38)           # small highlights
STRIP = (229, 230, 223)         # pale strip behind the UTC line
SEA = (196, 208, 210)           # ocean tint used inside scenes
SKY = (203, 216, 220)

# One colour per region, shared by the region bar, the map dots,
# the legend and the tick beside every brief.
REGION_PAINT = {
    "E": (58, 124, 196),        # Europe
    "M": (198, 44, 52),         # Middle East
    "F": (46, 150, 84),         # Africa
    "S": (140, 70, 170),        # East Asia
    "H": (232, 164, 32),        # South & SE Asia
    "N": (38, 84, 124),         # North America
    "L": (224, 122, 58),        # South America
    "O": (24, 148, 156),        # Oceania
    "W": (118, 118, 112),       # World & Space
}


# ---------------------------------------------------------------------------
# PNG packing: a single IDAT, filter-0 rows, correct CRCs
# ---------------------------------------------------------------------------
def _pack_chunk(kind, body):
    crc = zlib.crc32(kind + body) & 0xFFFFFFFF
    return (struct.pack(">I", len(body)) + kind + body
            + struct.pack(">I", crc))


def save_png(path, width, height, pixels):
    stride = width * 3
    raw = bytearray()
    for y in range(height):
        raw.append(0)
        raw += pixels[y * stride:(y + 1) * stride]
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    blob = (b"\x89PNG\r\n\x1a\n" + _pack_chunk(b"IHDR", ihdr)
            + _pack_chunk(b"IDAT", zlib.compress(bytes(raw), 6))
            + _pack_chunk(b"IEND", b""))
    with open(path, "wb") as fh:
        fh.write(blob)


# ---------------------------------------------------------------------------
# Sheet: an RGB pixel buffer plus the small set of painters the page
# needs. Coordinates are plain pixels; box corners are inclusive.
# ---------------------------------------------------------------------------
class Sheet:
    def __init__(self, width, height, base):
        self.width = width
        self.height = height
        self.px = bytearray(bytes(base) * (width * height))

    def _run(self, y, xa, xb, colour):
        """Paint one horizontal run, clipped to the sheet."""
        if y < 0 or y >= self.height:
            return
        xa = max(0, int(xa))
        xb = min(self.width - 1, int(xb))
        if xb < xa:
            return
        at = (y * self.width + xa) * 3
        self.px[at:at + (xb - xa + 1) * 3] = bytes(colour) * (xb - xa + 1)

    def mix(self, x, y, colour, alpha):
        """Alpha-blend a single pixel (used by the glyph stamper)."""
        if alpha <= 0 or not (0 <= x < self.width and 0 <= y < self.height):
            return
        at = (y * self.width + x) * 3
        if alpha >= 255:
            self.px[at:at + 3] = bytes(colour)
            return
        keep = 255 - alpha
        for i in range(3):
            self.px[at + i] = (colour[i] * alpha
                               + self.px[at + i] * keep) // 255

    def box(self, xa, ya, xb, yb, colour):
        xa, ya, xb, yb = (int(round(v)) for v in (xa, ya, xb, yb))
        for y in range(max(0, ya), min(self.height - 1, yb) + 1):
            self._run(y, xa, xb, colour)

    def edge(self, xa, ya, xb, yb, colour, thick=2):
        self.box(xa, ya, xb, ya + thick - 1, colour)
        self.box(xa, yb - thick + 1, xb, yb, colour)
        self.box(xa, ya, xa + thick - 1, yb, colour)
        self.box(xb - thick + 1, ya, xb, yb, colour)

    def disc(self, cx, cy, rad, colour):
        self.ellipse(cx - rad, cy - rad, cx + rad, cy + rad, colour)

    def ellipse(self, xa, ya, xb, yb, colour):
        cx, cy = (xa + xb) / 2.0, (ya + yb) / 2.0
        rx, ry = (xb - xa) / 2.0, (yb - ya) / 2.0
        if rx <= 0 or ry <= 0:
            self.box(xa, ya, xb, yb, colour)
            return
        for y in range(int(ya), int(yb) + 1):
            frac = (y - cy) / ry
            if abs(frac) > 1.0:
                continue
            half = rx * sqrt(1.0 - frac * frac)
            self._run(y, cx - half, cx + half, colour)

    def ring(self, cx, cy, rad, colour, thick, inside):
        self.disc(cx, cy, rad, colour)
        self.disc(cx, cy, rad - thick, inside)

    def tri(self, points, colour):
        pts = [(float(a), float(b)) for a, b in points]
        top = max(0, int(min(b for _, b in pts)))
        bottom = min(self.height - 1, int(max(b for _, b in pts)))
        n = len(pts)
        for y in range(top, bottom + 1):
            scan = y + 0.5
            hits = []
            for i in range(n):
                ax, ay = pts[i]
                bx, by = pts[(i + 1) % n]
                if ay == by:
                    continue
                if (ay <= scan < by) or (by <= scan < ay):
                    hits.append(ax + (scan - ay) * (bx - ax) / (by - ay))
            hits.sort()
            for k in range(0, len(hits) - 1, 2):
                self._run(y, hits[k], hits[k + 1], colour)

    def seg(self, xa, ya, xb, yb, colour, thick=2):
        """Thick segment with round caps, drawn as a chain of discs."""
        dist = sqrt((xb - xa) ** 2 + (yb - ya) ** 2)
        steps = max(1, int(dist * 1.5))
        rad = thick / 2.0
        for i in range(steps + 1):
            t = i / steps
            self.disc(xa + (xb - xa) * t, ya + (yb - ya) * t, rad, colour)

    def polyline(self, points, colour, thick=2):
        for i in range(len(points) - 1):
            self.seg(points[i][0], points[i][1],
                     points[i + 1][0], points[i + 1][1], colour, thick)

    def dash_arc(self, cx, cy, rad, a0, a1, colour, thick=3, dash=0.55):
        """Arc from angle a0 to a1 (radians, 0 = east, up is negative
        y), drawn as short dashes along the circle."""
        steps = 60
        for i in range(steps):
            if (i * dash) % 1.0 >= dash:
                continue
            t0 = a0 + (a1 - a0) * i / steps
            t1 = a0 + (a1 - a0) * (i + 1) / steps
            self.seg(cx + rad * cos(t0), cy - rad * sin(t0),
                     cx + rad * cos(t1), cy - rad * sin(t1),
                     colour, thick)


# ---------------------------------------------------------------------------
# Lettering: glyph bitmaps live in glyphs.py as
# GLYPHS[face][size][char] = [advance, off_x, off_y, w, h, payload]
# with offsets measured from the PIL draw point (left edge, top of
# the ascender line). The cache holds each decoded bitmap once.
# ---------------------------------------------------------------------------
_glyph_cache = {}


def _lookup(face, size, ch):
    adv, ox, oy, w, h, packed = glyphs.GLYPHS[face][size][ch]
    if not packed:
        return adv, ox, oy, w, h, None
    key = (face, size, ch)
    if key not in _glyph_cache:
        _glyph_cache[key] = zlib.decompress(
            base64.b85decode(packed.encode("ascii")))
    return adv, ox, oy, w, h, _glyph_cache[key]


def measure(face, size, text):
    table = glyphs.GLYPHS[face][size]
    return sum(table[ch][0] for ch in text)


def stamp(sheet, x, y, text, face, size, colour):
    """Draw text with (x, y) as the draw point; returns the end x."""
    pen = float(x)
    top = int(round(y))
    for ch in text:
        adv, ox, oy, w, h, alpha = _lookup(face, size, ch)
        if alpha is not None:
            gx = int(round(pen)) + ox
            for row in range(h):
                line = alpha[row * w:(row + 1) * w]
                if not line.strip(b"\x00"):
                    continue
                for i, a in enumerate(line):
                    if a:
                        sheet.mix(gx + i, top + oy + row, colour, a)
        pen += adv
    return pen


def stamp_mid(sheet, centre, y, text, face, size, colour):
    stamp(sheet, centre - measure(face, size, text) / 2.0, y,
          text, face, size, colour)


def stamp_end(sheet, right, y, text, face, size, colour):
    stamp(sheet, right - measure(face, size, text), y,
          text, face, size, colour)


def stamp_spread(sheet, centre, y, text, face, size, colour, tracking):
    table = glyphs.GLYPHS[face][size]
    total = sum(table[ch][0] for ch in text) + tracking * (len(text) - 1)
    pen = centre - total / 2.0
    for ch in text:
        stamp(sheet, pen, y, ch, face, size, colour)
        pen += table[ch][0] + tracking


def wrap_lines(text, face, size, limit):
    """Greedy word wrap against glyph advances."""
    lines, current = [], ""
    for word in text.split(" "):
        trial = word if not current else current + " " + word
        if measure(face, size, trial) <= limit or not current:
            current = trial
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def pick_size(text, face, start, floor, limit):
    """Largest size at or below `start` whose single line fits."""
    size = start
    while size > floor and measure(face, size, text) > limit:
        size -= 1
    return size


def num_disc(sheet, cx, cy, rad, number, fill=NAVY):
    """Numbered circle: white halo, coloured fill, white numeral."""
    sheet.disc(cx, cy, rad + 1.5, (255, 255, 255))
    sheet.disc(cx, cy, rad, fill)
    label = str(number)
    size = 13 if rad >= 10 else 11
    stamp_mid(sheet, cx, cy - size * 0.36, label, "lb", size,
              (255, 255, 255))


def pill(sheet, right, y, text, fill=NAVY, face="lb", size=11, h=16):
    """Small status pill, right-aligned at `right`, top at y."""
    w = measure(face, size, text) + 14
    sheet.box(right - w, y, right, y + h, fill)
    stamp_mid(sheet, right - w / 2.0, y + (h - size) / 2.0 - 1,
              text, face, size, (255, 255, 255))
    return w


# ---------------------------------------------------------------------------
# Lead-story scenes. Each fills a box (x, y, w, h) and is framed by
# the caller. They are flat silhouette pictures in the house style.
# ---------------------------------------------------------------------------
def _hull(sheet, x, keel, scale, tone):
    """Oil tanker side view; keel is the waterline y."""
    beam, hull_h = 300 * scale, 30 * scale
    sheet.tri([(x, keel - hull_h), (x + 0.85 * beam, keel - hull_h),
               (x + beam, keel - 0.3 * hull_h), (x + 0.93 * beam, keel),
               (x + 0.07 * beam, keel), (x, keel - 0.28 * hull_h)], tone)
    sheet.box(x + 0.12 * beam, keel - hull_h - 7 * scale,
              x + 0.60 * beam, keel - hull_h, tone)          # deck strip
    sheet.box(x + 0.05 * beam, keel - hull_h - 46 * scale,
              x + 0.19 * beam, keel - hull_h - 7 * scale, tone)  # castle
    sheet.box(x + 0.08 * beam, keel - hull_h - 58 * scale,
              x + 0.16 * beam, keel - hull_h - 46 * scale, tone)
    sheet.seg(x + 0.44 * beam, keel - hull_h - 7 * scale,
              x + 0.44 * beam, keel - hull_h - 50 * scale,
              tone, max(2, int(4 * scale)))                  # mast


def scene_convoy(sheet, x, y, w, h):
    horizon = y + int(h * 0.62)
    sheet.box(x, y, x + w, horizon, SKY)
    sheet.box(x, y, x + w, y + int(h * 0.30), (214, 224, 226))
    sheet.box(x, horizon, x + w, y + h, (43, 74, 94))
    sheet.box(x, horizon, x + w, horizon + 5, (33, 58, 74))
    for wx in range(x + 26, x + w - 40, 64):               # wave ticks
        sheet.seg(wx, horizon + 12, wx + 22, horizon + 12, (86, 122, 140), 2)
        sheet.seg(wx + 30, horizon + 24, wx + 52, horizon + 24,
                  (86, 122, 140), 2)
    _hull(sheet, x + 18, y + h - 8, 0.52, (30, 33, 38))
    _hull(sheet, x + w - 150, y + h - 16, 0.34, (52, 57, 63))
    # Escort warship ahead of the convoy, grey hull and mast.
    ex, ey = x + w - 66, y + h - 10
    sheet.tri([(ex - 34, ey), (ex + 30, ey), (ex + 22, ey - 12),
               (ex - 20, ey - 12)], (96, 104, 112))
    sheet.box(ex - 8, ey - 26, ex + 6, ey - 12, (96, 104, 112))
    sheet.seg(ex - 2, ey - 26, ex - 2, ey - 38, (96, 104, 112), 3)
    # Dashed safe lane curving through the strait, arrow pointing on.
    sheet.dash_arc(x + w - 84, y + h - 20, 34, pi * 0.95, pi * 0.08,
                   GOLD, 3)
    sheet.tri([(x + w - 116, y + h - 24), (x + w - 100, y + h - 27),
               (x + w - 108, y + h - 13)], GOLD)
    for bx in range(x + 30, x + w - 16, 42):               # lane buoys
        sheet.ellipse(bx - 5, y + h - 11, bx + 5, y + h - 3, GOLD)
        sheet.box(bx - 5, y + h - 8, bx + 5, y + h - 6, (255, 255, 255))


def scene_oil(sheet, x, y, w, h):
    sheet.box(x, y, x + w, y + h, (216, 226, 230))
    base = y + h
    # City skyline in two depths.
    far = [(0.02, 0.52), (0.10, 0.38), (0.18, 0.58), (0.27, 0.34),
           (0.36, 0.50), (0.46, 0.30), (0.55, 0.46), (0.64, 0.36),
           (0.73, 0.54), (0.82, 0.32), (0.90, 0.48), (0.97, 0.40)]
    for fx, fh in far:
        sheet.box(x + fx * w, base - fh * h, x + (fx + 0.07) * w, base,
                  (148, 168, 178))
    near = [(0.06, 0.34), (0.22, 0.26), (0.40, 0.38), (0.58, 0.24),
            (0.76, 0.33), (0.90, 0.27)]
    for fx, fh in near:
        sheet.box(x + fx * w, base - fh * h, x + (fx + 0.09) * w, base,
                  (52, 66, 80))
    # The day's chart: a jagged red climb across the whole scene.
    pts = [(x + 0.04 * w, base - 0.16 * h), (x + 0.20 * w, base - 0.28 * h),
           (x + 0.34 * w, base - 0.22 * h), (x + 0.50 * w, base - 0.46 * h),
           (x + 0.64 * w, base - 0.40 * h), (x + 0.80 * w, base - 0.64 * h),
           (x + 0.94 * w, base - 0.82 * h)]
    sheet.polyline(pts, RED, 5)
    tip = pts[-1]
    sheet.tri([(tip[0] + 4, tip[1] + 2), (tip[0] - 12, tip[1] + 4),
               (tip[0] + 1, tip[1] + 16)], RED)


def scene_lights(sheet, x, y, w, h):
    sheet.box(x, y, x + w, y + h, (24, 30, 46))              # night sky
    base = y + h
    blocks = [(0.00, 0.55), (0.11, 0.72), (0.22, 0.48), (0.33, 0.66),
              (0.45, 0.52), (0.56, 0.76), (0.68, 0.46), (0.78, 0.62),
              (0.89, 0.54)]
    for fx, fh in blocks:
        bx, bw = x + fx * w, 0.10 * w
        top = base - fh * h
        sheet.box(bx, top, bx + bw, base, (10, 12, 18))
        # Windows relighting block by block after the blackout.
        for wy in range(int(top) + 6, base - 6, 11):
            for wx in range(int(bx) + 5, int(bx + bw) - 5, 12):
                if (wx * 7 + wy * 13) % 29 < 7:
                    sheet.box(wx, wy, wx + 3, wy + 4, GOLD)
    # A warm glow rising over the recovering city.
    for i in range(5):
        sheet.disc(x + w * 0.5, base - 4 - i * 3, 26 - i * 4,
                   (232, 178, 92))
    sheet.box(x, base - 3, x + w, base, (6, 8, 12))


# ---------------------------------------------------------------------------
# Card icons: small silhouettes drawn inside box (x, y, s).
# ---------------------------------------------------------------------------
def icon_chart(sheet, x, y, s, accent):
    sheet.seg(x + 0.10 * s, y + 0.06 * s, x + 0.10 * s, y + 0.92 * s, INK, 3)
    sheet.seg(x + 0.10 * s, y + 0.92 * s, x + 0.96 * s, y + 0.92 * s, INK, 3)
    pts = [(x + 0.18 * s, y + 0.30 * s), (x + 0.40 * s, y + 0.42 * s),
           (x + 0.56 * s, y + 0.36 * s), (x + 0.86 * s, y + 0.72 * s)]
    sheet.polyline(pts, accent, 4)
    tx, ty = pts[-1]
    sheet.tri([(tx, ty), (tx - 0.15 * s, ty - 0.02 * s),
               (tx - 0.03 * s, ty - 0.15 * s)], accent)


def icon_lens(sheet, x, y, s):
    cx, cy = x + 0.42 * s, y + 0.42 * s
    sheet.ring(cx, cy, 0.30 * s, INK, 4, CARD)
    sheet.seg(cx + 0.20 * s, cy + 0.20 * s, cx + 0.44 * s, cy + 0.44 * s,
              INK, 4)
    sheet.disc(cx - 0.06 * s, cy - 0.08 * s, 0.06 * s, RED)


def icon_bank(sheet, x, y, s):
    sheet.tri([(x + 0.04 * s, y + 0.34 * s), (x + 0.50 * s, y + 0.04 * s),
               (x + 0.96 * s, y + 0.34 * s)], INK)
    for fx in (0.12, 0.34, 0.56, 0.78):
        sheet.box(x + fx * s, y + 0.44 * s, x + (fx + 0.10) * s, y + 0.82 * s,
                  INK)
    sheet.box(x + 0.04 * s, y + 0.86 * s, x + 0.96 * s, y + 0.96 * s, INK)


def icon_leaf(sheet, x, y, s):
    sheet.ellipse(x + 0.10 * s, y + 0.12 * s, x + 0.90 * s, y + 0.82 * s,
                  (46, 150, 84))
    sheet.ellipse(x + 0.26 * s, y + 0.28 * s, x + 0.74 * s, y + 0.66 * s,
                  CARD)
    sheet.seg(x + 0.20 * s, y + 0.78 * s, x + 0.80 * s, y + 0.22 * s,
              (46, 150, 84), 3)


def icon_rocket(sheet, x, y, s):
    cx = x + 0.5 * s
    sheet.tri([(cx, y + 0.03 * s), (cx + 0.15 * s, y + 0.30 * s),
               (cx + 0.15 * s, y + 0.62 * s), (cx - 0.15 * s, y + 0.62 * s),
               (cx - 0.15 * s, y + 0.30 * s)], INK)
    sheet.disc(cx, y + 0.32 * s, 0.06 * s, STOCK)
    sheet.tri([(cx - 0.15 * s, y + 0.50 * s), (cx - 0.30 * s, y + 0.74 * s),
               (cx - 0.15 * s, y + 0.74 * s)], RED)
    sheet.tri([(cx + 0.15 * s, y + 0.50 * s), (cx + 0.30 * s, y + 0.74 * s),
               (cx + 0.15 * s, y + 0.74 * s)], RED)
    sheet.tri([(cx - 0.07 * s, y + 0.98 * s), (cx, y + 0.74 * s),
               (cx + 0.07 * s, y + 0.98 * s)], (232, 100, 30))


def icon_dove(sheet, x, y, s):
    sheet.tri([(x + 0.20 * s, y + 0.56 * s), (x + 0.02 * s, y + 0.44 * s),
               (x + 0.05 * s, y + 0.74 * s), (x + 0.24 * s, y + 0.72 * s)],
              INK)
    sheet.ellipse(x + 0.16 * s, y + 0.40 * s, x + 0.78 * s, y + 0.78 * s, INK)
    sheet.tri([(x + 0.32 * s, y + 0.48 * s), (x + 0.14 * s, y + 0.12 * s),
               (x + 0.54 * s, y + 0.38 * s)], INK)
    sheet.ellipse(x + 0.60 * s, y + 0.20 * s, x + 0.88 * s, y + 0.48 * s, INK)
    sheet.tri([(x + 0.85 * s, y + 0.30 * s), (x + 0.99 * s, y + 0.37 * s),
               (x + 0.85 * s, y + 0.42 * s)], RED)


def icon_train(sheet, x, y, s):
    sheet.box(x + 0.16 * s, y + 0.10 * s, x + 0.84 * s, y + 0.82 * s, INK)
    sheet.box(x + 0.26 * s, y + 0.22 * s, x + 0.74 * s, y + 0.46 * s, CARD)
    sheet.box(x + 0.16 * s, y + 0.56 * s, x + 0.84 * s, y + 0.62 * s, GOLD)
    sheet.disc(x + 0.32 * s, y + 0.72 * s, 0.05 * s, CARD)
    sheet.disc(x + 0.68 * s, y + 0.72 * s, 0.05 * s, CARD)
    sheet.seg(x + 0.06 * s, y + 0.92 * s, x + 0.94 * s, y + 0.92 * s, INK, 3)


def icon_gavel(sheet, x, y, s):
    sheet.box(x + 0.10 * s, y + 0.82 * s, x + 0.90 * s, y + 0.92 * s, INK)
    sheet.seg(x + 0.18 * s, y + 0.78 * s, x + 0.82 * s, y + 0.14 * s, INK, 4)
    sheet.box(x + 0.62 * s, y + 0.04 * s, x + 0.96 * s, y + 0.38 * s, RED)


def icon_bat(sheet, x, y, s):
    cx, cy = x + 0.38 * s, y + 0.55 * s
    sheet.disc(cx, cy, 0.30 * s, RED)
    sheet.seg(cx - 0.16 * s, cy - 0.24 * s, cx - 0.16 * s, cy + 0.24 * s,
              (255, 255, 255), 2)
    sheet.seg(cx + 0.16 * s, cy - 0.24 * s, cx + 0.16 * s, cy + 0.24 * s,
              (255, 255, 255), 2)
    sheet.tri([(x + 0.66 * s, y + 0.10 * s), (x + 0.78 * s, y + 0.14 * s),
               (x + 0.60 * s, y + 0.72 * s), (x + 0.50 * s, y + 0.66 * s)],
              (150, 108, 58))


def icon_storm(sheet, x, y, s):
    sheet.ellipse(x + 0.10 * s, y + 0.14 * s, x + 0.58 * s, y + 0.50 * s, INK)
    sheet.ellipse(x + 0.40 * s, y + 0.04 * s, x + 0.90 * s, y + 0.50 * s, INK)
    sheet.box(x + 0.10 * s, y + 0.34 * s, x + 0.90 * s, y + 0.50 * s, INK)
    for t in (0.26, 0.50, 0.74):
        sheet.seg(x + t * s, y + 0.60 * s, x + (t - 0.09) * s, y + 0.88 * s,
                  (86, 122, 140), 4)


ICONS = {
    "chart": icon_chart, "lens": icon_lens, "bank": icon_bank,
    "leaf": icon_leaf, "rocket": icon_rocket, "dove": icon_dove,
    "train": icon_train, "gavel": icon_gavel, "bat": icon_bat,
    "storm": icon_storm,
}


# ---------------------------------------------------------------------------
# The day's stories. Every item carries its region code (see
# REGION_PAINT) and field so the header statistics and the region bar
# are tallied from the data itself and can never disagree with the
# page. Leads and cards are numbered 1-13 to match the map pins;
# briefs continue the numbering to the full count.
# ---------------------------------------------------------------------------
REGION_ORDER = [
    ("E", "EUROPE"), ("M", "MIDDLE EAST"), ("F", "AFRICA"),
    ("S", "EAST ASIA"), ("H", "SOUTH & SE ASIA"), ("N", "N. AMERICA"),
    ("L", "S. AMERICA"), ("O", "OCEANIA"), ("W", "WORLD & SPACE"),
]
REGION_NAME = dict(REGION_ORDER)

LEADS = [
    {
        "num": 1, "tag": "HORMUZ • ENERGY", "region": "M",
        "field": "Energy", "status": "OFFICIAL", "scene": "convoy",
        "callout": "CONVOY SAILS", "callout_bg": RED,
        "headline": "First escorted convoy sails the Strait of Hormuz",
        "summary": "US and Gulf warships shepherd 12 tankers through "
                   "as the closure enters day two.",
        "source": "Reuters • AP",
    },
    {
        "num": 2, "tag": "LONDON • MARKETS", "region": "E",
        "field": "Markets", "status": "REPORTED", "scene": "oil",
        "callout": "$140 A BARREL", "callout_bg": NAVY,
        "headline": "Brent crude tops $140 as the oil shock deepens",
        "summary": "Oil jumps again on the convoy news; airlines slide "
                   "and gold hits a record high.",
        "source": "Reuters • Bloomberg",
    },
    {
        "num": 3, "tag": "KYIV • ENERGY WAR", "region": "E",
        "field": "War", "status": "REPORTED", "scene": "lights",
        "callout": "LIGHTS RETURN", "callout_bg": RED,
        "headline": "Kyiv restores power to half the city after blackout",
        "summary": "Crews reconnect two substations; heating returns to "
                   "hospitals first as repairs race on.",
        "source": "AP • Reuters",
    },
]

CARDS = [
    {"num": 4, "tag": "SEOUL • MARKETS", "region": "S",
     "field": "Markets", "status": "REPORTED", "icon": "chart",
     "title": "KOSPI steadies as oil eases from its peak",
     "summary": "Seoul ends flat after a wild session.",
     "source": "Reuters"},
    {"num": 5, "tag": "RIYADH • INVESTIGATION", "region": "M",
     "field": "Security", "status": "REPORTED", "icon": "lens",
     "title": "Riyadh probe names drone parts supplier",
     "summary": "Investigators trace tower-drone parts to a Gulf dealer.",
     "source": "Al Jazeera"},
    {"num": 6, "tag": "WASHINGTON • ECONOMY", "region": "N",
     "field": "Economy", "status": "OFFICIAL", "icon": "bank",
     "title": "Fed holds rates, pledges oil-shock backstop",
     "summary": "Powell says the Fed stands ready to lend calm.",
     "source": "Reuters"},
    {"num": 7, "tag": "ANTALYA • CLIMATE", "region": "M",
     "field": "Climate", "status": "REPORTED", "icon": "leaf",
     "title": "COP31 talks resume after the collapse",
     "summary": "Ministers return to Antalya for a final 48 hours.",
     "source": "AFP"},
    {"num": 8, "tag": "CHINA • SPACE", "region": "S",
     "field": "Space", "status": "OFFICIAL", "icon": "rocket",
     "title": "Shenzhou-24 crew ends second spacewalk",
     "summary": "Two taikonauts fit a new solar wing in six hours.",
     "source": "Xinhua"},
    {"num": 9, "tag": "CAIRO • DIPLOMACY", "region": "M",
     "field": "Diplomacy", "status": "CONFIRMED", "icon": "dove",
     "title": "Gaza talks agree a 72-hour truce",
     "summary": "Cairo deal pauses strikes from midnight tonight.",
     "source": "AP"},
    {"num": 10, "tag": "MUMBAI • FLOODS", "region": "H",
     "field": "Disaster", "status": "REPORTED", "icon": "train",
     "title": "Mumbai trains restart as floodwaters recede",
     "summary": "Suburban lines reopen after a day underwater.",
     "source": "Reuters"},
    {"num": 11, "tag": "NEW YORK • TECH TRIAL", "region": "N",
     "field": "Tech", "status": "OFFICIAL", "icon": "gavel",
     "title": "Huawei trial: prosecutors show emails",
     "summary": "Day two hears the firm's own messages read aloud.",
     "source": "AP"},
    {"num": 12, "tag": "ADELAIDE • CRICKET", "region": "O",
     "field": "Sport", "status": "OFFICIAL", "icon": "bat",
     "title": "Australia level the Ashes at Adelaide",
     "summary": "Hosts chase 312 to square the series 1-1.",
     "source": "BBC"},
    {"num": 13, "tag": "CORNWALL • WEATHER", "region": "E",
     "field": "Weather", "status": "REPORTED", "icon": "storm",
     "title": "Storm Bella floods Cornwall; rail lines shut",
     "summary": "Winds of 90 mph cut power to 20,000 homes.",
     "source": "BBC"},
]

# (place, text, source, region, field) -- numbered 14 onwards.
BRIEFS = [
    ("TOKYO", "Shinkansen resumes after quake safety checks",
     "Kyodo", "S", "Disaster"),
    ("BERLIN", "Germany taps its strategic oil reserve",
     "Reuters", "E", "Energy"),
    ("WASHINGTON", "US airlines cancel Gulf routes for a week",
     "AP", "N", "Aviation"),
    ("VANUATU", "Aftershock M5.9 rattles Vanuatu; no tsunami",
     "USGS", "O", "Disaster"),
    ("MADRID", "Barcelona beat Sevilla 2-0 to stay top",
     "Reuters", "E", "Sport"),
    ("BOSTON", "Celtics edge Nuggets 112-109 in overtime",
     "AP", "N", "Sport"),
    ("BRASILIA", "Brazil launches a rainforest carbon fund",
     "Reuters", "L", "Environment"),
    ("KHARTOUM", "WHO ships cholera vaccines to Sudan",
     "WHO", "F", "Health"),
    ("SYDNEY", "Mass coral spawning recorded on the Reef",
     "ABC", "O", "Science"),
    ("TORONTO", "Toronto digs out after the season's first blizzard",
     "CBC", "N", "Weather"),
    ("SANTIAGO", "Chile copper miners resume work after pay deal",
     "Reuters", "L", "Labour"),
    ("JAKARTA", "First stone laid for Jakarta's giant sea wall",
     "Antara", "H", "Climate"),
    ("DELHI", "Delhi smog eases after overnight rain",
     "Reuters", "H", "Environment"),
    ("GENEVA", "WHO clears a fast new TB test",
     "WHO", "W", "Health"),
    ("SPACE", "Webb telescope spots the earliest galaxy yet",
     "NASA", "W", "Science"),
    ("ROME", "Rome opera opens its season with Verdi",
     "ANSA", "E", "Culture"),
    ("LUXOR", "Pharaoh's tomb opens to the public",
     "AFP", "F", "Culture"),
    ("DRESDEN", "Dresden fab ships its first chips",
     "Reuters", "E", "Tech"),
    ("PACIFIC", "Undersea cable repaired after quake damage",
     "AP", "W", "Tech"),
    ("SEOUL", "Samsung unveils its fastest AI chip",
     "Reuters", "S", "Tech"),
    ("LIMA", "Peru quake M6.1 causes no damage",
     "USGS", "L", "Disaster"),
    ("NAIROBI", "Kenya launches a digital shilling pilot",
     "AFP", "F", "Economy"),
]

# The UTC timeline strip: (time, short label) for seven key moments.
UTC_ITEMS = [
    ("02:15", "Convoy sails"), ("04:30", "Brent $140"),
    ("07:50", "Kyiv lights on"), ("10:20", "Gaza truce"),
    ("13:45", "COP31 resumes"), ("18:10", "Shenzhou walk"),
    ("21:30", "Ashes level"),
]


def _tally():
    """Region counts and field count across every story on the page."""
    counts = {code: 0 for code, _ in REGION_ORDER}
    fields = set()
    for item in LEADS + CARDS:
        counts[item["region"]] += 1
        fields.add(item["field"])
    for _place, _text, _src, region, field in BRIEFS:
        counts[region] += 1
        fields.add(field)
    total = sum(counts.values())
    return counts, len(fields), total


REGION_COUNTS, FIELD_COUNT, STORY_TOTAL = _tally()


# ---------------------------------------------------------------------------
# Section painters
# ---------------------------------------------------------------------------
def paint_masthead(sheet):
    # Top strip: paper name on the left, the day's statistics right.
    stamp(sheet, PAD, 10, "THE WORLD IN ONE DAY", "lb", 14, INK)
    stats = (f"{STORY_TOTAL} DATED STORIES • {len(REGION_ORDER)} REGIONS "
             f"• {FIELD_COUNT} FIELDS • ALL FROM FRI 27 NOV 2026")
    stamp_end(sheet, FAR, 12, stats, "lb", 12, FAINT)
    sheet.box(PAD, 30, FAR, 32, INK)
    sheet.box(PAD, 36, FAR, 36, INK)

    # The date itself, as large as the measure allows.
    date = "Friday 27 November 2026"
    size = pick_size(date, "db", 54, 44, WIDTH)
    stamp_mid(sheet, SHEET // 2, 44, date, "db", size, INK)

    # One-line digest of the three leads.
    digest = ("First convoy sails the Strait • Brent tops $140 a barrel "
              "• Kyiv's lights return")
    stamp_mid(sheet, SHEET // 2, 106, digest, "lb", 15, RED)

    # Region bar: one slot per region, counts tallied from the data.
    bar_y, bar_h = 128, 24
    sheet.box(PAD, bar_y, FAR, bar_y + bar_h, NAVY)
    slot = WIDTH / len(REGION_ORDER)
    for i, (code, name) in enumerate(REGION_ORDER):
        cx = PAD + slot * (i + 0.5)
        label = f"{name} {REGION_COUNTS[code]}"
        size = pick_size(label, "lb", 12, 11, slot - 8)
        stamp_mid(sheet, cx, bar_y + (bar_h - size) / 2.0 - 1,
                  label, "lb", size, (255, 255, 255))
        if i:
            vx = int(PAD + slot * i)
            sheet.box(vx, bar_y + 4, vx, bar_y + bar_h - 4, (74, 94, 124))

    # UTC timeline of the day's key moments.
    strip_y, strip_h = 158, 20
    sheet.box(PAD, strip_y, FAR, strip_y + strip_h, STRIP)
    sheet.box(PAD, strip_y, PAD + 106, strip_y + strip_h, RED)
    stamp_mid(sheet, PAD + 53, strip_y + 4, "FRIDAY UTC",
              "lb", 12, (255, 255, 255))
    pen = PAD + 116.0
    for i, (when, what) in enumerate(UTC_ITEMS):
        if i:
            pen = stamp(sheet, pen, strip_y + 4, " • ", "lr", 12, FAINT)
        pen = stamp(sheet, pen, strip_y + 4, when, "lb", 12, INK)
        pen = stamp(sheet, pen, strip_y + 4, " " + what, "lr", 12, INK)


SCENES = {"convoy": scene_convoy, "oil": scene_oil,
          "lights": scene_lights}


def paint_lead(sheet, x, y, w, item):
    h = 206
    sheet.box(x, y, x + w, y + h, CARD)
    sheet.edge(x, y, x + w, y + h, INK, 2)
    sheet.box(x, y, x + w, y + 4, REGION_PAINT[item["region"]])
    num_disc(sheet, x + 17, y + 21, 11, item["num"])
    stamp(sheet, x + 34, y + 14, item["tag"], "lb", 13, INK)
    pill(sheet, x + w - 10, y + 12, item["status"])

    sx, sy, sw, sh = x + 10, y + 34, w - 20, 60
    SCENES[item["scene"]](sheet, sx, sy, sw, sh)
    sheet.edge(sx, sy, sx + sw, sy + sh, INK, 2)

    sheet.box(x + 10, y + 98, x + w - 10, y + 118, item["callout_bg"])
    stamp_mid(sheet, x + w / 2.0, y + 101, item["callout"],
              "lb", 15, (255, 255, 255))

    lines = wrap_lines(item["headline"], "lb", 18, w - 20)
    size = 18
    while len(lines) > 2 and size > 15:
        size -= 1
        lines = wrap_lines(item["headline"], "lb", size, w - 20)
    ty = y + 123
    for line in lines[:2]:
        stamp(sheet, x + 10, ty, line, "lb", size, INK)
        ty += size + 2

    body = wrap_lines(item["summary"], "lr", 13, w - 20)
    bsize = 13
    while len(body) > 2 and bsize > 11:
        bsize -= 1
        body = wrap_lines(item["summary"], "lr", bsize, w - 20)
    for line in body[:2]:
        stamp(sheet, x + 10, ty + 2, line, "lr", bsize, FAINT)
        ty += bsize + 2
    stamp(sheet, x + 10, y + h - 13, item["source"], "lb", 11, FAINT)


def paint_card(sheet, x, y, w, h, item):
    sheet.box(x, y, x + w, y + h, CARD)
    sheet.edge(x, y, x + w, y + h, INK, 2)
    sheet.box(x, y, x + w, y + 3, REGION_PAINT[item["region"]])
    num_disc(sheet, x + 14, y + 15, 9, item["num"])
    tag_size = pick_size(item["tag"], "lb", 11, 11, w - 30)
    stamp(sheet, x + 27, y + 9, item["tag"], "lb", tag_size, INK)

    icon = ICONS[item["icon"]]
    if item["icon"] == "chart":
        icon(sheet, x + 9, y + 27, 30, REGION_PAINT[item["region"]])
    else:
        icon(sheet, x + 9, y + 27, 30)
    lines = wrap_lines(item["title"], "lb", 14, w - 56)
    ty = y + 25
    for line in lines[:3]:
        stamp(sheet, x + 47, ty, line, "lb", 14, INK)
        ty += 16

    body = wrap_lines(item["summary"], "lr", 12, w - 18)
    by = y + 73
    for line in body[:2]:
        stamp(sheet, x + 9, by, line, "lr", 12, FAINT)
        by += 13

    pill(sheet, x + w - 8, y + h - 17, item["status"], h=14)
    stamp(sheet, x + 9, y + h - 15, item["source"], "lb", 11, FAINT)


def paint_map_panel(sheet, x, y, w, h):
    sheet.box(x, y, x + w, y + h, CARD)
    sheet.edge(x, y, x + w, y + h, INK, 2)
    stamp(sheet, x + 10, y + 9, "WHERE IT HAPPENED", "lb", 14, INK)
    stamp_end(sheet, x + w - 10, y + 11, "STORIES 1-13", "lb", 11, RED)

    pitch = 3.8
    ox, oy = x + 2, y + 34
    for row, line in enumerate(mapdata.GRID):
        for col, code in enumerate(line):
            if code == ".":
                continue
            sheet.disc(ox + col * pitch + pitch / 2.0,
                       oy + row * pitch + pitch / 2.0, 1.7,
                       REGION_PAINT[code])
    for num, (col, row) in mapdata.PINS.items():
        num_disc(sheet, ox + col * pitch + pitch / 2.0,
                 oy + row * pitch + pitch / 2.0, 7.5, num)

    note = ("Pins 1-13 locate the lead and feature stories; "
            "all 35 items are colour-coded across 9 regions.")
    ty = oy + mapdata.ROWS * pitch + 10
    for line in wrap_lines(note, "lr", 12, w - 20)[:3]:
        stamp(sheet, x + 10, ty, line, "lr", 12, FAINT)
        ty += 15

    # Legend: region colour dot, name and story count, 3 x 3.
    short = {"E": "Europe", "M": "Mid East", "F": "Africa",
             "S": "E. Asia", "H": "S. & SE Asia", "N": "N. America",
             "L": "S. America", "O": "Oceania", "W": "World"}
    ly = y + h - 62
    for i, (code, _name) in enumerate(REGION_ORDER):
        col, row = i % 3, i // 3
        lx = x + 10 + col * ((w - 16) // 3)
        yy = ly + row * 19
        sheet.disc(lx + 4, yy + 5, 4, REGION_PAINT[code])
        stamp(sheet, lx + 13, yy,
              f"{short[code]} {REGION_COUNTS[code]}", "lb", 11, INK)


def paint_briefs(sheet, x, y, w):
    sheet.box(x, y, x + w, y + 24, NAVY)
    stamp(sheet, x + 10, y + 5,
          "ALSO ON FRIDAY 27 NOVEMBER - 22 MORE DATED BRIEFS",
          "lb", 13, (255, 255, 255))
    stamp_end(sheet, x + w - 10, y + 7, "9 REGIONS MATCHED BY COLOUR",
              "lb", 11, GOLD)

    gap = 14
    colw = (w - gap) // 2
    first = 14
    for i, (place, text, source, region, _field) in enumerate(BRIEFS):
        num = first + i
        col, row = divmod(i, 11)
        bx = x + col * (colw + gap)
        by = y + 34 + row * 26
        sheet.box(bx, by + 2, bx + 3, by + 21, REGION_PAINT[region])
        sheet.box(bx + 6, by + 1, bx + 23, by + 16, NAVY)
        stamp_mid(sheet, bx + 14.5, by + 3, str(num), "lb", 11,
                  (255, 255, 255))
        stamp_end(sheet, bx + colw, by + 1, source, "lb", 11, FAINT)
        body = f"{place}: {text}"
        lines = wrap_lines(body, "lb", 12, colw - 82)
        for j, line in enumerate(lines[:2]):
            stamp(sheet, bx + 28, by + j * 13, line, "lb", 12, INK)


def paint_footer(sheet):
    band_y = 966
    sheet.box(PAD, band_y, FAR, band_y + 38, RED)
    stamp(sheet, PAD + 10, band_y + 5,
          "DATE CHECK - EXCLUDED   Every story above happened or "
          "was first reported on Fri 27 Nov 2026.",
          "lb", 12, (255, 255, 255))
    stamp(sheet, PAD + 10, band_y + 21,
          "Left out: Hormuz closure announced (Thu Nov 26) - Kyiv "
          "blackout (Thu Nov 26) - COP31 collapse (Wed Nov 25)",
          "lb", 12, (255, 255, 255))
    stamp(sheet, PAD, band_y + 44,
          "OFFICIAL = on record - REPORTED = one account - "
          "CONFIRMED = 2+ outlets",
          "lb", 11, FAINT)
    stamp_end(sheet, FAR, band_y + 44,
              "Sources: Reuters - AP - AFP - Al Jazeera - Guardian - "
              "BBC - Kyodo - USGS - Xinhua",
              "lb", 11, FAINT)


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------
def compose():
    sheet = Sheet(SHEET, SHEET, STOCK)
    paint_masthead(sheet)

    gap = 10
    colw = (WIDTH - 2 * gap) // 3
    for i, item in enumerate(LEADS):
        paint_lead(sheet, PAD + i * (colw + gap), 180, colw, item)

    card_gap = 8
    cardw = (WIDTH - 4 * card_gap) // 5
    cardh = 114
    for i, item in enumerate(CARDS):
        col, row = i % 5, i // 5
        paint_card(sheet, PAD + col * (cardw + card_gap),
                   392 + row * (cardh + card_gap), cardw, cardh, item)

    paint_map_panel(sheet, PAD, 634, 300, 324)
    paint_briefs(sheet, PAD + 312, 634, WIDTH - 312)
    paint_footer(sheet)
    return sheet


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output"
    os.makedirs(out_dir, exist_ok=True)
    target = os.path.join(out_dir, "entry.png")
    page = compose()
    save_png(target, SHEET, SHEET, page.px)
    print(f"wrote {target}: {SHEET}x{SHEET}")


if __name__ == "__main__":
    main()
