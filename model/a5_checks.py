#!/usr/bin/env python3
"""A5: keeping to the coast. Writes ../a5-checks/results.csv and a few route files."""
import csv, json, sys, time
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
from engine import STARTS, rc_to_xy
from prep import surface, closed_sea
from a4_checks import switch

OUT = Path(__file__).resolve().parent.parent / "a5-checks"; OUT.mkdir(exist_ok=True)
s = surface(200, "a4")
rows = []; t0 = time.time()
pts = lambda r: ";".join(f"{x/1000:.0f},{y/1000:.0f}" for x, y in r["transfer_xy"])
for rule in ["none", "in_sight", "within_20", "within_10", "within_5", "within_2"]:
    cs = closed_sea(rule, s.z, s.sea, 200)
    for coastal in ["bristol_channel", "full_coast"]:
        for T in [0, 25]:
            for start in STARTS:
                kw = dict(coastal=coastal, transfer=T * 1000, closed_sea=cs)
                m_in, m_sea, cache = switch(s, start, **kw)
                row = dict(rule=rule, coastal=coastal, transfer_km=T, start=start,
                           switch_m=round(m_in, 3) if m_in else "none<=50",
                           last_sea_m=round(m_sea, 3) if m_sea else "")
                if m_sea:
                    r = cache[m_sea]
                    row.update(sea_len_km=round(r["length_m"]/1000, 1), sea_water_pct=round(100*r["water_fraction"], 1),
                               sea_transfers=r["transfers"], sea_transfer_pts=pts(r) if r["transfers"] <= 6 else f"{r['transfers']} transfers")
                if m_in:
                    r = cache[m_in]
                    row.update(inland_len_km=round(r["length_m"]/1000, 1), inland_water_pct=round(100*r["water_fraction"], 1))
                if coastal == "full_coast" and T == 0:
                    r = s.run(STARTS[start], 0.05, **kw)
                    xy = np.array([rc_to_xy(a, b, s.info) for a, b in r["path_rc"]])
                    row.update(le_len_km=round(r["length_m"]/1000, 1), le_water_pct=round(100*r["water_fraction"], 1),
                               lands_end=bool(((xy[:, 0] < 170000) & (xy[:, 1] < 60000)).any()), le_transfer_pts=pts(r) if r["transfers"] <= 6 else f"{r['transfers']} transfers")
                    if start == "Carn_Goedog":
                        (OUT / f"le_path_{rule}.json").write_text(json.dumps([[int(a), int(b)] for a, b in r["path_rc"]]))
                rows.append(row); print(json.dumps(row), round(time.time()-t0), flush=True)
keys = []
for r in rows: keys += [k for k in r if k not in keys]
with open(OUT / "results.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(rows)
