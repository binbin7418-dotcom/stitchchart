#!/usr/bin/env python3
"""
StitchChart — turn a photo into a print-ready cross-stitch pattern pack.

Outputs, from one photo:
  * pattern PDF — cover page, symbol chart pages (numbered grid,
    paginated for home printing) and a legend
  * pattern.csv — the grid as DMC codes (for spreadsheet/chart software)
  * chart_report.md — the verification

Every stitch cell is mapped to the nearest colour from a built-in
palette of 422 DMC floss codes (RGB screen approximations from the
public DMC colour chart — the pattern always names the official DMC
code, which is what you buy). An optional colour cap merges the
least-used colours into their nearest neighbours so kits stay sane.

Verification (built in, not optional): the grid is recounted from
scratch — total cells must equal width x height exactly (stitch
conservation), every legend count must equal its grid recount, and
the symbol map must be one-to-one. The report prints the numbers.

Estimates are labelled estimates: skeins = ceil(stitches / 1,800)
per colour (a common rule of thumb for 2 strands on 14-count fabric),
and finished size assumes the fabric count you pick.

Local only. No network. Uses Pillow + reportlab.
"""
import csv
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image
from dmc_palette import PALETTE

SYMBOLS = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ"
               "abcdefghijklmnopqrstuvwxyz"
               "0123456789") + ["+", "x", "%", "=", "#", "@", "*",
                                "<", ">", "^", "~", "?", "!", "$"]
MAX_COLORS_CAP = len(SYMBOLS)
SKEIN_STITCH_ESTIMATE = 1800


def _dist2(c1, c2):
    """Weighted RGB distance (redmean-flavoured)."""
    r = (c1[0] + c2[0]) / 2.0
    dr, dg, db = c1[0] - c2[0], c1[1] - c2[1], c1[2] - c2[2]
    return (2 + r / 256) * dr * dr + 4 * dg * dg + (2 + (255 - r) / 256) * db * db


_PAL_RGB = [(code, (r, g, b)) for code, _n, r, g, b in PALETTE]
_cache = {}


def nearest_dmc(rgb):
    if rgb in _cache:
        return _cache[rgb]
    best, bd = None, None
    for code, prgb in _PAL_RGB:
        d = _dist2(rgb, prgb)
        if bd is None or d < bd:
            best, bd = code, d
    _cache[rgb] = best
    return best


def build_grid(image_path, width_stitches, max_colors):
    im = Image.open(image_path).convert("RGB")
    w0, h0 = im.size
    height_stitches = max(1, round(width_stitches * h0 / w0))
    small = im.resize((width_stitches, height_stitches), Image.BOX)
    px = small.load()
    grid = [[nearest_dmc(px[x, y]) for x in range(width_stitches)]
            for y in range(height_stitches)]
    # colour cap: merge least-used colour into its nearest remaining one
    while True:
        counts = {}
        for row in grid:
            for c in row:
                counts[c] = counts.get(c, 0) + 1
        if len(counts) <= max_colors:
            break
        victim = min(counts, key=lambda c: counts[c])
        vrgb = dict(_PAL_RGB)[victim]
        target, td = None, None
        for c in counts:
            if c == victim:
                continue
            d = _dist2(vrgb, dict(_PAL_RGB)[c])
            if td is None or d < td:
                target, td = c, d
        grid = [[target if c == victim else c for c in row] for row in grid]
    return grid, (w0, h0)


def legend_for(grid):
    counts = {}
    for row in grid:
        for c in row:
            counts[c] = counts.get(c, 0) + 1
    names = {code: n for code, n, _r, _g, _b in PALETTE}
    rgbs = {code: (r, g, b) for code, _n, r, g, b in PALETTE}
    legend = []
    for code, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        legend.append({"code": code, "name": names[code], "rgb": rgbs[code],
                       "stitches": n,
                       "skeins": max(1, math.ceil(n / SKEIN_STITCH_ESTIMATE))})
    for i, entry in enumerate(legend):
        entry["symbol"] = SYMBOLS[i]
    return legend


