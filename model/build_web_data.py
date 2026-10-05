#!/usr/bin/env python3
"""Write the web model's grids and relief image into docs/data/.

grid{cell}.b64.txt : base64 of gzip of int16 elevation in decimetres (row-major, north row first)
                    followed by uint8 flags (1 = sea, 2 = major river buffer, 4 = sea in sight of land, A5)
                    followed by uint8 distance from sea cell to nearest land, in quarter-km (capped 254)
relief.jpg        : 200 m hillshade/tint basemap for the same frame
meta.json         : frame and grid sizes
"""
import gzip, json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
from prep import aggregate, river_mask, coast_masks

DOCS = Path(__file__).resolve().parent.parent / "docs" / "data"
DOCS.mkdir(parents=True, exist_ok=True)
meta = {}
for cell in (400, 200):
    z, sea, gi = aggregate(cell, "a4")
    riv = river_mask(gi)
    zz = np.where(np.isfinite(z), np.round(z * 10), -32768).astype("<i2")
    dist_km, visible = coast_masks(z, sea, cell)
    fl = (sea.astype(np.uint8) | (riv.astype(np.uint8) << 1) | ((sea & visible).astype(np.uint8) << 2))
    dq = np.where(sea, np.minimum(np.round(dist_km * 4), 254), 0).astype(np.uint8)   # quarter-km to nearest land
    import base64
    (DOCS / f"grid{cell}.b64.txt").write_text(base64.b64encode(gzip.compress(zz.tobytes() + fl.tobytes() + dq.tobytes(), 9)).decode())
    meta[str(cell)] = dict(width=gi["width"], height=gi["height"], cell=cell)
    print(cell, gi, (DOCS / f"grid{cell}.b64.txt").stat().st_size)
    if cell == 200:
        import matplotlib
        matplotlib.use("Agg")
        from matplotlib.colors import LightSource, LinearSegmentedColormap
        import matplotlib.pyplot as plt
        zl = np.where(sea | ~np.isfinite(z), 0, z)
        ls = LightSource(azdeg=315, altdeg=40)
        hs = ls.hillshade(zl, vert_exag=6, dx=cell, dy=cell)
        tint = LinearSegmentedColormap.from_list("t", [
            (0.0, "#c9cfb4"), (0.08, "#b9c39c"), (0.25, "#c8bf92"),
            (0.5, "#b79f78"), (0.75, "#9a8a76"), (1.0, "#e8e4dc")])
        rgb = tint(np.clip(zl / 800.0, 0, 1))[..., :3]
        rgb = rgb * (0.55 + 0.6 * hs[..., None])
        seac = np.array([0x9f, 0xb8, 0xc4]) / 255
        rgb[sea] = seac
        rgb[riv & ~sea] = rgb[riv & ~sea] * 0.75 + np.array([0x6f, 0x93, 0xa6]) / 255 * 0.25
        from PIL import Image
        Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8)).save(DOCS / "relief.jpg", quality=84, optimize=True, progressive=True)
meta["frame"] = dict(xmin=120000, ymax=260000, xmax=450000, ymin=10000)
(DOCS / "meta.json").write_text(json.dumps(meta))
