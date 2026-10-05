# Bluestone sea-vs-land dial — pass-2 results

**Run:** 2026-10-05 ~09:00–09:24 Europe/London  
**Status:** secondary dials only. No blog. Not for publication.  
**Protocol:** `../PROTOCOL.md` amendment **A2** (recorded before run).  
**Locked:** `LOCKED_params.json`

---

## Dials (locked before run)

| Dial | Settings |
|------|----------|
| `m_water` | 0.05, 0.1, 0.5, 1, 2, 5, 10 |
| `river_mode` | ignore / barrier (×100·d) / conduit (same `m_water` as sea) |
| `coastal_reach` | `bristol_channel` (sea with E&lt;200000 impassable) / `full_coast` (all sea) |
| DEM | OS Terrain 50 @ **200 m**; frame expanded S/W for Land’s End; sea-connected ocean NaN filled |

Major rivers: OS Open Rivers (OGL) — Afon Teifi, Tywi, Wysg, Gwy, Hafren; River Avon; ~400 m buffer.

Both starts: Carn Goedog, Craig Rhos-y-felin. End: Stonehenge. **84 runs.**

---

## Headline answers

1. **Switch still ~1 → 2.** In every river × coastal combination, sea-preferring at `m_water≤1`, inland-preferring at `m_water≥2` (protocol cut-offs 0.25 / 0.10).
2. **Land’s End only when water is very cheap and full coast is allowed.** Flagged at `m_water≤0.1` (`full_coast`; conduit only at 0.05). Paths ~640–685 km, water fraction ~0.91–0.93. **Never** under `bristol_channel`. At `m≥0.5` even `full_coast` prefers the short Bristol Channel route.
3. **A40 / Teifi–Usk–Wye inland family** locks in with inland regime (`m≥2`) when rivers are `ignore` or `conduit` (Welsh land mean N ≳ 200 km). Under `barrier`, inland paths are shoved off the river corridors and the A40-style flag fails — rivers-as-walls distort the inland story.
4. **Severn approach:** no Hereford-side in this sweep. Labels are **Bristol-Channel** (sea-dominated approaches) or **lower-Severn** (inland / estuary-mouth crossings). Monmouth-vs-Hereford not resolved as a clean flip here.

---

## Regime sketch (Carn Goedog; Craig matches)

| coastal | rivers | m≤0.1 | m=0.5–1 | m≥2 |
|---------|--------|-------|---------|-----|
| bristol_channel | ignore/conduit/barrier | sea (Channel) | sea (Channel) | inland |
| full_coast | ignore/barrier | **Land’s End sea** | sea (Channel) | inland |
| full_coast | conduit | LE at 0.05 only; at 0.1 shorter hybrid | sea | inland |

---

## Pass / fail

| ID | Result |
|----|--------|
| P1 Switch | **Pass** (still 1→2) |
| P2 Fractions | **Pass** |
| P3 Starts | **Pass** (same regimes; Craig LE same band) |
| P4 Grain | **Pass** at 200 m (pass-3 will check finer) |
| P5 Eyeball | **Pass** — LE routes go west/south around Cornwall; Channel routes stay in estuary; barrier inland avoids river cells |

---

## Maps

`map_lands_end.png`, `map_switch_bristol_ignore.png`, `map_switch_full_coast_ignore.png`, `map_river_modes_m2.png`, `map_inland_m10.png`, `map_conduit_vs_ignore_m0.5.png`

Full table: `results_table.csv`. Script: `lcp_sea_dial_pass2.py`.
