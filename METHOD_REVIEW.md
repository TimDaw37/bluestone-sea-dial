# Method review of passes 1–3, and amendment A4 results

**Reviewer:** Claude, 5 October 2026. **Scope:** `PROTOCOL.md` (A1–A3), the three pass scripts, their `LOCKED_params.json`, `results_table.csv` and maps. **New code:** `model/engine.py`, `model/prep.py`, `model/build_mosaic.py`, `model/a4_checks.py`. **New results:** `a4-checks/`.

All coordinates below are OSGB in km (E, N).

---

## 1. Summary

1. **The passes are reproducible.** The new engine, run with the legacy preprocessing, gives the pass-2 results to the decimal place (`m_water` = 1: 247,400.6; `m_water` = 2: 257,332.3). The core arithmetic is sound.
2. **The switch is not "between 1 and 2". It is at `m_water` ≈ 1.03.** Bisection puts it at 1.027–1.037 for both starts, at 400, 200 and 100 m grain. Sea is preferred whenever a kilometre on water costs no more than about a kilometre on flat ground.
3. **Terrain hardly decides the result.** At the switch the sea and land routes are both about 239 km long. Climbing adds only 3–10 % to an overland route, so the outcome depends on the price of water and on what it costs to get a stone onto and off it. The DEM cannot supply either.
4. **The "inland" route under the protocol settings is not the A40 corridor.** For `m_water` from 2 to 10 it follows the Tywi to Llandeilo, then runs south-east over the coalfield valleys to Newport and crosses the Severn by a 3.5 km ferry at Beachley–Aust. Just above the switch it keeps to the coast and hops the estuaries. The pass-2/3 test (mean Welsh land northing ≥ 200 km) passed both routes. Prediction 3 is **not supported** under the protocol settings.
5. **A fixed transfer cost is the missing term.** Charge 25 km of flat-ground equivalent for each embark or landing and the inland winner becomes Llandovery–Brecon–Monmouth, round the head of the Severn estuary, with no water. That is the A40 family. The switch then falls to about 0.8.
6. **Two preprocessing faults** (missing SP and SZ tiles; Land's End route on the frame edge) are fixed or flagged. Neither changes the switch.

---

## 2. Findings on method and assumptions

### 2.1 The overland cost is linear in rise and fall

`d × (1 + 4·up + 2.6·dn)` with `up = rise/d` reduces to

    cost = d + 4 × rise + 2.6 × fall   (metres)

So the cost of a land route is its length plus 4 × its total climb plus 2.6 × its total descent. **Steepness does not enter.** A 50 m rise costs the same up a cliff as up a 5 km ramp, and no slope is impassable. The cost works as a generic movement cost. As a haulage cost for multi-tonne stones it is weak, because haulage depends strongly on gradient. A4 adds an optional maximum gradient. With water costs fixed, a 1-in-10 limit leaves the switch at 1.03.

`W_UP = 4` can be read as a sledge friction coefficient: for force ∝ μ + gradient, the cost per metre is ∝ 1 + gradient/μ, which gives `W_UP = 1/μ` and μ = 0.25. This reading is worth stating in any write-up, because it gives the dial a physical meaning. The descent charge (2.6) has no such reading: in that physics a descent reduces the force needed.

### 2.2 The switch is set by distance, not terrain

At the switch (200 m, Carn Goedog):

| | Length | On water | Climb | Cost |
|---|---|---|---|---|
| Last sea-preferring route (m = 1.027) | 238.9 km | 72.2 km | 1,305 m | 249,774 |
| First inland-preferring route (m = 1.030) | 238.9 km | 20.5 km | 1,530 m | 249,952 |

The routes are the same length, and the climb difference (225 m × 4 = 0.9 km equivalent) is small against 239 km. Any rule that makes water cheaper than flat ground per km produces a sea route. Any rule that makes it dearer produces a land route. The model shows that the Bristol Channel lies almost on the straight line from Preseli to Stonehenge, which is a useful geographical result. It does not show which way the stones went.

### 2.3 No cost for loading or landing

Under the locked rule, moving from land to water and back costs nothing beyond distance. The least-cost paths exploit this. At the switch the "inland" path makes 18 transfers, hopping the Taf, Tywi and Loughor estuaries, and the sea path makes 24. Any real transfer of a multi-tonne stone has a large fixed cost. A4 adds `transfer` (T, in flat-ground metres per land↔water step).

### 2.4 The 8-neighbour grid's direction bias

An 8-move grid overstates straight-line distance by 0 % (along an axis or diagonal) to 8.2 % (at 22.5°). That is larger than the 1–3 % separating the competing routes. With 16 moves (bias ≤ 2.7 %) the switch moves to 1.05–1.08, and a mixed band (water 10–25 %) opens between 0.67 and the switch. The conclusion survives, but the 1→2 bracket was never resolved finely enough to show this.

### 2.5 The inland corridor test

`a40_teifi_usk_wye` was `True` when the mean northing of the Welsh land cells was ≥ 200 km. Pembrokeshire and Carmarthenshire lie north of 200 km, so almost any path passes. Waypoints from A4:

| Setting | E 260 | E 280 | E 300 | E 320 | E 340 | Severn |
|---|---|---|---|---|---|---|
| Protocol, m = 1.03 | N 196 (Loughor) | — | N 183 | — | — | ferry Cardiff (321,175) → Weston (332,166) |
| Protocol, m = 2–10 | N 220 (Llandeilo) | N 212 | N 203 (Hirwaun) | N 191 (Caerphilly) | N 187 (Newport) | ferry Beachley (351,187) → Aust (354,186) |
| m ≥ 25, or T = 25 km | N 232 | N 231 (Llandovery) | N 229 (Brecon) | N 219 | N 213 (Monmouth) | on land, round the head of the estuary |

Only the last row follows the A40 / Usk–Wye family. The Teifi is not used in any setting.

### 2.6 Preprocessing

- **Missing tiles.** The pass-2/3 tile set lacked the SP and SZ 100 km squares. In the pass-2 maps, E 400–450, N 200–260 is blank (impassable), and E 400–450, N 10–100 (Bournemouth, the Solent, the Isle of Wight) was flood-filled as sea. The Land's End route landed through this false sea. A4 builds from the complete `terr50_gagg_gb.zip` (510 tiles). Effect on the switch: none. Effect on the Land's End cost: under 1 %.
- **Coastal averaging.** `nanmean` over a block that mixes cliff-top and sea values gives a false intermediate height. A4 classes a cell as sea when ≥ 50 % of its 50 m posts are open sea, and averages land posts only. Effect: negligible (`m_water` = 1: 247,340.9 against 247,400.6).
- **Isolated below-OD pockets** (6.9 km² in total, e.g. by the Tamar and near Bridgwater) count as land in A4.
- **Frame edge (P5).** The Land's End route runs along N = 10 km, the frame's southern edge, for about 120 km. Lizard Point is at N ≈ 11.5 km, so the edge constrains the route. Pass 2 marked P5 as a pass. It should be a **fail for the Land's End route only**, to be fixed by extending the frame south to N = 0 or below in any re-run that matters for that route. The headline routes do not touch any edge.

### 2.7 Smaller points

- Conduit rivers use a 400 m buffer each side, so the "river" is a corridor about 1 km wide that includes the valley floor. In pass 2 the water fraction counted sea only and ignored conduit river cells. A4 counts both.
- A barrier river costs 100 × d per cell. A crossing of a buffered river is about 5 cells, so in practice it is impassable.
- The Severn-approach classifier read the first crossing of E 340 km only.
- `PROTOCOL.md` in the local copy (D:\Projects\bluestone-sea-dial) predates A1–A3. The GitHub copy is current.

---

### 2.8 Mid-Holocene sea level (ignored, deliberately)

The model uses today's coast. This is defensible for the Preseli–Stonehenge routes. By the mid-Holocene (c. 5,000–4,500 cal BP) relative sea level around the Bristol Channel was already within a few metres of present, not the tens of metres below present of the early Holocene. The coasts the sea routes use (Pembrokeshire, Carmarthen Bay, Gower, north Devon) are mostly steep. A few metres of vertical change therefore moves the shoreline by much less than a 200 m cell. The exception is the low Severn levels (Gwent and Somerset Levels), where a low-gradient surface and later reclamation mean the mid-Holocene tidal edge may have lain some way inland of today's. The routes' landfalls near Avonmouth and Weston-super-Mare are close to those levels. This affects where a stone could come ashore, not whether the sea is cheaper than the land. A palaeo-coast mask is needed for low embayments like the Wash and Fenland, where the shoreline differed by tens of kilometres (research note `research/altar-stone/east-anglia-mid-holocene-coast.md`, citing Shennan et al. 2018; Brew et al. 2015). It is not needed for this dial.

## 3. A4 results (switch value of `m_water`)

Switch = smallest `m_water` with water ≤ 10 % of route length (bisection, tolerance 0.5 %). Both starts, 200 m and 8 moves unless stated. The full rows are in `a4-checks/results_*.csv`.

| Check | Setting | Carn Goedog | Craig Rhos-y-felin |
|---|---|---|---|
| Grain | 400 / 200 / 100 m | 1.027 / 1.030 / 1.037 | 1.027 / 1.030 / 1.037 |
| Moves | 8 / 16 | 1.030 / 1.084 | 1.030 / 1.051 |
| Climb penalty `W_UP` | 1 / 2 / 4 / 8 / 16 | 1.010 / 1.016 / 1.030 / 1.058 / 1.117 | 1.010 / 1.016 / 1.030 / 1.058 / 1.117 |
| Max gradient | none / 0.15 / 0.10 | 1.030 / 1.030 / 1.030 | 1.030 / 1.030 / 1.030 |
| Rivers × coast | all 6 combinations | 1.030 | 1.030 |
| Transfer T (km) | 0 / 5 / 10 / 25 / 50 | 1.030 / 1.020 / 1.020 / 0.808 / 0.437 | 1.030 / 1.020 / 1.020 / 0.792 / 0.424 |
| T = 25 km with `W_UP` | 2 / 4 / 8 / 16 | 0.743 / 0.808 / 0.909 / 1.044 | 0.730 / 0.792 / 0.891 / 1.013 |
| T = 25 km with max gradient | 0.15 / 0.10 | 0.816 / 0.856 | 0.803 / 0.836 |

Reading the table:

- The switch is **grain-stable** and **start-stable** (P3, P4 pass).
- Without a transfer cost, nothing in the terrain moves the switch more than about 10 %.
- With a transfer cost, the switch falls below 1. The sea must then be genuinely cheaper per km than flat ground, by 20 % at T = 25 km and by 56 % at T = 50 km. Climbing penalties push the switch back up.
- Sea routes with T ≥ 25 km embark at Pendine/Marros (222,207) and land near Weston-super-Mare (332,164). At T = 50 km they land at Avonmouth (352,177).

## 3a. A5 results: keeping to the coast

Switch value of `m_water` (whole coast open; Carn Goedog / Craig Rhos-y-felin). Full rows: `a5-checks/results.csv`.

| Coast rule | T = 0 | T = 25 km | Land's End route at m = 0.05 |
|---|---|---|---|
| No limit | 1.030 / 1.030 | 0.808 / 0.792 | 684.5 km |
| In sight of land (eye 2 m) | 1.030 / 1.030 | 0.808 / 0.792 | 684.5 km (unchanged) |
| Within 20 km | 1.030 / 1.030 | 0.808 / 0.792 | 753.9 km |
| Within 10 km | 1.030 / 1.030 | 0.808 / 0.792 | 863.9 km |
| Within 5 km | 1.030 / 1.030 | 0.784 / 0.771 | 988.9 km |
| Within 2 km | 0.973 / 0.944 | 0.678 / 0.669 | not taken (407.7 km, Channel route) |

- Every sea cell used by these routes, the Land's End loop included, has land in sight, so the in-sight rule closes only open Atlantic water that no route needs.
- Distance limits of 20 km or less mainly lengthen the voyages. They move the switch only at 5 km (with a transfer charge) and at 2 km.
- The Bristol Channel is narrow enough that Atkinson's coast-hugging assumption hardly affects the choice between sea and land.
- The "Bristol Channel only" setting (`bristol_channel`) gives the same switch values as the whole coast at every rule (see the CSV). The web page now omits it and leaves the whole coast open.

## 4. Pass/fail and predictions after A4

| ID | Result |
|---|---|
| P1 Switch exists | **Pass**, at m ≈ 1.03 (protocol settings) |
| P2 Water fraction | **Pass**; with 16 moves a mixed band opens between 0.67 and 1.08 |
| P3 Start stability | **Pass**; the two starts differ by ≤ 0.03 |
| P4 Grain honesty | **Pass**; 400–100 m agree to 1 % |
| P5 Eyeball | **Pass** for the switch routes; **fail** for the Land's End route (frame edge); tile gaps fixed in A4 |

| Prediction | Status |
|---|---|
| 1. Switch inside a moderate range | Supported: m ≈ 1.03, near parity with flat ground |
| 2. Sea winner uses the Bristol Channel unless water is very cheap | Supported; Land's End needs m ≤ 0.05–0.1 with the whole coast open |
| 3. Inland winner resembles the Teifi–Usk–Wye / A40 family | **Not supported** under the protocol settings (Tywi → coalfield → Beachley–Aust ferry). Supported only when water is ≥ 25 × flat ground or a transfer cost ≥ 25 km is charged |
| 4. Monmouth/Hereford flips with secondary dials | The Monmouth line appears only with expensive water or a transfer cost. No Hereford line in any setting |

## 5. What should be said in public

- The model locates a balance point, not a route: water at about the cost of flat ground.
- The decision between sea and land rests on the cost of water transport and of loading and landing. A terrain model has nothing to say about either.
- The A40 corridor is the least-cost land route only when water is avoided, by price or by transfer cost.
- Land's End is a least-cost route only if water costs about a twentieth of flat ground.
- None of these routes is evidence of the route used.
