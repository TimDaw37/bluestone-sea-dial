#!/usr/bin/env python3
"""
Bluestone sea-vs-land dial — FIRST PASS (cheap and cheerful)
Locked BEFORE run 1. Do not change mid-sweep.

Protocol: ../PROTOCOL.md
Approved decisions (Tim): DEM=OS Terrain 50; m_water grid as below;
water-fraction cut-offs 0.25 / 0.10; secondary dials only if main ambiguous.
"""

from __future__ import annotations
import csv, json, math, os, time, heapq
from pathlib import Path
from datetime import datetime

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LightSource

# ---------------------------------------------------------------------------
# LOCKED BEFORE RUN 1
# ---------------------------------------------------------------------------
DEM_SOURCE = "OS Terrain 50 (ASCII Grid), OGL — from terr50_gagg_gb / flyover cache"
DEM_VERSION_NOTE = "tiles dated 20260529 in supply zip"
WORKING_CELL_M = 200  # first-pass working grid; Terrain 50 source posts are 50 m
# Study frame OSGB (EPSG:27700), chosen before seeing paths:
BBOX = dict(xmin=180000, xmax=440000, ymin=120000, ymax=260000)
# Endpoints (OSGB), checked sources:
#   Carn Goedog: britishplacenames SN128331 → 212878, 233160
#   Craig Rhos-y-felin: Coflein SN1165036140 → 211650, 236140
#   Stonehenge centroid: ~SU122422 → 412250, 142200 (monument centre)
STARTS = {
    "Carn_Goedog": (212878.0, 233160.0),
    "Craig_Rhos_y_felin": (211650.0, 236140.0),
}
END = ("Stonehenge", 412250.0, 142200.0)

M_WATER_GRID = [0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 25.0, 50.0]
SEA_FRAC_THRESH = 0.25
INLAND_FRAC_THRESH = 0.10

# Slope cost (overland), anisotropic, Tobler-ish simple form:
#   cost(a→b) = d * (1 + W_UP * up + W_DN * dn)
#   up = max((z_b-z_a)/d, 0); dn = max((z_a-z_b)/d, 0)
W_UP = 4.0
W_DN = 0.65 * W_UP  # 2.6

# Water definition (locked):
#   Water cell iff elev < WATER_ELEV_MAX (OS Terrain 50 encodes sea ≈ -1.5 m).
#   Major rivers NOT separately digitised in v1 — sea + estuary from DEM only.
#   Step cost if BOTH endpoints are water OR the destination is water:
#       cost = m_water * d
#     (i.e. m_water × zero-slope overland step cost, since overland base = 1*d)
#   Else overland slope formula.
WATER_ELEV_MAX = 0.0  # metres OD; cells strictly below this are water

TILE_DIR = Path("/workspace/projects/bluestone-sea-dial/data/terr50_tiles")
OUT_DIR = Path("/workspace/projects/bluestone-sea-dial/first-pass")
# ---------------------------------------------------------------------------


def read_asc(path: Path):
    meta = {}
    with open(path) as f:
        for _ in range(5):
            k, v = f.readline().split()
            meta[k.lower()] = float(v) if "." in v or "e" in v.lower() else int(float(v))
        # optional NODATA
        pos = f.tell()
        line = f.readline()
        if line.lower().startswith("nodata"):
            meta["nodata_value"] = float(line.split()[1])
        else:
            f.seek(pos)
            meta["nodata_value"] = -9999
        data = np.loadtxt(f, dtype=np.float32)
    return meta, data


