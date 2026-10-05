# Bluestone sea-vs-land dial — pass-3 results (finer grain)

**Run:** 2026-10-05 ~09:27–09:50 Europe/London  
**Status:** confirmation pass. No blog.  
**Protocol:** amendment **A3** (recorded before run). Locked: `LOCKED_params.json`

---

## What was run

OS Terrain 50 at **100 m** working grid (same expanded frame + ocean-fill as pass-2). Subset:

- Switch: `m_water` ∈ {0.5, 1, 2, 5} × `bristol_channel` × {ignore, conduit} × both starts  
- Land’s End: `m_water` ∈ {0.05, 0.1} × `full_coast` × ignore × both starts  

**20 runs.** Mean runtime ~70 s/run.

**50 m:** not run. Full-frame 50 m would be ~4× slower (~5 min/run) — not “cheap” under A3. Logged as A3 note below.

---

## Confirmation vs pass-2 (200 m)

| Claim | Pass-2 (200 m) | Pass-3 (100 m) |
|-------|----------------|----------------|
| Switch ~1 → 2 | Yes (all dial combos) | **Yes** — sea at m≤1, inland at m≥2 (ignore & conduit, both starts) |
| Land’s End | m≤0.1 full_coast (ignore/barrier); conduit only m=0.05 | **Only m=0.05** full_coast ignore (both starts). At m=0.1, shorter Channel-side sea route (~350 km, water ~0.78) — LE flag **false** |
| A40 / inland family | Inland m≥2 with ignore/conduit | **Holds** (welsh mean land N ≳ 210 km on inland runs) |
| Conduit vs ignore at switch | Same regime | **Same** regimes; costs nearly identical at m=1–2 |

So: **switch and inland lock-in are grain-stable** between 200 m and 100 m. **Land’s End is more fragile** — only the very cheapest water (0.05) still takes the long loop at 100 m.

---

## Pass / fail

| ID | Result |
|----|--------|
| P1 Switch | **Pass** at 100 m |
| P2 Fractions | **Pass** |
| P3 Starts | **Pass** |
| P4 Grain | **Pass** for 100 m claims; 50 m not claimed |
| P5 Eyeball | **Pass** (maps) |

---

## Maps

`map_100m_switch_bristol_ignore.png`, `map_100m_lands_end.png`, `map_100m_river_m2.png`

Table: `results_table.csv`. Script: `lcp_sea_dial_pass3.py`.

### A3 addendum — 50 m skipped

Full-frame Terrain 50 at 50 m estimated ~4× 100 m cost; not run in this pass. A cropped-frame 50 m check remains optional later.
