#!/usr/bin/env python3
"""StitchChart seeded acceptance test (run with the product-factory venv
python, which provides Pillow + reportlab).

Seeds an 8x6 photo made of four solid blocks coloured EXACTLY like four
palette entries (310 black, B5200 snow white, 321 red, 700 green), so
the expected grid is known cell by cell. Asserts: exact codes per
quadrant, stitch conservation, legend counts, one-to-one symbols,
skein maths, CSV == grid, PDF exists with cover + chart + legend
pages, and the colour-cap merge keeps totals while reducing colours.
"""
import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from PIL import Image
from pypdf import PdfReader

from stitch_chart import run_stitchchart, build_grid, legend_for, verify_pattern

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
CHECKS = []


def check(name, ok, detail=""):
    CHECKS.append((name, bool(ok), detail))
    print(("PASS " if ok else "FAIL ") + name + (f" — {detail}" if detail else ""))


os.makedirs(OUT, exist_ok=True)
img_path = os.path.join(OUT, "seed_photo.png")
im = Image.new("RGB", (8, 6))
px = im.load()
BLOCKS = {(0, 0): (0, 0, 0), (1, 0): (255, 255, 255),
          (0, 1): (199, 43, 59), (1, 1): (7, 115, 27)}
for y in range(6):
    for x in range(8):
        px[x, y] = BLOCKS[(x // 4, y // 3)]
im.save(img_path)

s = run_stitchchart(img_path, os.path.join(OUT, "run1"),
                    width_stitches=8, max_colors=30)
check("grid size exact", s["grid_size"] == (8, 6), f"{s['grid_size']}")

grid, _ = build_grid(img_path, 8, 30)
expect = {(0, 0): "310", (1, 0): "B5200", (0, 1): "321", (1, 1): "700"}
got = {(bx, by): grid[by * 3][bx * 4] for (bx, by) in expect}
check("quadrant codes exact", got == expect, f"{got}")
legend = {e["code"]: e for e in s["legend"]}
check("four colours only", len(legend) == 4, f"{list(legend)}")
check("each colour 12 stitches",
      all(legend[c]["stitches"] == 12 for c in expect.values()))
check("stitch conservation 48", sum(e["stitches"] for e in legend.values()) == 48)
check("symbols one-to-one", len({e['symbol'] for e in legend.values()}) == 4)
check("skein estimate ceil(12/1800)=1",
      all(e["skeins"] == 1 for e in legend.values()))
check("engine verdict PASS", s["verdict"] and not s["problems"])
rows = list(csv.reader(open(s["csv_path"])))
check("CSV grid matches engine grid",
      len(rows) == 6 and all(len(r) == 8 for r in rows) and rows[0][0] == "310"
      and rows[5][7] == "700")
pages = len(PdfReader(s["pdf_path"]).pages)
check("PDF has cover+chart+legend (>=3 pages)", pages >= 3, f"pages={pages}")

grid2, _ = build_grid(img_path, 8, 2)
leg2 = legend_for(grid2)
check("colour cap merges to 2, totals kept",
      len(leg2) == 2 and sum(e["stitches"] for e in leg2) == 48
      and not verify_pattern(grid2, leg2))

passed = sum(1 for _, ok, _ in CHECKS if ok)
print(f"\n{passed}/{len(CHECKS)} checks passed")
sys.exit(0 if passed == len(CHECKS) else 1)
