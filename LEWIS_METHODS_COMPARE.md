# Lewis (2024) vs our bluestone sea dial: methods comparison

**Paper:** J. Lewis, "Estimating the scale-dependent influence of natural terrestrial corridors on the positioning of settlements: A multi-scale study of Roman forts in Wales", *J. Archaeol. Sci.* 170 (2024) 106055. Checked against the published PDF, the April 2024 preprint (josephlewis.github.io/RW_Natural_Corridors.pdf, same methods) and his public code (github.com/josephlewis/RW_Natural_Corridors, `R/Main.R`).
**Ours:** `PROTOCOL.md` (amendments A1, A2), `first-pass/RESULTS.md`, `first-pass/LOCKED_params.json`, `pass-2/LOCKED_params.json`. Written 5 Oct 2026.

---

## 1. What Lewis actually models

- **Question:** at what spatial scale do natural corridors best explain *where 53 Roman conquest-period forts in Wales were sited*? The question is about settlement siting, not routes.
- **Corridors:** "from everywhere to everywhere". 794 points on a 10 km grid (land cells only), with least-cost paths between every pair (629,642 paths per scenario). Corridor strength is the number of paths crossing each 100 m cell.
- **Multi-scale:** that count is summed in circular windows from 300 m to 36.1 km (82 scales). He then fits a point-process model (spatstat, cubic B-spline) of fort locations at each scale and picks the best one by AIC. **Result: 1,100 m.** He reads this as the distance at which a garrison could both reach and watch a corridor.
- **Three scenarios:** (1) walking only, (2) rivers as barriers, (3) rivers as conduits, with fixed river speeds of 0.6 / 2.5 km/h taken from Roman transport studies. In the code, the slower speed applies upstream, which is the sensible way round. The printed text has the two speeds swapped. **Walking only fits best.** Lewis concludes that the forts were placed to control foot corridors, not rivers.
- **DEM and cost:** OS Terrain 50, mean-aggregated to 100 m "for computational tractability". Herzog's energy-based sixth-degree polynomial is applied as a conductance surface on an 8-neighbour grid using leastcostpath and cppRouting. River rasters come from Yan et al. (2022), a global dataset.

## 2. What he does **not** do

- **No Preseli → Stonehenge least-cost path.** No bluestones, nothing Neolithic, and no single route is reported anywhere. His output is a corridor-density surface. His DEM box (E 150–500 km, N 100–400 km) happens to contain both Carn Goedog and Stonehenge, but he never extracts that journey. Reading a bluestone route off his corridor map, as the July 2025 post does, is our inference, not his result.
- **No sea dial.** In his DEM the sea is NoData, so it is impassable (I checked the repository raster: Carmarthen Bay, Cardigan Bay and the mid Bristol Channel are all NoData). Ships appear only in his discussion (about 25% of forts were reachable by ship).
- No sensitivity sweep on water cost: rivers get one fixed pair of speeds. No Severn-crossing analysis. No time-based cost.

## 3. Where our first pass matches his spirit

- **Same DEM source** (OS Terrain 50), mean-aggregated, with an 8-neighbour anisotropic slope cost and Dijkstra least-cost paths.
- **Compare scenarios rather than trust one surface.** His three scenarios correspond to our `m_water` sweep. Pass 2's `river_mode` (ignore / barrier / conduit) deliberately mirrors his three cases.
- **Our expensive-water end reproduces his world.** As `m_water` grows, the sea effectively becomes NoData. At m ≥ 2 our path is inland-preferring (water ≤ 1.5% of length). That agrees with his foot-corridor picture and gives the same broad inland south Wales → Wye/Severn family.
- **Openness about grain.** His section on DEM resolution and process scale is the same concern as our P4 (no sub-cell claims). Like his archive, our parameters are locked in a file before any run.

## 4. Deliberate differences, and why

| Item | Lewis | Ours | Why |
|---|---|---|---|
| **OD pair** | 794 × 793 pairs over Wales and the borders | 2 starts (Carn Goedog, Craig Rhos-y-felin) → Stonehenge | We ask about one journey, not a general corridor map, so the point-process and window stage has nothing to explain here. Two starts test stability (P3). |
| **Sea mask** | Sea = NoData (impassable) | Sea and estuary cells (DEM elev < 0) are traversable. Pass 2 flood-fills open-sea NoData and adds a `bristol_channel` / `full_coast` reach dial | The whole question is whether a sea leg ever wins, so the sea has to be a priced option instead of a wall. |
| **Water cost** | Fixed river speeds borrowed from Roman transport studies | `m_water` sweep, 0.1–50 (pass 2: 0.05–10). Each water step costs `m_water × d`, i.e. a multiple of the cost of flat ground | There is no defensible Neolithic water cost. Picking one would choose the answer, so we report the switch point instead (first pass: between m = 1 and m = 2, both starts). |
| **Grid** | 100 m | 200 m (amendment A1) | Same reason as his (run time), only coarser. The choice between sea and land is decided over about 240 km, so 200 m is fair for the regime but not for route detail. Pass-3 re-ran the switch bracket and Land’s End test at 100 m: switch 1→2 holds; Land’s End only at m=0.05. 50 m full-frame skipped as not cheap. |
| **Slope cost** | Herzog polynomial, energy-based. Cheapest at about −10% (gentle downhill); ×2.7 flat cost at +10% | `d × (1 + 4·up + 2.6·dn)`, linear. Flat is cheapest; ×1.4 at +10%, ×1.26 at −10% | The protocol asked for a simple formula locked before the run. A linear form with base 1 gives `m_water` a clean unit ("× flat walking"), which Herzog's curve does not, because its minimum is off flat. Our formula is a generic movement cost, not a haulage model. |

**Two caveats.**
- The 1–2 switch belongs to *our* slope formula. Herzog punishes climbing much harder and rewards gentle descent, so a Herzog run could move the switch, in a direction we can't predict without running it. That would be a worthwhile secondary check, logged as a dated amendment.
- As a rough comparison only: if Lewis's river speeds are expressed against his flat-ground conductance, they imply about **m ≈ 0.9 downstream and m ≈ 3.7 upstream**. That straddles our switch, but it mixes time-based and energy-based units, and it applies to rivers, not sea.

**Status:** pass-2 parameters and masks are locked (09:00), but there are no pass-2 results yet. Pass-2 river conduits use the same `m_water` as the sea in both directions (Lewis uses asymmetric speeds). Our barrier is a 100× penalty, where his is a hard cut.
