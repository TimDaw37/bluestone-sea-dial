#!/usr/bin/env python3
"""A4 sensitivity checks. Writes ../a4-checks/results_*.csv and paths_*.json."""
import csv, json, sys, time
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
from engine import STARTS, rc_to_xy
from prep import surface

OUT = Path(__file__).resolve().parent.parent / "a4-checks"
OUT.mkdir(exist_ok=True)

def crossings(r, info):
    xs, ys = zip(*(rc_to_xy(a, b, info) for a, b in r["path_rc"]))
    xs, ys = np.array(xs), np.array(ys)
    out = {}
    for E in (260000, 300000, 350000, 380000):
        i = np.nonzero(xs >= E)[0]
        out[f"N_at_E{E//1000}"] = round(float(ys[i[0]]) / 1000, 1) if len(i) else None
    return out

def switch(s, start, lo=0.05, hi=50.0, tol=0.005, **kw):
    """smallest m with water fraction <= 0.10; largest with >= 0.25"""
    cache = {}
    def wf(m):
        if m not in cache:
            cache[m] = s.run(STARTS[start], m, **kw)
        return cache[m]["water_fraction"]
    if wf(hi) > 0.10:
        return None, None, cache
    if wf(lo) <= 0.10:
        return lo, None, cache
    a, b = lo, hi
    while b / a > 1 + tol:
        mid = (a * b) ** 0.5
        if wf(mid) <= 0.10: b = mid
        else: a = mid
    sea_ms = [m for m in cache if cache[m]["water_fraction"] >= 0.25]
    return b, (max(sea_ms) if sea_ms else None), cache

def row(tag, start, m_in, m_sea, cache, info, extra):
    rin = cache[m_in]
    d = dict(check=tag, start=start, switch_m=round(m_in, 3),
             last_sea_m=round(m_sea, 3) if m_sea else "", **extra)
    if m_sea:
        rs = cache[m_sea]
        d.update(sea_cost=round(rs["cost"]), sea_len_km=round(rs["length_m"]/1000, 1),
                 sea_water_km=round(rs["water_m"]/1000, 1), sea_climb=round(rs["climb_m"]),
                 sea_transfers=rs["transfers"],
                 sea_transfer_pts=";".join(f"{x/1000:.0f},{y/1000:.0f}" for x, y in rs["transfer_xy"]))
    d.update(inland_cost=round(rin["cost"]), inland_len_km=round(rin["length_m"]/1000, 1),
             inland_water_km=round(rin["water_m"]/1000, 1), inland_climb=round(rin["climb_m"]),
             inland_descent=round(rin["descent_m"]), inland_transfers=rin["transfers"],
             inland_transfer_pts=";".join(f"{x/1000:.0f},{y/1000:.0f}" for x, y in rin["transfer_xy"]),
             **crossings(rin, info))
    return d

def main(which):
    rows = []
    t0 = time.time()
    grains = {"grain": [400, 200, 100]}.get(which, [200])
    for cell in grains:
        s = surface(cell, "a4")
        cases = []
        if which == "grain":
            cases = [("grain", dict(), dict(grain=cell))]
        elif which == "nbr":
            cases = [("nbr", dict(nbr=n), dict(nbr=n)) for n in (8, 16)]
        elif which == "slope":
            cases = [("slope", dict(w_up=w, w_dn=0.65*w), dict(w_up=w)) for w in (1, 2, 4, 8, 16)]
        elif which == "transfer":
            cases = [("transfer", dict(transfer=T*1000), dict(transfer_km=T)) for T in (0, 5, 10, 25, 50)]
        elif which == "gmax":
            cases = [("gmax", dict(gmax=g), dict(gmax=g if g else "none")) for g in (None, 0.15, 0.10)]
        elif which == "tslope":
            cases = [("tslope", dict(transfer=25000, w_up=w, w_dn=0.65*w), dict(transfer_km=25, w_up=w)) for w in (2, 4, 8, 16)]
            cases += [("tslope", dict(transfer=25000, gmax=g), dict(transfer_km=25, gmax=g)) for g in (0.15, 0.10)]
        elif which == "coast":
            cases = [("coast", dict(coastal=c, river_mode=rm), dict(coastal=c, rivers=rm))
                     for c in ("bristol_channel", "full_coast") for rm in ("ignore", "conduit", "barrier")]
        for tag, kw, extra in cases:
            for start in STARTS:
                m_in, m_sea, cache = switch(s, start, **kw)
                if m_in is None:
                    rows.append(dict(check=tag, start=start, switch_m="none<=50", **extra)); continue
                r = row(tag, start, m_in, m_sea, cache, s.info, extra)
                rows.append(r)
                print(json.dumps(r), round(time.time()-t0), flush=True)
                if start == "Carn_Goedog":
                    keep = {f"{m:.4f}": [[int(a), int(b)] for a, b in cache[m]["path_rc"][::1]] for m in (m_in, m_sea) if m}
                    (OUT / f"paths_{tag}_{'_'.join(str(v) for v in extra.values())}.json").write_text(json.dumps(dict(info=s.info, paths=keep)))
    keys = []
    for r in rows:
        keys += [k for k in r if k not in keys]
    with open(OUT / f"results_{which}.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(rows)

if __name__ == "__main__":
    main(sys.argv[1])