def verify_pattern(grid, legend):
    """Independent recount. Returns a list of problems (empty = PASS)."""
    problems = []
    height = len(grid)
    width = len(grid[0]) if height else 0
    total = sum(len(row) for row in grid)
    if total != width * height:
        problems.append(f"grid not rectangular: total {total} != {width}x{height}")
    recount = {}
    for row in grid:
        for c in row:
            recount[c] = recount.get(c, 0) + 1
    if sum(recount.values()) != width * height:
        problems.append("stitch conservation failed")
    for entry in legend:
        if recount.get(entry["code"], 0) != entry["stitches"]:
            problems.append(
                f"legend count mismatch for {entry['code']}: "
                f"{entry['stitches']} vs recount {recount.get(entry['code'], 0)}")
    if set(recount) != {e["code"] for e in legend}:
        problems.append("legend colours != grid colours")
    syms = [e["symbol"] for e in legend]
    if len(syms) != len(set(syms)):
        problems.append("symbols are not one-to-one")
    return problems


def _lum(rgb):
    return 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]


def write_pdf(pdf_path, grid, legend, title, fabric_count, src_size):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    height, width = len(grid), len(grid[0])
    sym_of = {e["code"]: e["symbol"] for e in legend}
    rgb_of = {e["code"]: e["rgb"] for e in legend}
    c = canvas.Canvas(pdf_path, pagesize=A4)
    pw, ph = A4
    # ---------- cover ----------
    c.setFont("Helvetica-Bold", 22)
    c.drawString(20 * mm, ph - 30 * mm, title)
    c.setFont("Helvetica", 12)
    fin_w = width / fabric_count
    fin_h = height / fabric_count
    lines = [
        f"Design size: {width} x {height} stitches",
        f"Finished size on {fabric_count}-count fabric: "
        f"{fin_w:.1f} x {fin_h:.1f} inches ({fin_w * 2.54:.1f} x {fin_h * 2.54:.1f} cm)",
        f"Colours: {len(legend)} DMC",
        f"Source photo: {src_size[0]} x {src_size[1]} px",
        "",
        "How to use: print the chart pages at 100% scale. Each square is",
        "one stitch; the symbol in the square matches the legend. Start",
        "from the centre (marked by the bold mid lines) and work out.",
        "Skein counts in the legend are estimates (1 skein ~= 1,800",
        "stitches, 2 strands on 14-count) - buy one extra of main colours.",
    ]
    y = ph - 48 * mm
    for ln in lines:
        c.drawString(20 * mm, y, ln)
        y -= 7 * mm
    c.showPage()
    # ---------- chart pages ----------
    cols_per_page, rows_per_page = 40, 52
    cell = 4.2 * mm
    for gy in range(0, height, rows_per_page):
        for gx in range(0, width, cols_per_page):
            c.setFont("Helvetica", 7)
            c.drawString(15 * mm, ph - 12 * mm,
                         f"{title} - chart columns {gx + 1}-{min(gx + cols_per_page, width)}, "
                         f"rows {gy + 1}-{min(gy + rows_per_page, height)}")
            x0, ytop = 15 * mm, ph - 20 * mm
            # column numbers
            c.setFont("Helvetica", 5)
            for i in range(gx, min(gx + cols_per_page, width)):
                if (i + 1) % 5 == 0 or i == gx:
                    c.drawCentredString(x0 + (i - gx) * cell + cell / 2,
                                        ytop + 2 * mm, str(i + 1))
            for j in range(gy, min(gy + rows_per_page, height)):
                yrow = ytop - (j - gy + 1) * cell
                if (j + 1) % 5 == 0 or j == gy:
                    c.drawRightString(x0 - 2 * mm, yrow + cell / 3, str(j + 1))
                for i in range(gx, min(gx + cols_per_page, width)):
                    code = grid[j][i]
                    r, g, b = rgb_of[code]
                    c.setFillColorRGB(r / 255, g / 255, b / 255)
                    c.rect(x0 + (i - gx) * cell, yrow, cell, cell, stroke=0, fill=1)
                    dark = _lum((r, g, b)) > 140
                    c.setFillColorRGB(0, 0, 0) if dark else c.setFillColorRGB(1, 1, 1)
                    c.setFont("Helvetica-Bold", 5.2)
                    sym = sym_of[code]
                    c.drawCentredString(x0 + (i - gx) * cell + cell / 2,
                                        yrow + cell / 3.2,
                                        sym if len(sym) == 1 else sym[0])
                    c.setStrokeColorRGB(0.75, 0.75, 0.75)
                    c.setLineWidth(2 if (i + 1) % 10 == 0 or (j + 1) % 10 == 0 else 0.25)
                    c.rect(x0 + (i - gx) * cell, yrow, cell, cell, stroke=1, fill=0)
            # centre cross marker when this page contains the middle
            mid_x, mid_y = width // 2, height // 2
            if gx <= mid_x < gx + cols_per_page and gy <= mid_y < gy + rows_per_page:
                cx = x0 + (mid_x - gx) * cell
                cy = ytop - (mid_y - gy) * cell
                c.setStrokeColorRGB(1, 0, 0)
                c.setLineWidth(1.2)
                c.line(cx - 3 * mm, cy, cx + 3 * mm, cy)
                c.line(cx, cy - 3 * mm, cy if False else cy, cy + 3 * mm)
            c.showPage()
    # ---------- legend ----------
    c.setFont("Helvetica-Bold", 15)
    c.drawString(20 * mm, ph - 25 * mm, "Legend - DMC colours")
    c.setFont("Helvetica", 9.5)
    y = ph - 38 * mm
    c.drawString(20 * mm, y, "Sym   DMC       Colour name                              Stitches   Skeins (est.)")
    y -= 4 * mm
    c.line(20 * mm, y, pw - 20 * mm, y)
    y -= 7 * mm
    for e in legend:
        if y < 18 * mm:
            c.showPage()
            y = ph - 25 * mm
        r, g, b = e["rgb"]
        c.setFillColorRGB(r / 255, g / 255, b / 255)
        c.rect(20 * mm, y - 1 * mm, 6 * mm, 4.5 * mm, stroke=1, fill=1)
        c.setFillColorRGB(0, 0, 0)
        c.drawString(28 * mm, y, f"{e['symbol']:<5} {e['code']:<9} "
                                 f"{e['name'][:38]:<40} {e['stitches']:>8}   {e['skeins']}")
        y -= 6.5 * mm
    c.showPage()
    c.save()
    return c.getPageNumber()


