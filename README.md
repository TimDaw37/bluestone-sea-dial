# Bluestone sea-vs-land dial

Broad-brush least-cost sensitivity for **Preseli → Stonehenge**: at what relative cost of water travel vs overland does a route prefer the sea (Bristol Channel / Severn estuary, or a longer west-coast / Land’s End loop) over the inland corridor?

**Not a reconstruction** of how stones were moved. No Neolithic engineering claims. Protocol-first; amendments dated.

## Question

See `PROTOCOL.md`. Pass/fail and dials are written before runs.

## Re-run (short)

1. Download [OS Terrain 50](https://osdatahub.os.uk/downloads/open/Terrain50) ASCII Grid (Open Government Licence).
2. Extract tiles covering OSGB roughly E 120000–450000, N 10000–260000 into `data/terr50_tiles/`.
3. Create a venv; `pip install numpy matplotlib geopandas rasterio shapely`.
4. Run in order (or reuse mosaics you build locally — large `.npy` DEMs are **not** in this repo):
   - `first-pass/lcp_sea_dial_first_pass.py`
   - `pass-2/lcp_sea_dial_pass2.py` (needs OS Open Rivers major-river extract or `data/rivers/major_rivers_pass2.gpkg`)
   - `pass-3/lcp_sea_dial_pass3.py`
5. Read each pass’s `RESULTS.md` and `results_table.csv`.

Exact bbox, cost formula, and dial grids are in each pass’s `LOCKED_params.json`.

## A4: method review and web model (5 Oct 2026)

- `METHOD_REVIEW.md` — audit of passes 1–3 and the A4 sensitivity results. Headline: the switch is at `m_water` ≈ 1.03 (stable from 400 m to 100 m and for both starts). A fixed cost for each embark or landing moves it; terrain barely does.
- `model/` — shared engine (`engine.py`, same cost rule as passes 1–3 plus transfer cost, max gradient, 16 moves), mosaic builder (`build_mosaic.py`, reads `terr50_gagg_gb.zip` directly), A4 checks (`a4_checks.py`), web data builder (`build_web_data.py`).
- `a4-checks/` — results CSVs, logs and switch-bracket paths.
- `docs/` — the interactive model page (GitHub Pages: `docs/index.html`). Routes are solved in the browser with the same rule; the browser and Python engines agree to within 0.01 %.

Rebuild: `python3 model/build_mosaic.py path/to/terr50_gagg_gb.zip`, then `python3 model/a4_checks.py transfer` (or `grain`, `nbr`, `slope`, `gmax`, `coast`, `tslope`), then `python3 model/build_web_data.py`.

## Data credit

Contains Ordnance Survey data © Crown copyright and database right. **OS Terrain 50** and **OS Open Rivers** under the [Open Government Licence](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/).

## Passes

| Pass | Grain | What |
|------|-------|------|
| 1 | 200 m | Main `m_water` dial; sea vs inland switch |
| 2 | 200 m | River dial + coastal-reach dial; Land’s End test |
| 3 | 100 m (50 m if cheap) | Confirm switch / LE / inland on finer Terrain 50 grid |

## Licence of this repo

Analysis text and scripts: use freely with attribution to Tim Daw / sarsen.org. OS data remains under OGL.
