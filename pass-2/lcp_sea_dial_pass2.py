#!/usr/bin/env python3
"""
Bluestone sea-vs-land dial — PASS 2
Locked BEFORE run. Amendment A2 in ../PROTOCOL.md.
Terrain 50 @ 200 m. No finer grain. No blog.
"""
from __future__ import annotations
import csv, json, math, time, heapq
from pathlib import Path
from datetime import datetime

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LightSource
import geopandas as gpd
from shapely.ops import unary_union

# ---------------------------------------------------------------------------
# LOCKED BEFORE PASS-2 RUN (see PROTOCOL A2)
# ---------------------------------------------------------------------------
DEM_SOURCE = "OS Terrain 50 ASCII Grid OGL @ 200 m working grid"
WORKING_CELL_M = 200
BBOX = dict(xmin=120000, xmax=450000, ymin=10000, ymax=260000)  # expanded for Land's End
STARTS = {
    "Carn_Goedog": (212878.0, 233160.0),
    "Craig_Rhos_y_felin": (211650.0, 236140.0),
}
END = ("Stonehenge", 412250.0, 142200.0)

M_WATER_GRID = [0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
RIVER_MODES = ["ignore", "barrier", "conduit"]
COASTAL_MODES = ["bristol_channel", "full_coast"]

# Coastal reach mechanism (locked):
#   bristol_channel — sea cells with OSGB easting < COAST_WEST_LIMIT are IMPASSABLE
#   full_coast — all DEM sea cells traversable at m_water
COAST_WEST_LIMIT = 200000  # metres OSGB easting

# River dial (locked):
#   ignore — sea/estuary only
#   barrier — river cells step cost = RIVER_BARRIER_MULT * d
#   conduit — river cells treated as water (cost m_water * d)
RIVER_BARRIER_MULT = 100.0
RIVER_BUFFER_M = 400.0  # coarse buffer onto 200 m grid
RIVER_SOURCE = "OS Open Rivers (OGL) named: Afon Teifi/Tywi/Wysg/Gwy/Hafren, River Avon (+ Afon Gwy covers Wye in-frame)"

W_UP = 4.0
W_DN = 2.6
WATER_ELEV_MAX = 0.0
SEA_FRAC_THRESH = 0.25
INLAND_FRAC_THRESH = 0.10

OUT = Path("/workspace/projects/bluestone-sea-dial/pass-2")
RIVER_GPKG = Path("/workspace/projects/bluestone-sea-dial/data/rivers/major_rivers_pass2.gpkg")
# ---------------------------------------------------------------------------

NEIGH = [
    (-1, 0, 1.0), (1, 0, 1.0), (0, -1, 1.0), (0, 1, 1.0),
    (-1, -1, math.sqrt(2)), (-1, 1, math.sqrt(2)),
    (1, -1, math.sqrt(2)), (1, 1, math.sqrt(2)),
]


def xy_to_rc(x, y, info):
    c = int((x - info["xmin"]) / info["cell"])
    r = int((info["ymax"] - y) / info["cell"])
    return r, c


def rc_to_xy(r, c, info):
    x = info["xmin"] + (c + 0.5) * info["cell"]
    y = info["ymax"] - (r + 0.5) * info["cell"]
    return x, y


def rasterize_rivers(info, path_gpkg) -> np.ndarray:
    H, W = info["height"], info["width"]
    cell = info["cell"]
    rivers = gpd.read_file(path_gpkg).to_crs(epsg=27700)
    # buffer then burn
    geom = unary_union(rivers.geometry.buffer(RIVER_BUFFER_M))
    mask = np.zeros((H, W), dtype=bool)
    # sample grid centres against prepared geometry
    from shapely.prepared import prep
    prep_g = prep(geom)
    # blockwise for speed
    ys = info["ymax"] - (np.arange(H) + 0.5) * cell
    xs = info["xmin"] + (np.arange(W) + 0.5) * cell
    # Use geopandas points overlay in chunks
    from shapely.geometry import Point
    for r in range(H):
        y = float(ys[r])
        # only columns that might intersect bounds
        minx, miny, maxx, maxy = geom.bounds
        c0 = max(0, int((minx - info["xmin"]) / cell) - 2)
        c1 = min(W, int((maxx - info["xmin"]) / cell) + 3)
        if y < miny - RIVER_BUFFER_M or y > maxy + RIVER_BUFFER_M:
            continue
        for c in range(c0, c1):
            if prep_g.contains(Point(float(xs[c]), y)) or prep_g.intersects(Point(float(xs[c]), y)):
                mask[r, c] = True
        if r % 200 == 0:
            print(f"  river rasterize row {r}/{H}", flush=True)
    return mask


def rasterize_rivers_fast(info, path_gpkg) -> np.ndarray:
    """Burn buffered rivers via skimage / shapely coords onto grid."""
    from rasterio import features
    from rasterio.transform import from_origin
    H, W = info["height"], info["width"]
    cell = info["cell"]
    rivers = gpd.read_file(path_gpkg).to_crs(epsg=27700)
    buffered = rivers.copy()
    buffered["geometry"] = buffered.buffer(RIVER_BUFFER_M)
    transform = from_origin(info["xmin"], info["ymax"], cell, cell)
    shapes = [(geom, 1) for geom in buffered.geometry if geom is not None and not geom.is_empty]
    mask = features.rasterize(
        shapes=shapes,
        out_shape=(H, W),
        transform=transform,
        fill=0,
        dtype=np.uint8,
    ).astype(bool)
    return mask


def build_sea_mask(dem, info, coastal_reach):
    sea = np.isfinite(dem) & (dem < WATER_ELEV_MAX)
    if coastal_reach == "bristol_channel":
        # columns with easting < COAST_WEST_LIMIT impassable as sea
        xs = info["xmin"] + (np.arange(info["width"]) + 0.5) * info["cell"]
        west = xs < COAST_WEST_LIMIT
        sea[:, west] = False  # remove western sea from traversable water
        # Those cells become impassable nodata-like for water travel; treat as blocked
        blocked_west_sea = (np.isfinite(dem) & (dem < WATER_ELEV_MAX)) & west[np.newaxis, :]
        return sea, blocked_west_sea
    elif coastal_reach == "full_coast":
        return sea, np.zeros(dem.shape, dtype=bool)
    else:
        raise ValueError(coastal_reach)


def least_cost_path(z, water, river, river_mode, blocked, info, start_rc, end_rc, m_water):
    H, W = z.shape
    cell = info["cell"]
    sr, sc = start_rc
    er, ec = end_rc
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
        for dr, dc, diag in NEIGH:
            rr, cc = r + dr, c + dc
            if rr < 0 or rr >= H or cc < 0 or cc >= W:
                continue
            if blocked[rr, cc]:
                continue
            zb = z[rr, cc]
            if not np.isfinite(zb):
                continue
            d = cell * diag
            dest_water = bool(water[rr, cc])
            dest_river = bool(river[rr, cc])

            # River modes
            if river_mode == "barrier" and dest_river and not dest_water:
                cost = RIVER_BARRIER_MULT * d
            elif river_mode == "conduit" and (dest_water or dest_river):
                cost = m_water * d
            elif dest_water:
                cost = m_water * d
            else:
                # land
                slope = (float(zb) - za) / d
                up = max(slope, 0.0)
                dn = max(-slope, 0.0)
                cost = d * (1.0 + W_UP * up + W_DN * dn)

            nd = cd + cost
            if nd < dist[rr, cc]:
                dist[rr, cc] = nd
                parent[rr, cc] = (r, c)
                heapq.heappush(heap, (nd, rr, cc))

    total = dist[er, ec]
    if total >= INF / 2:
        return None
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

    length = water_len = river_len = 0.0
    for i in range(len(path) - 1):
        r0, c0 = path[i]
        r1, c1 = path[i + 1]
        diag = math.sqrt(2) if (r0 != r1 and c0 != c1) else 1.0
        d = cell * diag
        length += d
        if water[r1, c1]:
            water_len += d
        if river[r1, c1] and not water[r1, c1]:
            river_len += d
    return total, path, length, water_len / length if length else 0.0, river_len / length if length else 0.0


def regime_label(water_frac):
    if water_frac >= SEA_FRAC_THRESH:
        return "sea-preferring"
    if water_frac <= INLAND_FRAC_THRESH:
        return "inland-preferring"
    return "mixed/unresolved"


def classify_path(path, info, water):
    """Land's End / corridor / Severn approach heuristics."""
    xs, ys = [], []
    on_water_west = False
    on_water_south = False
    for r, c in path:
        x, y = rc_to_xy(r, c, info)
        xs.append(x); ys.append(y)
        if water[r, c]:
            if x < 160000:
                on_water_west = True
            if y < 80000:
                on_water_south = True
    lands_end = on_water_west and on_water_south  # around Cornwall
    # weaker: any water south of 100000 with x < 250000
    lands_end_weak = any(water[r, c] and rc_to_xy(r, c, info)[1] < 100000 and rc_to_xy(r, c, info)[0] < 280000 for r, c in path)

    # Severn crossing at E=340000
    sev = "none"
    for i in range(len(xs) - 1):
        if (xs[i] - 340000) * (xs[i + 1] - 340000) <= 0 and abs(xs[i + 1] - xs[i]) > 0:
            y = ys[i]
            if y >= 220000:
                sev = "Hereford-side"
            elif y >= 200000:
                sev = "Monmouth-side"
            elif y >= 170000:
                sev = "lower-Severn"
            else:
                sev = "Bristol-Channel"
            break

    # A40 / Teifi–Usk–Wye style: inland path through Wales with mean N in Welsh section (x<340k) >= 200000
    welsh = [(x, y) for x, y in zip(xs, ys) if x < 340000]
    if welsh:
        mean_n = sum(y for _, y in welsh) / len(welsh)
        # also check not hugging south coast (mean N of land cells)
        land_welsh = [(x, y) for (x, y), (r, c) in zip(zip(xs, ys), path) if x < 340000 and not water[r, c]]
        mean_land_n = (sum(y for _, y in land_welsh) / len(land_welsh)) if land_welsh else mean_n
        a40ish = mean_land_n >= 200000 and not lands_end and not lands_end_weak
    else:
        a40ish = False
        mean_land_n = float("nan")

    return dict(
        lands_end=bool(lands_end or lands_end_weak),
        lands_end_strict=bool(lands_end),
        severn_approach=sev,
        a40_teifi_usk_wye=bool(a40ish),
        welsh_mean_land_N=round(mean_land_n, 0) if mean_land_n == mean_land_n else None,
    )


def nudge_land(z, water, blocked, rc):
    r, c = rc
    if np.isfinite(z[r, c]) and not water[r, c] and not blocked[r, c]:
        return rc
    H, W = z.shape
    for rad in range(1, 25):
        for dr in range(-rad, rad + 1):
            for dc in range(-rad, rad + 1):
                rr, cc = r + dr, c + dc
                if 0 <= rr < H and 0 <= cc < W:
                    if np.isfinite(z[rr, cc]) and not water[rr, cc] and not blocked[rr, cc]:
                        return (rr, cc)
    raise SystemExit(f"cannot place {rc}")


def plot_map(hs, sea_show, river, info, paths, title, out_png):
    fig, ax = plt.subplots(figsize=(12, 9), dpi=110)
    extent = [info["xmin"], info["xmax"], info["ymin"], info["ymax"]]
    ax.imshow(hs, cmap="gray", extent=extent, origin="upper", alpha=0.9)
    ww = np.ma.masked_where(~sea_show, np.ones_like(sea_show, float))
    ax.imshow(ww, cmap="Blues", extent=extent, origin="upper", alpha=0.35, vmin=0, vmax=1)
    rr = np.ma.masked_where(~river, np.ones_like(river, float))
    ax.imshow(rr, cmap="Greens", extent=extent, origin="upper", alpha=0.25, vmin=0, vmax=1)
    colours = plt.cm.tab10.colors
    for i, (label, path) in enumerate(paths.items()):
        xs, ys = zip(*(rc_to_xy(r, c, info) for r, c in path))
        ax.plot(xs, ys, color=colours[i % 10], lw=1.4, label=label)
    ax.plot(STARTS["Carn_Goedog"][0], STARTS["Carn_Goedog"][1], "ro", ms=5)
    ax.plot(END[1], END[2], "k*", ms=11, label="Stonehenge")
    # coast limit line
    ax.axvline(COAST_WEST_LIMIT, color="cyan", ls="--", lw=0.8, alpha=0.7, label=f"coast limit E{COAST_WEST_LIMIT}")
    ax.set_title(title, fontsize=10)
    ax.legend(loc="lower left", fontsize=6)
    ax.set_aspect("equal")
    ax.set_xlabel("OSGB easting"); ax.set_ylabel("OSGB northing")
    fig.tight_layout()
    fig.savefig(out_png)
    plt.close(fig)
    print("Wrote", out_png, flush=True)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    lock = dict(
        locked_at=datetime.now().isoformat(timespec="seconds"),
        pass_name="pass-2",
        DEM_SOURCE=DEM_SOURCE,
        WORKING_CELL_M=WORKING_CELL_M,
        BBOX=BBOX,
        STARTS=STARTS,
        END=END,
        M_WATER_GRID=M_WATER_GRID,
        RIVER_MODES=RIVER_MODES,
        COASTAL_MODES=COASTAL_MODES,
        COAST_WEST_LIMIT=COAST_WEST_LIMIT,
        coastal_mechanism={
            "bristol_channel": f"sea cells with easting < {COAST_WEST_LIMIT} impassable",
            "full_coast": "all DEM sea (elev<0) traversable at m_water",
        },
        RIVER_BARRIER_MULT=RIVER_BARRIER_MULT,
        RIVER_BUFFER_M=RIVER_BUFFER_M,
        RIVER_SOURCE=RIVER_SOURCE,
        W_UP=W_UP, W_DN=W_DN,
        WATER_ELEV_MAX=WATER_ELEV_MAX,
        SEA_FRAC_THRESH=SEA_FRAC_THRESH,
        INLAND_FRAC_THRESH=INLAND_FRAC_THRESH,
        overland="d*(1+W_UP*up+W_DN*dn)",
        water_step="m_water*d when dest is water (or river if conduit)",
    )
    (OUT / "LOCKED_params.json").write_text(json.dumps(lock, indent=2))
    print("LOCKED", flush=True)

    dem = np.load(OUT / "dem_mosaic_200m.npy")
    info = json.loads((OUT / "dem_info.json").read_text())
    assert info["cell"] == WORKING_CELL_M

    river_path = OUT / "river_mask.npy"
    if river_path.exists():
        river = np.load(river_path).astype(bool)
        print("loaded river mask", river.mean(), flush=True)
    else:
        print("rasterizing rivers...", flush=True)
        try:
            river = rasterize_rivers_fast(info, RIVER_GPKG)
        except Exception as e:
            print("rasterio burn failed", e, "fallback slow", flush=True)
            river = rasterize_rivers(info, RIVER_GPKG)
        np.save(river_path, river)
        print("river cells", int(river.sum()), f"({100*river.mean():.2f}%)", flush=True)

    # base z: sea elev -> 0 for slope from land
    z_base = dem.copy()
    sea_all = np.isfinite(dem) & (dem < WATER_ELEV_MAX)
    z_base[sea_all] = 0.0
    nodata = ~np.isfinite(dem)

    end_rc = xy_to_rc(END[1], END[2], info)
    rows = []
    paths = {}  # key -> path

    t0 = time.time()
    nrun = 0
    total_runs = len(STARTS) * len(M_WATER_GRID) * len(RIVER_MODES) * len(COASTAL_MODES)
    for coastal in COASTAL_MODES:
        sea, blocked_west = build_sea_mask(dem, info, coastal)
        # blocked = west sea under bristol mode OR original nodata (non-sea)
        blocked = blocked_west | (nodata & ~sea_all)
        # Under bristol_channel, western sea is blocked entirely
        z = z_base.copy()
        z[blocked] = np.nan

        for river_mode in RIVER_MODES:
            for sname, (sx, sy) in STARTS.items():
                src = nudge_land(z, sea, blocked, xy_to_rc(sx, sy, info))
                er = nudge_land(z, sea, blocked, end_rc)
                for m in M_WATER_GRID:
                    nrun += 1
                    print(f"[{nrun}/{total_runs}] {sname} m={m} river={river_mode} coast={coastal}", flush=True)
                    t1 = time.time()
                    # water for conduit includes rivers via cost rule; sea mask separate
                    result = least_cost_path(z, sea, river, river_mode, blocked, info, src, er, m)
                    elapsed = time.time() - t1
                    if result is None:
                        rows.append(dict(
                            start=sname, m_water=m, river_mode=river_mode, coastal_reach=coastal,
                            total_cost="", length_m="", water_fraction="", river_fraction="",
                            regime="NO_PATH", lands_end="", severn_approach="", a40_teifi_usk_wye="",
                            runtime_s=round(elapsed, 1),
                        ))
                        continue
                    total, path, length, wfrac, rfrac = result
                    reg = regime_label(wfrac)
                    cls = classify_path(path, info, sea)
                    print(f"  cost={total:.0f} len={length/1000:.0f}km water={wfrac:.3f} {reg} "
                          f"LE={cls['lands_end']} A40={cls['a40_teifi_usk_wye']} Sev={cls['severn_approach']} [{elapsed:.1f}s]",
                          flush=True)
                    rows.append(dict(
                        start=sname, m_water=m, river_mode=river_mode, coastal_reach=coastal,
                        total_cost=round(total, 1), length_m=round(length, 1),
                        water_fraction=round(wfrac, 4), river_fraction=round(rfrac, 4),
                        regime=reg, lands_end=cls["lands_end"], lands_end_strict=cls["lands_end_strict"],
                        severn_approach=cls["severn_approach"],
                        a40_teifi_usk_wye=cls["a40_teifi_usk_wye"],
                        welsh_mean_land_N=cls["welsh_mean_land_N"],
                        runtime_s=round(elapsed, 1),
                    ))
                    paths[(sname, m, river_mode, coastal)] = path

    csv_path = OUT / "results_table.csv"
    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    print("Wrote", csv_path, flush=True)

    # Hillshade from full dem
    zz = z_base.copy(); zz[~np.isfinite(zz)] = 0
    ls = LightSource(azdeg=315, altdeg=45)
    hs = ls.hillshade(zz, vert_exag=1.5, dx=WORKING_CELL_M, dy=WORKING_CELL_M)
    sea_show = sea_all

    # Maps
    # 1) Land's End candidate if any
    le_keys = [k for k, r in zip(paths.keys(), rows) if r.get("lands_end") is True or r.get("lands_end") == True]
    # rebuild from rows
    le_rows = [r for r in rows if r.get("lands_end") == True or r.get("lands_end") == "True"]
    if any(r["lands_end"] is True for r in rows):
        # pick cheapest water full_coast ignore Carn
        cands = [r for r in rows if r["lands_end"] is True and r["start"] == "Carn_Goedog"]
        cands.sort(key=lambda r: (r["m_water"], r["river_mode"]))
        r0 = cands[0]
        key = (r0["start"], r0["m_water"], r0["river_mode"], r0["coastal_reach"])
        plot_map(hs, sea_show, river, info,
                 {f"LE m={r0['m_water']} {r0['river_mode']} {r0['coastal_reach']}": paths[key]},
                 f"Land's End path appears (m_water={r0['m_water']}, {r0['coastal_reach']}, rivers={r0['river_mode']})",
                 OUT / "map_lands_end.png")
    else:
        # show full_coast m=0.05 vs bristol m=0.05 for contrast
        k1 = ("Carn_Goedog", 0.05, "ignore", "full_coast")
        k2 = ("Carn_Goedog", 0.05, "ignore", "bristol_channel")
        d = {}
        if k1 in paths: d["full_coast m=0.05"] = paths[k1]
        if k2 in paths: d["bristol_channel m=0.05"] = paths[k2]
        if d:
            plot_map(hs, sea_show, river, info, d,
                     "Very cheap water: full_coast vs bristol_channel (no Land's End flag)",
                     OUT / "map_cheap_water_coast_compare.png")

    # 2) Switch bracket bristol ignore
    k_sea = ("Carn_Goedog", 1.0, "ignore", "bristol_channel")
    k_inl = ("Carn_Goedog", 2.0, "ignore", "bristol_channel")
    d = {}
    if k_sea in paths: d["sea m=1 ignore bristol"] = paths[k_sea]
    if k_inl in paths: d["inland m=2 ignore bristol"] = paths[k_inl]
    if d:
        plot_map(hs, sea_show, river, info, d, "Switch bracket (bristol_channel, rivers=ignore)",
                 OUT / "map_switch_bristol_ignore.png")

    # 3) River modes at m=2 bristol
    d = {}
    for rm in RIVER_MODES:
        k = ("Carn_Goedog", 2.0, rm, "bristol_channel")
        if k in paths:
            d[f"m=2 {rm}"] = paths[k]
    if d:
        plot_map(hs, sea_show, river, info, d, "River dial at m_water=2 (bristol_channel)",
                 OUT / "map_river_modes_m2.png")

    # 4) A40 inland high m
    k = ("Carn_Goedog", 10.0, "ignore", "bristol_channel")
    if k in paths:
        plot_map(hs, sea_show, river, info, {"m=10 ignore bristol": paths[k],
                                             "Craig same": paths.get(("Craig_Rhos_y_felin", 10.0, "ignore", "bristol_channel"), paths[k])},
                 "Inland high m (A40 / Teifi–Usk–Wye check)",
                 OUT / "map_inland_m10.png")

    # 5) Conduit rivers sea-preferring
    k = ("Carn_Goedog", 0.5, "conduit", "bristol_channel")
    if k in paths:
        plot_map(hs, sea_show, river, info,
                 {"conduit m=0.5": paths[k], "ignore m=0.5": paths.get(("Carn_Goedog", 0.5, "ignore", "bristol_channel"), paths[k])},
                 "Conduit vs ignore at m=0.5 (bristol_channel)",
                 OUT / "map_conduit_vs_ignore_m0.5.png")

    # 6) full coast switch if different
    k1 = ("Carn_Goedog", 1.0, "ignore", "full_coast")
    k2 = ("Carn_Goedog", 2.0, "ignore", "full_coast")
    d = {}
    if k1 in paths: d["full m=1"] = paths[k1]
    if k2 in paths: d["full m=2"] = paths[k2]
    if d:
        plot_map(hs, sea_show, river, info, d, "Switch bracket (full_coast, rivers=ignore)",
                 OUT / "map_switch_full_coast_ignore.png")

    meta = dict(elapsed_s=round(time.time() - t0, 1), n_rows=len(rows),
                lands_end_count=sum(1 for r in rows if r["lands_end"] is True),
                a40_count=sum(1 for r in rows if r["a40_teifi_usk_wye"] is True))
    (OUT / "run_meta.json").write_text(json.dumps(meta, indent=2))
    print("DONE", meta, flush=True)


if __name__ == "__main__":
    main()
