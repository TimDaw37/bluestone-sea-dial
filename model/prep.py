#!/usr/bin/env python3
"""Aggregate the 50 m frame mosaic to a working grid and build sea / river masks.

Two aggregation styles:
  "legacy"  passes 1-3: block nanmean of elevation; sea = mean < 0; ocean nodata
            connected to sea filled as sea (A2).
  "a4"      sea = majority of 50 m posts in the block are open sea (negative posts or
            no-post cells connected to the open sea); land elevation = mean of land
            posts only, so cliff-top and sea values are not averaged together.
            Isolated below-OD pockets not connected to the sea count as land.
"""
import json
from pathlib import Path
import numpy as np
from scipy import ndimage

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RIVER_GPKG = DATA / "rivers" / "major_rivers_pass2.gpkg"
RIVER_BUFFER_M = 400.0


def load50():
    d = np.load(DATA / "terr50_frame_50m.npy")
    info = json.loads((DATA / "terr50_frame_50m.json").read_text())
    return d, info


def open_sea_50(d):
    wet = np.isnan(d) | (d < 0)
    lab, _ = ndimage.label(wet, structure=np.ones((3, 3)))
    main = np.bincount(lab.ravel())[1:].argmax() + 1
    return lab == main


def aggregate(cell, style="a4"):
    d, info = load50()
    f = cell // 50
    H, W = d.shape[0] // f, d.shape[1] // f
    d = d[:H * f, :W * f]
    sea50 = open_sea_50(d)
    blk = lambda a: a.reshape(H, f, W, f)
    with np.errstate(all="ignore"):
        if style == "legacy":
            z = np.nanmean(blk(d), axis=(1, 3))
            sea = np.isfinite(z) & (z < 0)
            # A2 ocean fill: NaN blocks connected to sea become sea
            nanb = ~np.isfinite(z)
            lab, _ = ndimage.label(sea | nanb, structure=np.ones((3, 3)))
            keep = np.unique(lab[sea])
            sea = np.isin(lab, keep[keep > 0])
            z = np.where(sea & ~np.isfinite(z), -1.5, z)
        else:
            frac = blk(sea50.astype(np.float32)).mean(axis=(1, 3))
            sea = frac >= 0.5
            land = np.where(sea50, np.nan, d)
            z = np.nanmean(blk(land), axis=(1, 3))
            z = np.where(sea, 0.0, z)
    z = np.where(sea, 0.0, z).astype(np.float64)
    ginfo = dict(xmin=info["xmin"], ymax=info["ymax"], cell=cell, width=W, height=H,
                 xmax=info["xmin"] + W * cell, ymin=info["ymax"] - H * cell, style=style)
    return z, sea, ginfo


def river_mask(ginfo):
    import geopandas as gpd
    from rasterio.features import rasterize
    from rasterio.transform import from_origin
    g = gpd.read_file(RIVER_GPKG).to_crs(epsg=27700)
    shapes = [(geom, 1) for geom in g.geometry.buffer(RIVER_BUFFER_M) if geom is not None and not geom.is_empty]
    tr = from_origin(ginfo["xmin"], ginfo["ymax"], ginfo["cell"], ginfo["cell"])
    return rasterize(shapes, out_shape=(ginfo["height"], ginfo["width"]), transform=tr, fill=0,
                     dtype="uint8", all_touched=True).astype(bool)


def surface(cell, style="a4"):
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from engine import Surface
    z, sea, gi = aggregate(cell, style)
    return Surface(z, sea, river_mask(gi), gi)


def coast_masks(z, sea, cell):
    """A5: distance from each sea cell to the nearest land cell (km), and the in-sight mask."""
    land = ~sea
    dist_km = ndimage.distance_transform_edt(sea) * cell / 1000.0
    zl = np.where(land & np.isfinite(z), z, -1.0)
    visible = np.zeros(sea.shape, bool)
    for H in range(0, 901, 10):
        src = land & (zl >= H)
        if not src.any():
            break
        d = ndimage.distance_transform_edt(~src) * cell / 1000.0
        visible |= d <= 3.57 * (2 ** 0.5 + max(H, 0) ** 0.5)
    return dist_km, visible


def closed_sea(rule, z, sea, cell, _cache={}):
    key = (id(z), cell)
    if key not in _cache:
        _cache[key] = coast_masks(z, sea, cell)
    dist_km, visible = _cache[key]
    if rule in (None, "none"):
        return None
    if rule == "in_sight":
        return sea & ~visible
    D = float(rule.split("_")[1])
    return sea & (dist_km > D)