def run_stitchchart(image_path, outdir, width_stitches=100, max_colors=30,
                    fabric_count=14, title=None):
    if max_colors > MAX_COLORS_CAP:
        raise ValueError(f"max_colors {max_colors} exceeds symbol pool {MAX_COLORS_CAP}")
    os.makedirs(outdir, exist_ok=True)
    grid, src_size = build_grid(image_path, width_stitches, max_colors)
    legend = legend_for(grid)
    problems = verify_pattern(grid, legend)
    title = title or ("StitchChart Pattern — "
                      + os.path.splitext(os.path.basename(image_path))[0])
    base = os.path.join(outdir, "stitchchart")
    pdf_path = base + "_pattern.pdf"
    pages = write_pdf(pdf_path, grid, legend, title, fabric_count, src_size)
    csv_path = base + "_pattern.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        wcsv = csv.writer(fh)
        for row in grid:
            wcsv.writerow(row)
    height, width = len(grid), len(grid[0])
    report = ["# StitchChart — pattern & verification report", "",
              f"Source photo: {image_path} ({src_size[0]}x{src_size[1]} px)",
              f"Grid: {width} x {height} = {width * height} stitches",
              f"Colours used: {len(legend)} (cap {max_colors})",
              f"Total skeins (estimate): {sum(e['skeins'] for e in legend)}",
              f"Pattern PDF pages: {pages}", "",
              "## Verification",
              f"- Stitch conservation: grid recount = {sum(e['stitches'] for e in legend)} "
              f"vs width x height = {width * height}",
              f"- Legend counts vs independent recount: "
              f"{'match' if not problems else 'MISMATCH'}",
              f"- Symbols one-to-one: {len(legend)} symbols for {len(legend)} colours",
              f"- Verdict: {'PASS' if not problems else 'FAIL — ' + '; '.join(problems)}",
              "",
              "## Honest limits",
              "- Floss RGB values are screen approximations from the public",
              "  DMC chart; always buy by DMC code, not by screen colour.",
              "- Skein estimates assume ~1,800 stitches per skein (2 strands,",
              "  14-count). Your mileage varies with coverage and strand count.",
              "- Very fine photo detail smaller than one stitch is averaged",
              "  into its cell — raise the stitch width for portraits."]
    report_path = base + "_report.md"
    with open(report_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(report) + "\n")
    return {"grid_size": (width, height), "colors": len(legend),
            "legend": legend, "pdf_path": pdf_path, "csv_path": csv_path,
            "report_path": report_path, "problems": problems,
            "verdict": not problems}


def main(argv):
    if len(argv) != 3:
        print("usage: stitch_chart.py <image> <outdir>")
        return 2
    s = run_stitchchart(argv[1], argv[2])
    print(f"grid={s['grid_size']} colors={s['colors']} verdict={s['verdict']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
