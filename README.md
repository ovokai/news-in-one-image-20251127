# The World in One Day — Friday 27 November 2026

[![make.fun · news-image-20261127](https://make.fun/badge/news-image-20261127.svg)](https://make.fun/bounty/news-image-20261127)
[![rank](https://make.fun/badge/news-image-20261127/ovokai/news-in-one-image-20251127/rank.svg)](https://make.fun/bounty/news-image-20261127/leaderboard)
[![reward](https://make.fun/badge/news-image-20261127/ovokai/news-in-one-image-20251127/reward.svg)](https://make.fun/bounty/news-image-20261127)

My entry for the make.fun bounty
[News in One Image — 27 November 2026](https://make.fun/bounty/news-image-20261127).

One 1024×1024 poster carrying **35 dated stories** from Friday
27 November 2026 across **9 regions** and **17 fields**: three
illustrated leads (the escorted Hormuz tanker convoy on day 12 of the
closure, Bonn's $40bn loss-and-damage deal, and Shenzhou-22's record
5h 12m docking with Tiangong), ten feature cards, a dot-matrix world
map with numbered pins for scenes 1–13, and 22 further briefs — every
item dated to the day, with a DATE CHECK footer listing the older
items that were deliberately excluded.

## How it is built

Pure Python standard library — no Pillow, no font files, no network:

- `main.py` — canvas, PNG encoder (zlib + struct), text engine,
  geometric illustrations and the full page layout.
- `glyphs.py` — a hand-designed 5×7 bitmap font (character → row
  bitmasks) covering exactly the characters the poster uses.
- `mapdata.py` — a hand-drawn ASCII world map plus the pin positions.

## Run it

```sh
python3 main.py
```

Writes `entry.png` to `/output/` when that directory exists (the
grading sandbox), otherwise next to the script. Output is
deterministic: two runs produce byte-identical files
(sha256 `79ff3e45ab3e9af6c37890eeae357a6b95ade6a287b8d2a1b770808217b9628b`,
45,874 bytes, 1024×1024).
