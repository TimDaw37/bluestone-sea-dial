# Bluestone sea-vs-land dial — pre-registration

**Committed before any cost surface is built or any least-cost path is run.
Not to be revised after results are seen.** If something here turns out wrong or
unworkable, the change is recorded as an amendment with its date and reason, not
edited away.

**This document is protocol only.** No analysis is run under this file until Tim
approves it.

Target posts to update if the work proceeds:
- https://www.sarsen.org/2025/07/natural-route-analysis-of-possible.html
- earlier: https://www.sarsen.org/2024/04/the-natural-corridor-for-bluestones.html

Context already on the table (fixed background, not hypotheses to re-test here):
Lewis 2024 *JAS* 170 106055; Keith Ray inland walk; A40 / Teifi–Usk–Wye corridor;
Monmouth vs Hereford Severn-crossing debate.

---

## Why this exists

The inland corridor from Preseli toward Stonehenge is already argued on the
ground and in corridor modelling. What is not fixed is the **relative cost of
water travel**. A least-cost model that treats the sea as free, or as
prohibitive, will answer a different question from one that dials that cost.

Researcher degrees of freedom on that dial are large enough to pick an answer.
So the dial, the DEM grain, the starts and end, the reporting, and the pass/fail
rules are written down first.

---

## Question

**At what relative cost of water travel versus overland does a Preseli →
Stonehenge route prefer sea (Bristol Channel / Severn estuary, or a longer Welsh
coast leg) over the inland corridor?**

Report, for each dial setting: total accumulated cost, route length, and the
**fraction of the route that is water**. Preference for sea is defined as the
least-cost path using a continuous sea or major-estuary leg rather than staying
with the inland Teifi–Usk–Wye style corridor across the Welsh border.

This is a **broad-brush** sensitivity dial, not a reconstruction of how stones
were moved.

---

## Fixed endpoints

| Role | Place |
|------|--------|
| Starts | **Carn Goedog** and **Craig Rhos-y-felin**. If both yield the same corridor family under the same dial, a single Preseli north-flank centroid may be substituted and that substitution reported. |
| End | **Stonehenge** (monument centroid). |

No other sources or destinations in this run.

---

## Frozen: DEM and grain

- National DEM only, **~30–90 m** posts.
- Preferred: **OS Terrain 50** where licence and download are straightforward;
  otherwise **SRTM** or **Copernicus DEM** at comparable grain.
- **Not** 1 m LiDAR. Not OS Terrain 5. No local high-resolution patches that
  would make one corridor look finer than another.
- Study frame: large enough to contain Preseli, the south Welsh coast / Bristol
  Channel approaches, the inland A40 / Teifi–Usk–Wye band, Severn crossings at
  Monmouth and Hereford latitudes, and Stonehenge, with margin so the frame edge
  does not force the path. Exact bbox recorded when the raster is cut; not tuned
  after seeing paths.

---

## Frozen: cost model (one main dial)

Overland cells: a simple slope-based cost on an 8-neighbour grid (anisotropic
upslope/downslope allowed; exact formula locked in the analysis notebook before
the first production run and not changed mid-sweep).

**Main dial — water cost multiplier `m_water`:**

Sea and optionally major rivers / estuary cells cost
`m_water ×` the equivalent overland step cost at zero slope (or a fixed base
water cost × `m_water` — choose one definition before run 1 and keep it).

Sweep `m_water` across a pre-stated range from cheap water (sea preferred) to
expensive water (inland preferred). Suggested starting grid, to be confirmed in
the notebook before run 1: e.g. `0.1, 0.25, 0.5, 1, 2, 5, 10, 25, 50` (or a
log-spaced equivalent). The range must include values that, by design, force
each regime if the terrain allows it.

**Optional secondary dials** (run only if the main dial alone is ambiguous; each
stated before use):

1. Rivers as **barriers** / **free conduits** / **costed waterways**.
2. Severn crossing options: unconstrained; favour Monmouth-side; favour
   Hereford-side; or discrete forced crossing bands.

Secondary dials are reported separately. They do not redefine the main result.

---

## Frozen: what is reported

For every dial setting:

1. Least-cost path (and, if cheap, the band within ~10% of optimal cost).
2. Total accumulated cost.
3. Length; **fraction of length classed as water**.
4. Regime label: **sea-preferring**, **inland-preferring**, or **mixed /
   unresolved** under the pass/fail rules below.
5. Which Severn approach the path takes when it leaves Wales (when relevant).

A single “best” `m_water` is **not** claimed. The deliverable is the **switch
point(s)** or the range where the regime flips.

---

## Pass / fail (written before running)

Pass / fail applies to the *analysis design*, not to any archaeological
conclusion.

| Criterion | Pass | Fail |
|-----------|------|------|
| **P1 Switch exists** | There exist dial values where the LCP is sea-dominated and values where it is inland-dominated (water-fraction threshold below). | Every dial setting yields the same regime → report “no switch in tested range” and stop; do not invent further dials to force a flip. |
| **P2 Water fraction** | Sea-preferring: water fraction **≥ 0.25** of route length (or a continuous Bristol Channel / Severn estuary leg of at least that share). Inland-preferring: water fraction **≤ 0.10** and path stays with the land corridor family. Between = **mixed / unresolved**. | Thresholds changed after seeing maps. |
| **P3 Start stability** | Carn Goedog and Craig Rhos-y-felin give the same regime family at the same `m_water` values that matter for the switch. | Different regimes at the switch → report both; do not average starts into a false consensus. |
| **P4 Grain honesty** | Paths and switch statements are consistent with ~30–90 m DEM (no sub-cell claims). | Any claim that needs 1 m LiDAR or engineered haulage detail. |
| **P5 Eyeball** | Paths are not artefacts of nodata, coastline encoding, or frame clipping. | Path hugs a raster edge, crosses impossible nodata bridges, or follows a modern artefact (motorway embankment etc.) → fix preprocessing, log amendment, re-run; do not publish the artefact. |