def mosaic_bbox(tile_dir: Path, bbox: dict, cell_out: int) -> tuple[np.ndarray, dict]:
    """Build DEM mosaic and resample to cell_out metres."""
    xmin, xmax, ymin, ymax = bbox["xmin"], bbox["xmax"], bbox["ymin"], bbox["ymax"]
    # Terrain 50 native 50 m
    native = 50
    width = int((xmax - xmin) / native)
    height = int((ymax - ymin) / native)
    dem = np.full((height, width), np.nan, dtype=np.float32)

    asc_files = sorted(tile_dir.glob("*.asc"))
    used = 0
    for path in asc_files:
        meta, data = read_asc(path)
        x0 = meta["xllcorner"]
        y0 = meta["yllcorner"]
        cs = meta["cellsize"]
        assert cs == native
        nrows, ncols = data.shape
        # tile covers [x0, x0+ncols*cs) × [y0, y0+nrows*cs)
        tx1, ty1 = x0 + ncols * cs, y0 + nrows * cs
        if tx1 <= xmin or x0 >= xmax or ty1 <= ymin or y0 >= ymax:
            continue
        # place into mosaic; ASC row 0 = north
        for r in range(nrows):
            gy = y0 + (nrows - 1 - r) * cs + cs / 2  # cell centre
            if gy < ymin or gy >= ymax:
                continue
            mr = int((ymax - gy) / native)  # row 0 = north
            if mr < 0 or mr >= height:
                continue
            for c in range(ncols):
                gx = x0 + c * cs + cs / 2
                if gx < xmin or gx >= xmax:
                    continue
                mc = int((gx - xmin) / native)
                if 0 <= mc < width:
                    dem[mr, mc] = data[r, c]
        used += 1
    print(f"Mosaic: {used} tiles, native shape {dem.shape}", flush=True)

    # Resample by block mean
    factor = cell_out // native
    assert cell_out % native == 0
    h2 = (height // factor) * factor
    w2 = (width // factor) * factor
    dem = dem[:h2, :w2]
    dem = dem.reshape(h2 // factor, factor, w2 // factor, factor)
    # nanmean over blocks
    with np.errstate(all="ignore"):
        out = np.nanmean(dem, axis=(1, 3)).astype(np.float32)

    info = dict(
        xmin=xmin, ymax=ymax, cell=cell_out,
        width=out.shape[1], height=out.shape[0],
        xmax=xmin + out.shape[1] * cell_out,
        ymin=ymax - out.shape[0] * cell_out,
        tiles_used=used,
    )
    return out, info


def xy_to_rc(x, y, info):
    c = int((x - info["xmin"]) / info["cell"])
    r = int((info["ymax"] - y) / info["cell"])
    return r, c


def rc_to_xy(r, c, info):
    x = info["xmin"] + (c + 0.5) * info["cell"]
    y = info["ymax"] - (r + 0.5) * info["cell"]
    return x, y


def build_water_mask(dem: np.ndarray) -> np.ndarray:
    # Sea / estuary: elev < 0. Treat NaN as impassable land-gap (not water highway)
    water = np.zeros(dem.shape, dtype=bool)
    valid = np.isfinite(dem)
    water[valid & (dem < WATER_ELEV_MAX)] = True
    return water


def fill_sea_elev(dem: np.ndarray, water: np.ndarray) -> np.ndarray:
    """For slope calc on land only; water cells get 0 so adjacent land slopes sane."""
    z = dem.copy()
    z[water] = 0.0
    # fill remaining NaN as impassable — set very high elev so we block them
    z[~np.isfinite(z)] = np.nan
    return z


def step_cost(za, zb, d, a_water, b_water, m_water):
    """Locked step cost a→b."""
    if a_water and b_water:
        return m_water * d
    if b_water:  # stepping onto water
        return m_water * d
    if a_water and not b_water:  # landing
        # use overland formula toward land elevation
        slope = (zb - za) / d
        up = max(slope, 0.0)
        dn = max(-slope, 0.0)
        return d * (1.0 + W_UP * up + W_DN * dn)
    # land → land
    slope = (zb - za) / d
    up = max(slope, 0.0)
    dn = max(-slope, 0.0)
    return d * (1.0 + W_UP * up + W_DN * dn)


NEIGH = [
    (-1, 0, 1.0), (1, 0, 1.0), (0, -1, 1.0), (0, 1, 1.0),
    (-1, -1, math.sqrt(2)), (-1, 1, math.sqrt(2)),
    (1, -1, math.sqrt(2)), (1, 1, math.sqrt(2)),
]


def least_cost_path(z, water, info, start_rc, end_rc, m_water):
    """Dijkstra on 8-neighbour grid. Returns (cost, path_rcs, length_m, water_frac)."""
    H, W = z.shape
    cell = info["cell"]
    sr, sc = start_rc
    er, ec = end_rc
    if not (0 <= sr < H and 0 <= sc < W and 0 <= er < H and 0 <= ec < W):
        raise ValueError(f"start/end out of frame: {start_rc} {end_rc}")
    if not np.isfinite(z[sr, sc]) or not np.isfinite(z[er, ec]):
        raise ValueError("start/end on nodata")
    # starts should be on land
    INF = 1e100
    dist = np.full((H, W), INF, dtype=np.float64)
    parent = np.full((H, W, 2), -1, dtype=np.int32)
    dist[sr, sc] = 0.0
    heap = [(0.0, sr, sc)]
    while heap:
        cd, r, c = heapq.heappop(heap)
        if cd > dist[r, c]:
            continue
        if r == er and c == ec:
            break
        za = float(z[r, c])
        aw = bool(water[r, c])
        for dr, dc, diag in NEIGH:
            rr, cc = r + dr, c + dc
            if rr < 0 or rr >= H or cc < 0 or cc >= W:
                continue
            zb = z[rr, cc]
            if not np.isfinite(zb):
                continue
            d = cell * diag
            bw = bool(water[rr, cc])
            # Impassable: nodata already skipped. Allow water cells always.
            cost = step_cost(za, float(zb), d, aw, bw, m_water)
            nd = cd + cost
            if nd < dist[rr, cc]:
                dist[rr, cc] = nd
                parent[rr, cc] = (r, c)
                heapq.heappush(heap, (nd, rr, cc))
    total = dist[er, ec]
    if total >= INF / 2:
        return None

    # reconstruct
    path = []
    r, c = er, ec
    while True:
        path.append((r, c))
        if r == sr and c == sc:
            break
        pr, pc = int(parent[r, c, 0]), int(parent[r, c, 1])
        if pr < 0:
            return None
        r, c = pr, pc
    path.reverse()

    # length and water fraction (by step length)
    length = 0.0
    water_len = 0.0
    for i in range(len(path) - 1):
        r0, c0 = path[i]
        r1, c1 = path[i + 1]
        diag = math.sqrt(2) if (r0 != r1 and c0 != c1) else 1.0
        d = cell * diag
        length += d
        # count as water if destination is water (consistent with cost rule)
        if water[r1, c1]:
            water_len += d
    water_frac = water_len / length if length > 0 else 0.0
    return total, path, length, water_frac


def regime_label(water_frac: float) -> str:
    if water_frac >= SEA_FRAC_THRESH:
        return "sea-preferring"
    if water_frac <= INLAND_FRAC_THRESH:
        return "inland-preferring"
    return "mixed/unresolved"


def severn_approach(path, info) -> str:
    """Rough: where path crosses easting 340000 (approx Wye/Severn corridor)."""
    xs, ys = [], []
    for r, c in path:
        x, y = rc_to_xy(r, c, info)
        xs.append(x)
        ys.append(y)
    # find crossing of x=340000 going eastward
    target = 340000
    for i in range(len(xs) - 1):
        if xs[i] < target <= xs[i + 1] or xs[i] > target >= xs[i + 1]:
            y = ys[i]
            if y >= 220000:
                return "Hereford-side (north)"
            if y >= 200000:
                return "Monmouth-side"
            if y >= 170000:
                return "lower Severn / estuary"
            return "Bristol Channel south"
    # if path is mostly sea, report water entry
    return "no clear 340kmE land crossing (likely sea-dominated)"


def make_hillshade(z, water):
    zz = z.copy()
    zz[water] = 0
    zz[~np.isfinite(zz)] = 0
    ls = LightSource(azdeg=315, altdeg=45)
    hs = ls.hillshade(zz, vert_exag=2.0, dx=WORKING_CELL_M, dy=WORKING_CELL_M)
    return hs


def plot_paths(hs, water, info, paths_dict, title, out_png):
    fig, ax = plt.subplots(figsize=(12, 7), dpi=120)
    extent = [info["xmin"], info["xmax"], info["ymin"], info["ymax"]]
    ax.imshow(hs, cmap="gray", extent=extent, origin="upper", alpha=0.9)
    # water wash
    ww = np.ma.masked_where(~water, np.ones_like(water, dtype=float))
    ax.imshow(ww, cmap="Blues", extent=extent, origin="upper", alpha=0.35, vmin=0, vmax=1)
    colours = {"Carn_Goedog": "crimson", "Craig_Rhos_y_felin": "darkorange"}
    for name, (path, m_w, reg) in paths_dict.items():
        xs, ys = zip(*(rc_to_xy(r, c, info) for r, c in path))
        ax.plot(xs, ys, color=colours.get(name, "red"), lw=1.5, label=f"{name} m={m_w} ({reg})")
    # endpoints
    for name, (x, y) in STARTS.items():
        ax.plot(x, y, "o", color=colours.get(name, "red"), ms=6)
    ax.plot(END[1], END[2], "k*", ms=12, label="Stonehenge")
    ax.set_title(title)
    ax.set_xlabel("OSGB easting")
    ax.set_ylabel("OSGB northing")
    ax.legend(loc="lower left", fontsize=7)
    ax.set_aspect("equal")
    fig.tight_layout()
    fig.savefig(out_png)
    plt.close(fig)
    print("Wrote", out_png, flush=True)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    lock = {
        "locked_at": datetime.now().isoformat(timespec="seconds"),
        "DEM_SOURCE": DEM_SOURCE,
        "WORKING_CELL_M": WORKING_CELL_M,
        "BBOX": BBOX,
        "STARTS": STARTS,
        "END": END,
        "M_WATER_GRID": M_WATER_GRID,
        "SEA_FRAC_THRESH": SEA_FRAC_THRESH,
        "INLAND_FRAC_THRESH": INLAND_FRAC_THRESH,
        "W_UP": W_UP,
        "W_DN": W_DN,
        "WATER_ELEV_MAX": WATER_ELEV_MAX,
        "water_step_definition": "m_water * d when destination is water or both water; else d*(1+W_UP*up+W_DN*dn)",
        "rivers": "not separately digitised in v1; sea/estuary from DEM elev < 0 only",
    }
    with open(OUT_DIR / "LOCKED_params.json", "w") as f:
        json.dump(lock, f, indent=2)
    print("Locked params written", flush=True)

    dem50_path = OUT_DIR / "dem_mosaic_200m.npy"
    info_path = OUT_DIR / "dem_info.json"
    if dem50_path.exists() and info_path.exists():
        dem = np.load(dem50_path)
        info = json.loads(info_path.read_text())
        print("Loaded cached DEM", dem.shape, flush=True)
    else:
        print("Building mosaic (slow once)...", flush=True)
        dem, info = mosaic_bbox(TILE_DIR, BBOX, WORKING_CELL_M)
        np.save(dem50_path, dem)
        info_path.write_text(json.dumps(info, indent=2))
        print("Saved mosaic", dem.shape, info, flush=True)

    water = build_water_mask(dem)
    z = fill_sea_elev(dem, water)
    # mark original nodata impassable
    nodata = ~np.isfinite(dem)
    z[nodata & ~water] = np.nan

    print(f"Water cells: {water.sum()} / {water.size} ({100*water.mean():.1f}%)", flush=True)

    end_rc = xy_to_rc(END[1], END[2], info)
    # ensure end on land
    if water[end_rc]:
        raise SystemExit("Stonehenge fell in water mask — check bbox/coords")

    rows = []
    paths_by_key = {}  # (start, m) -> path

    for sname, (sx, sy) in STARTS.items():
        src = xy_to_rc(sx, sy, info)
        if water[src] or not np.isfinite(z[src]):
            # nudge to nearest land
            print(f"WARNING: {sname} not on land cell {src}, searching...", flush=True)
            found = None
            for rad in range(1, 20):
                for dr in range(-rad, rad + 1):
                    for dc in range(-rad, rad + 1):
                        rr, cc = src[0] + dr, src[1] + dc
                        if 0 <= rr < z.shape[0] and 0 <= cc < z.shape[1]:
                            if np.isfinite(z[rr, cc]) and not water[rr, cc]:
                                found = (rr, cc)
                                break
                    if found:
                        break
                if found:
                    break
            if not found:
                raise SystemExit(f"Cannot place start {sname}")
            src = found
            print(f"  nudged to {src} {rc_to_xy(*src, info)}", flush=True)

        for m in M_WATER_GRID:
            print(f"LCP {sname} m_water={m} ...", flush=True)
            t1 = time.time()
            result = least_cost_path(z, water, info, src, end_rc, m)
            elapsed = time.time() - t1
            if result is None:
                print("  FAILED — no path", flush=True)
                rows.append(dict(
                    start=sname, m_water=m, total_cost="", length_m="",
                    water_fraction="", regime="NO_PATH", severn_approach="",
                    runtime_s=round(elapsed, 1),
                ))
                continue
            total, path, length, wfrac = result
            reg = regime_label(wfrac)
            sev = severn_approach(path, info)
            print(f"  cost={total:.0f} len={length/1000:.1f}km water={wfrac:.3f} {reg} [{elapsed:.1f}s]", flush=True)
            rows.append(dict(
                start=sname, m_water=m, total_cost=round(total, 1),
                length_m=round(length, 1), water_fraction=round(wfrac, 4),
                regime=reg, severn_approach=sev, runtime_s=round(elapsed, 1),
            ))
            paths_by_key[(sname, m)] = (path, m, reg)

    # CSV
    csv_path = OUT_DIR / "results_table.csv"
    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print("Wrote", csv_path, flush=True)

    # Pick representative maps
    hs = make_hillshade(z, water)

    def pick(start, regime_want):
        cands = [(m, paths_by_key[(start, m)]) for (s, m) in paths_by_key if s == start and paths_by_key[(s, m)][2] == regime_want]
        return cands

    # inland: highest m that is inland-preferring (or m=50)
    # sea: lowest m that is sea-preferring (or m=0.1)
    # switch: first m where regime changes from sea to inland along increasing m
    maps_made = []
    for start in STARTS:
        sea_ms = [m for m in M_WATER_GRID if (start, m) in paths_by_key and paths_by_key[(start, m)][2] == "sea-preferring"]
        inl_ms = [m for m in M_WATER_GRID if (start, m) in paths_by_key and paths_by_key[(start, m)][2] == "inland-preferring"]
        mix_ms = [m for m in M_WATER_GRID if (start, m) in paths_by_key and paths_by_key[(start, m)][2] == "mixed/unresolved"]

    # Combined maps using Carn Goedog as primary (report both in table)
    start = "Carn_Goedog"
    sea_ms = [m for m in M_WATER_GRID if (start, m) in paths_by_key and paths_by_key[(start, m)][2] == "sea-preferring"]
    inl_ms = [m for m in M_WATER_GRID if (start, m) in paths_by_key and paths_by_key[(start, m)][2] == "inland-preferring"]

    if sea_ms:
        m = min(sea_ms)
        p = {start: paths_by_key[(start, m)], "Craig_Rhos_y_felin": paths_by_key[("Craig_Rhos_y_felin", m)]}
        png = OUT_DIR / f"map_sea_preferring_m{m}.png"
        plot_paths(hs, water, info, p, f"Sea-preferring example (m_water={m})", png)
        maps_made.append(png.name)
    if inl_ms:
        m = max(inl_ms)
        p = {start: paths_by_key[(start, m)], "Craig_Rhos_y_felin": paths_by_key[("Craig_Rhos_y_felin", m)]}
        png = OUT_DIR / f"map_inland_preferring_m{m}.png"
        plot_paths(hs, water, info, p, f"Inland-preferring example (m_water={m})", png)
        maps_made.append(png.name)

    # switch-point: find flip for Carn Goedog
    prev = None
    switch_pair = None
    for m in M_WATER_GRID:
        if (start, m) not in paths_by_key:
            continue
        reg = paths_by_key[(start, m)][2]
        if prev is not None and prev[1] != reg and "preferring" in prev[1] and "preferring" in reg:
            switch_pair = (prev[0], m, prev[1], reg)
        if "preferring" in reg or reg == "mixed/unresolved":
            prev = (m, reg)
    # also catch sea->mixed->inland: show first inland and last sea
    if sea_ms and inl_ms:
        m_lo, m_hi = max(sea_ms), min(inl_ms)
        p = {
            f"sea m={m_lo}": paths_by_key[(start, m_lo)],
            f"inland m={m_hi}": paths_by_key[(start, m_hi)],
        }
        # recolour hack — plot manually
        fig, ax = plt.subplots(figsize=(12, 7), dpi=120)
        extent = [info["xmin"], info["xmax"], info["ymin"], info["ymax"]]
        ax.imshow(hs, cmap="gray", extent=extent, origin="upper", alpha=0.9)
        ww = np.ma.masked_where(~water, np.ones_like(water, dtype=float))
        ax.imshow(ww, cmap="Blues", extent=extent, origin="upper", alpha=0.35, vmin=0, vmax=1)
        for label, (path, m_w, reg) in p.items():
            xs, ys = zip(*(rc_to_xy(r, c, info) for r, c in path))
            col = "dodgerblue" if "sea" in label else "sienna"
            ax.plot(xs, ys, color=col, lw=1.8, label=f"Carn Goedog {label} ({reg})")
        ax.plot(STARTS["Carn_Goedog"][0], STARTS["Carn_Goedog"][1], "ro", ms=6)
        ax.plot(END[1], END[2], "k*", ms=12, label="Stonehenge")
        ax.set_title(f"Switch bracket Carn Goedog: sea m≤{m_lo} vs inland m≥{m_hi}")
        ax.set_xlabel("OSGB easting")
        ax.set_ylabel("OSGB northing")
        ax.legend(loc="lower left", fontsize=8)
        ax.set_aspect("equal")
        fig.tight_layout()
        png = OUT_DIR / f"map_switch_bracket_m{m_lo}_to_m{m_hi}.png"
        fig.savefig(png)
        plt.close(fig)
        maps_made.append(png.name)
        print("Wrote", png, flush=True)

    # overview all m for Carn Goedog
    fig, ax = plt.subplots(figsize=(12, 7), dpi=120)
    extent = [info["xmin"], info["xmax"], info["ymin"], info["ymax"]]
    ax.imshow(hs, cmap="gray", extent=extent, origin="upper", alpha=0.9)
    ww = np.ma.masked_where(~water, np.ones_like(water, dtype=float))
    ax.imshow(ww, cmap="Blues", extent=extent, origin="upper", alpha=0.3, vmin=0, vmax=1)
    cmap = plt.cm.viridis
    for i, m in enumerate(M_WATER_GRID):
        if (start, m) not in paths_by_key:
            continue
        path, _, reg = paths_by_key[(start, m)]
        xs, ys = zip(*(rc_to_xy(r, c, info) for r, c in path))
        ax.plot(xs, ys, color=cmap(i / (len(M_WATER_GRID) - 1)), lw=1.0, alpha=0.85, label=f"m={m} {reg[:3]}")
    ax.plot(STARTS["Carn_Goedog"][0], STARTS["Carn_Goedog"][1], "ro", ms=6)
    ax.plot(END[1], END[2], "k*", ms=12)
    ax.set_title("Carn Goedog — all m_water (viridis: low→high)")
    ax.legend(loc="lower left", fontsize=6, ncol=2)
    ax.set_aspect("equal")
    fig.tight_layout()
    png = OUT_DIR / "map_all_m_carn_goedog.png"
    fig.savefig(png)
    plt.close(fig)
    maps_made.append(png.name)

    meta = dict(maps=maps_made, elapsed_s=round(time.time() - t0, 1), switch_pair=switch_pair,
                sea_ms_carn=sea_ms, inland_ms_carn=inl_ms)
    (OUT_DIR / "run_meta.json").write_text(json.dumps(meta, indent=2))
    print("DONE in", meta["elapsed_s"], "s", flush=True)


if __name__ == "__main__":
    main()
