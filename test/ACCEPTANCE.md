# StitchChart — Acceptance

Seeded test (pagesmith venv python: Pillow + reportlab + pypdf):
`test/acceptance_test.py` — full output: `test/acceptance_results.txt`

**Result: 11/11 checks passed.**

The seed is an 8×6 photo of four solid blocks coloured exactly like
four palette entries (310 black, B5200 snow white, 321 red, 700
green), so the correct output grid is known cell by cell.

Verified:
- Grid size exact (8×6); quadrant codes exactly 310 / B5200 / 321 / 700
- Exactly 4 colours, 12 stitches each; conservation 48 = 8×6
- Symbols one-to-one; skein estimate ceil(12/1800) = 1 per colour
- Engine verification verdict PASS with zero problems
- CSV grid matches the engine grid (corners 310 and 700 confirmed)
- PDF pack has cover + chart + legend (≥3 pages; measured 3)
- Colour cap: merging 4 colours to 2 preserves the 48-stitch total
  and still verifies clean
- Palette file integrity: 422 DMC entries, zero duplicate codes
- GUI + engine compile clean (`py_compile`)