Failed criteria are reported as failures. They are not patched quietly.

---

## Predictions (can be wrong)

1. A switch exists inside a moderate multiplier range; water is neither always
   free nor always prohibitive.
2. When sea wins, the preferred water is the **Bristol Channel / Severn estuary**
   approach rather than a long west-coast circumnavigation — unless `m_water` is
   extremely low.
3. The inland winner resembles the **Teifi–Usk–Wye / A40** corridor family already
   discussed, not a random cross-country line.
4. Monmouth vs Hereford Severn approach may flip with secondary dials more than
   with the main sea dial.

---

## Out of scope (explicit)

- No Neolithic engineering of sledges, rafts, boats, or haulage technology.
- No 1 m LiDAR; no micro-routing through gates or holloways.
- No Orkney.
- No Altar Stone provenance debate beyond route geometry (source endpoints stay
  Preseli as above).
- **Never mention Mike Pitts.**
- **Never use Pirrie et al.**
- No claim that least-cost equals historically used.
- This protocol does not run the analysis; approval comes first.

---

## Later deliverables (only if this protocol is approved)

1. A simple **dials map page** (slider or stepped `m_water`) showing regime and
   water fraction.
2. A **short draft section** for updating the July 2025 sarsen.org post.

Not part of this pre-registration file.

---

## Order of operations

1. Approve this protocol (or amend it dated).
2. Lock DEM source, bbox, cost formula, and `m_water` grid in the notebook.
3. Build cost surfaces; run the sweep; write timestamped results **before**
   narrative write-up.
4. Apply pass/fail; report failed predictions.
5. Only then draft the dials page and post section.

---

## Amendments

### A1 — 2026-10-05 — first-pass working grid 200 m

**Change.** First-pass LCP run used a **200 m** working grid mean-resampled from OS Terrain 50 (50 m posts), not a 50 m path grid.

**Reason.** Dijkstra cost on the full frame at 50–100 m was too slow for a cheap first pass; 200 m finishes the nine-point dial × two starts in minutes. Source DEM remains Terrain 50.

**Made before interpreting results as publishable.** This is a grain coarsening for speed, stated openly. A later pass may re-run the switch bracket at 100 m or 50 m without changing the locked cost formula or dial grid.

**Also:** major rivers were not digitised separately; water = DEM elev < 0 (sea/estuary only), as allowed for v1 simplicity.

### A2 — 2026-10-05 — pass-2 secondary dials (rivers + coastal reach)

**Change.** Pass 2 adds two secondary dials, still on OS Terrain 50 at **200 m** working grid (no finer grain). Study frame **expanded south and west** so a Land’s End sea loop is geometrically possible.

**River dial** (`river_mode`):
- `ignore` — sea/estuary only (as pass 1).
- `barrier` — major-river cells strongly penalised (step cost `100 × d`); coarse mask.
- `conduit` — major-river cells costed as water at the same `m_water` as sea.

Major rivers (coarse): Teifi, Tywi, Usk, Wye, Severn, Avon — from OSM waterways, buffered ~400 m onto the 200 m grid.

**Coastal-reach dial** (`coastal_reach`), mechanism locked before run:
- `bristol_channel` — sea cells with OSGB **easting < 200000** are **impassable** (not usable as water). Blocks west-Wales / Land’s End circumnavigation; leaves Bristol Channel / Severn estuary sea open.
- `full_coast` — all DEM sea cells in the expanded frame traversable at `m_water` (Land’s End loop allowed if cheap enough).

**m_water grid for pass 2:** `0.05, 0.1, 0.5, 1, 2, 5, 10` (switch bracket + one very cheap water for Atkinson-style Land’s End test).

**Reason.** Tim approved secondary dials after pass 1; main dial was clear but Land’s End and river treatment were untested.


**Ocean nodata:** OS Terrain 50 has no posts in open sea; pass-2 flood-fills NaN cells connected to DEM sea (elev < 0) as traversable sea at −1.5 m so Channel/Land’s End routes are possible. Inland NaN pockets stay impassable.

**Made before pass-2 run.**

### A3 — 2026-10-05 — pass-3 finer grain check

**Change.** Re-run a **subset** of dial settings at **100 m** (and 50 m if cheap) on the same OS Terrain 50 source, same cost formula, same coastal/river mechanisms as A2.

**Subset (locked before run):**
- Switch bracket: `m_water` ∈ {0.5, 1, 2, 5}; `bristol_channel` × `ignore` and `bristol_channel` × `conduit`
- Land’s End test: `m_water` ∈ {0.05, 0.1}; `full_coast` × `ignore`
- Starts: both Preseli starts
- Frame: same expanded bbox as pass-2; ocean-fill as A2

**Reason.** Confirm whether switch ~1–2, Land’s End only at very cheap water, and inland corridor behaviour hold at finer grain.

**Made before pass-3 run.**

**Pass-3 outcome note (after run):** 100 m subset completed; switch 1→2 and inland lock-in hold; Land’s End only at m=0.05 on full_coast. **50 m skipped** — full frame not cheap (~4× 100 m).

