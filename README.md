# StitchChart

Convert a photo into a print-ready cross-stitch pattern pack: paginated
symbol chart PDF (DMC), legend with stitch counts and skein estimates,
CSV grid — verified by an independent stitch recount.

## Run (dev)

```
python gui.py                       # desktop app (needs Pillow + reportlab)
python stitch_chart.py photo.jpg out/
<venv python> test/acceptance_test.py
```

## How it works

`stitch_chart.py` area-averages the photo to the stitch grid, maps each
cell to the nearest of 422 built-in DMC colours (`dmc_palette.py`, RGB
from the public DMC conversion chart transcribed 2026-10-29), merges
least-used colours down to the cap, assigns one symbol per colour, and
renders the pack with reportlab. `verify_pattern` recounts the grid:
total = width × height, legend counts equal recounts, symbols
one-to-one.

## Scope

Full-stitch patterns only (no backstitch/fractionals in this version).
Skein estimates assume ~1,800 stitches/skein (2 strands, 14-count) and
are labelled as estimates everywhere they appear.
