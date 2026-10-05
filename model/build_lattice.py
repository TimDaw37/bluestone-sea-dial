#!/usr/bin/env python3
"""Precompute the web page's route lattice (as on the sarsen route page): every combination of
water cost × landing charge × climb penalty × coast rule, Carn Goedog → Stonehenge, 200 m grid, 8 moves,
whole coast open, rivers ignored. Writes docs/data/lattice.json.

Paths are simplified (Douglas–Peucker, 100 m) separately on each land or water run, so the
land/water break points are kept exactly. Identical paths are stored once.
"""
import json, sys, time, hashlib
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
from engine import STARTS, rc_to_xy
from prep import surface, closed_sea

M = [0.05, 0.1, 0.2, 0.35, 0.5, 0.75, 0.9, 1.0, 1.1, 1.5, 2.0, 5.0, 50.0]
T = [0, 10, 25, 50]                     # km of flat-ground hauling per embark or landing
C = [2, 4, 8]                           # climb penalty (descent 0.65 of it)
COAST = {"open": "none", "sight": "in_sight", "near": "within_2"}
OUT = Path(__file__).resolve().parent.parent / "docs" / "data" / "lattice.json"


def rdp(pts, tol):
    if len(pts) < 3:
        return pts
    a, b = pts[0], pts[-1]
    ab = b - a
    n = np.hypot(*ab) or 1.0
    d = np.abs(ab[0] * (pts[:, 1] - a[1]) - ab[1] * (pts[:, 0] - a[0])) / n
    i = int(np.argmax(d))
    if d[i] <= tol:
        return np.array([a, b])
    return np.vstack([rdp(pts[: i + 1], tol)[:-1], rdp(pts[i:], tol)])


def main():
    s = surface(200, "a4")
    masks = {k: closed_sea(v, s.z, s.sea, 200) for k, v in COAST.items()}
    paths, index, keys = [], {}, {}
    t0 = time.time()
    for ck, cs in masks.items():
        for c in C:
            for t in T:
                for m in M:
                    r = s.run(STARTS["Carn_Goedog"], m, coastal="full_coast", transfer=t * 1000,
                              w_up=c, w_dn=0.65 * c, closed_sea=cs)
                    rc = r["path_rc"]
                    xy = np.array([rc_to_xy(a, b, s.info) for a, b in rc])
                    water = (s.sea & ~(cs if cs is not None else np.zeros_like(s.sea)))[rc[:, 0], rc[:, 1]]
                    # split into runs of equal water state; the boundary vertex belongs to both runs
                    out_xy, out_w = [], []
                    i = 0
                    while i < len(xy) - 1:
                        w = water[i + 1]
                        j = i + 1
                        while j < len(xy) - 1 and water[j + 1] == w:
                            j += 1
                        seg = rdp(xy[i:j + 1], 100.0)
                        if out_xy:
                            seg = seg[1:]
                        out_xy += seg.tolist()
                        out_w += [int(w)] * len(seg)
                        i = j
                    flat = [int(round(v / 10)) for p in out_xy for v in p]   # decametres OSGB
                    h = hashlib.md5(json.dumps(flat).encode()).hexdigest()
                    if h not in index:
                        index[h] = len(paths)
                        paths.append(dict(xy=flat, w=out_w))
                    # mark onto/off water for each transfer
                    ti = np.nonzero(water[1:] != water[:-1])[0]
                    tr = [[int(round(xy[k + 1][0] / 100)), int(round(xy[k + 1][1] / 100)), int(water[k + 1])] for k in ti]
                    keys[f"{ck}|{c}|{t}|{m}"] = dict(
                        p=index[h], cost=round(r["cost"] / 1000, 1), km=round(r["length_m"] / 1000, 1),
                        wkm=round(r["water_m"] / 1000, 1), wf=round(r["water_fraction"], 4),
                        climb=round(r["climb_m"]), desc=round(r["descent_m"]), tr=tr)
                print(ck, c, t, len(paths), round(time.time() - t0), flush=True)
    OUT.write_text(json.dumps(dict(dials=dict(m=M, t=T, c=C, coast=list(COAST)), routes=keys, paths=paths),
                              separators=(",", ":")))
    print("wrote", OUT, OUT.stat().st_size, "paths", len(paths), "routes", len(keys))


if __name__ == "__main__":
    main()
