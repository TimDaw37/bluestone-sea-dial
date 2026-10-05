#!/usr/bin/env python3
"""Build a 50 m OS Terrain 50 mosaic for the pass-2 frame straight from terr50_gagg_gb.zip.

Fixes the nodata problem in passes 1-3 (A4): every 100 km square that touches the
frame is read, including SP and SZ, which were missing from the earlier tile set.
Cells with no posts after all tiles are placed are open sea (Terrain 50 ships no
tiles for all-sea 10 km squares).

Output: data/terr50_frame_50m.npy (float32, NaN = no post), data/terr50_frame_50m.json
"""
import io, json, sys, zipfile
from pathlib import Path
import numpy as np

ZIP = Path(sys.argv[1] if len(sys.argv) > 1 else "/mnt/user-data/uploads/bluestone-sea-dial/data/terr50_gagg_gb.zip")
OUT = Path(__file__).resolve().parent.parent / "data"
BBOX = dict(xmin=120000, xmax=450000, ymin=10000, ymax=260000)
CELL = 50

W = (BBOX["xmax"] - BBOX["xmin"]) // CELL
H = (BBOX["ymax"] - BBOX["ymin"]) // CELL
dem = np.full((H, W), np.nan, dtype=np.float32)

outer = zipfile.ZipFile(ZIP)
used, neg_vals = [], {}
for name in outer.namelist():
    if not name.endswith(".zip"):
        continue
    inner = zipfile.ZipFile(io.BytesIO(outer.read(name)))
    asc = [n for n in inner.namelist() if n.lower().endswith(".asc")]
    if not asc:
        continue
    lines = inner.read(asc[0]).decode().split("\n", 6)
    hdr = {}
    for ln in lines[:5]:
        k, v = ln.split()
        hdr[k.lower()] = float(v)
    x0, y0 = hdr["xllcorner"], hdr["yllcorner"]
    nc, nr = int(hdr["ncols"]), int(hdr["nrows"])
    if x0 + nc * CELL <= BBOX["xmin"] or x0 >= BBOX["xmax"] or y0 + nr * CELL <= BBOX["ymin"] or y0 >= BBOX["ymax"]:
        continue
    body = "\n".join(lines[5:])
    if body.lower().startswith("nodata"):
        body = body.split("\n", 1)[1]
    a = np.array(body.split(), dtype=np.float32).reshape(nr, nc)
    r0 = int((BBOX["ymax"] - (y0 + nr * CELL)) // CELL)
    c0 = int((x0 - BBOX["xmin"]) // CELL)
    rs, cs = max(r0, 0), max(c0, 0)
    re, ce = min(r0 + nr, H), min(c0 + nc, W)
    dem[rs:re, cs:ce] = a[rs - r0:re - r0, cs - c0:ce - c0]
    used.append(asc[0])
    u, n = np.unique(a[a < 0], return_counts=True)
    for uu, nn in zip(u, n):
        neg_vals[float(uu)] = neg_vals.get(float(uu), 0) + int(nn)

np.save(OUT / "terr50_frame_50m.npy", dem)
top = sorted(neg_vals.items(), key=lambda kv: -kv[1])[:10]
info = dict(BBOX, cell=CELL, width=W, height=H, tiles_used=len(used),
            nodata_cells=int(np.isnan(dem).sum()), commonest_negative_values=top,
            source=ZIP.name)
(OUT / "terr50_frame_50m.json").write_text(json.dumps(info, indent=1))
print(json.dumps(info, indent=1))
