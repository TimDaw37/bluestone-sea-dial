# Bluestone sea-vs-land dial — first-pass results

**Run:** 2026-10-05 ~08:49 Europe/London  
**Status:** cheap first pass only. No blog post. Not for publication.  
**Protocol:** `../PROTOCOL.md` (Tim-approved). Params locked in `LOCKED_params.json` before run 1.

---

## Question answered (broad brush)

At what relative cost of water vs land does Preseli → Stonehenge prefer sea over the inland corridor?

**Answer on this dial:** the least-cost path flips from **sea-preferring** to **inland-preferring** between **`m_water = 1` and `m_water = 2`**.

| `m_water` | Regime (both starts) | Water fraction (Carn Goedog) |
|-----------|----------------------|------------------------------|
| 0.1 – 1   | sea-preferring       | 0.39 – 0.61                  |
| 2 – 50    | inland-preferring    | 0.00 – 0.015                 |

No mixed/unresolved cases on the pre-registered cut-offs (sea ≥ 0.25; inland ≤ 0.10). Main dial is **not** ambiguous → **secondary dials not run**.

---

## Data and locked model

- **DEM:** OS Terrain 50 ASCII Grid (OGL), tiles dated 20260529 from the national `terr50_gagg_gb` supply already cached on the box. **Obtained — not substituted with SRTM.**
- **Frame (OSGB):** E 180000–440000, N 120000–260000 (Preseli, Welsh coast, Bristol Channel, Teifi–Usk–Wye band, Severn Monmouth/Hereford latitudes, Salisbury Plain).
- **Working grid:** **200 m** (mean-resampled from 50 m posts). First-pass speed choice; source remains Terrain 50. Logged as protocol amendment A1.
- **Starts:** Carn Goedog (212878, 233160); Craig Rhos-y-felin (211650, 236140). **End:** Stonehenge (412250, 142200).
- **Water mask:** DEM elev &lt; 0 (OS sea ≈ −1.5). Sea + estuary only; major rivers **not** separately digitised in v1.
- **Overland step:** `cost = d × (1 + 4·up + 2.6·dn)`.
- **Water step:** `cost = m_water × d` when the destination cell is water (or both water).

Full table: `results_table.csv`.

---

## Pass / fail

| ID | Result |
|----|--------|
| **P1 Switch exists** | **Pass.** Sea at m≤1; inland at m≥2. |
| **P2 Water fraction** | **Pass.** Thresholds held; no post-hoc change. |
| **P3 Start stability** | **Pass.** Both starts same regime at every `m_water`. |
| **P4 Grain honesty** | **Pass** with caveat: claims are at 200 m working cells from 50 m posts — no sub-cell detail. |
| **P5 Eyeball** | **Pass for first pass.** Paths do not hug the frame edge; sea routes use Bristol Channel / Severn estuary (not a west-coast circumnavigation at m≥0.1); inland routes stay on land across south Wales and cross near the lower Wye / Monmouth latitudes at high `m_water`. Water mask is blocky at tile scale (Terrain 50 sea coding) — expected, not a path artefact. |

---

## What the paths look like

- **Sea-preferring (e.g. m=0.1, m=1):** south to the Carmarthen Bay / Bristol Channel coast, east along the Channel / Severn estuary, landfall on the English side, then overland to Stonehenge. Water share ~39–61% of length.
- **Inland-preferring (e.g. m=2, m=50):** east across south Wales, Severn approach Monmouth-side at the highest multipliers; almost no water length. Broad-brush family is inland south-Wales → Wye/Severn → Wiltshire (compatible with the Teifi–Usk–Wye / A40 corridor story at this grain; not a traced drovers’ line).

Maps: `map_sea_preferring_m0.1.png`, `map_inland_preferring_m50.0.png`, `map_switch_bracket_m1.0_to_m2.0.png`, `map_all_m_carn_goedog.png`.

---

## Predictions check

1. Switch in a moderate range — **yes** (1 → 2).  
2. Sea winner uses Bristol Channel / Severn rather than long west-coast loop — **yes** in this grid.  
3. Inland resembles Teifi–Usk–Wye / A40 family — **plausible at this grain**; not finely tested.  
4. Monmouth vs Hereford flips with secondary dials — **not tested** (main dial clear).

---

## Out of scope (kept)

No Neolithic engineering, no 1 m LiDAR, no Orkney, no Altar Stone provenance beyond endpoints, no Pirrie et al.

---

## Files

| File | Role |
|------|------|
| `LOCKED_params.json` | Cost formula + dial locked before run 1 |
| `lcp_sea_dial_first_pass.py` | Analysis script |
| `results_table.csv` | Full sweep table |
| `RESULTS.md` | This note |
| `map_*.png` | Four maps |
| `dem_mosaic_200m.npy`, `dem_info.json` | Working DEM |

**Next (not done):** finer 100/50 m check around the switch; optional river layer; dials web page / post draft only if Tim asks.
