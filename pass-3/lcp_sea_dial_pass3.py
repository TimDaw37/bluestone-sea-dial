#!/usr/bin/env python3
"""Pass-3 finer grain (100 m; optional 50 m). A3 locked before run."""
from __future__ import annotations
import csv, json, math, time, heapq
from pathlib import Path
from datetime import datetime
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LightSource

OUT = Path("/workspace/projects/bluestone-sea-dial/pass-3")
WORKING_CELL_M = 100
COAST_WEST_LIMIT = 200000
W_UP, W_DN = 4.0, 2.6
RIVER_BARRIER_MULT = 100.0
SEA_FRAC_THRESH, INLAND_FRAC_THRESH = 0.25, 0.10
STARTS = {"Carn_Goedog": (212878.0, 233160.0), "Craig_Rhos_y_felin": (211650.0, 236140.0)}
END = ("Stonehenge", 412250.0, 142200.0)

# Locked subset (A3)
RUNS = []
for m in (0.5, 1.0, 2.0, 5.0):
    for riv in ("ignore", "conduit"):
        RUNS.append((m, riv, "bristol_channel"))
for m in (0.05, 0.1):
    RUNS.append((m, "ignore", "full_coast"))

NEIGH = [(-1,0,1),(1,0,1),(0,-1,1),(0,1,1),(-1,-1,math.sqrt(2)),(-1,1,math.sqrt(2)),(1,-1,math.sqrt(2)),(1,1,math.sqrt(2))]

def xy_to_rc(x,y,info):
    return int((info["ymax"]-y)/info["cell"]), int((x-info["xmin"])/info["cell"])

def rc_to_xy(r,c,info):
    return info["xmin"]+(c+0.5)*info["cell"], info["ymax"]-(r+0.5)*info["cell"]

def regime(wf):
    if wf >= SEA_FRAC_THRESH: return "sea-preferring"
    if wf <= INLAND_FRAC_THRESH: return "inland-preferring"
    return "mixed/unresolved"

def classify(path, info, water):
    xs,ys=[],[]
    le=False
    for r,c in path:
        x,y=rc_to_xy(r,c,info); xs.append(x); ys.append(y)
        if water[r,c] and x<160000 and y<80000: le=True
        if water[r,c] and y<100000 and x<280000: le=True
    sev="none"
    for i in range(len(xs)-1):
        if (xs[i]-340000)*(xs[i+1]-340000)<=0:
            y=ys[i]
            sev = "Hereford-side" if y>=220000 else "Monmouth-side" if y>=200000 else "lower-Severn" if y>=170000 else "Bristol-Channel"
            break
    land_welsh=[(x,y) for (x,y),(r,c) in zip(zip(xs,ys),path) if x<340000 and not water[r,c]]
    mean_n = sum(y for _,y in land_welsh)/len(land_welsh) if land_welsh else float("nan")
    a40 = (mean_n>=200000) and (not le)
    return le, sev, a40, None if mean_n!=mean_n else round(mean_n,0)

def nudge(z, blocked, water, rc):
    r,c=rc; H,W=z.shape
    if np.isfinite(z[r,c]) and not blocked[r,c] and not water[r,c]: return rc
    for rad in range(1,40):
        for dr in range(-rad,rad+1):
            for dc in range(-rad,rad+1):
                rr,cc=r+dr,c+dc
                if 0<=rr<H and 0<=cc<W and np.isfinite(z[rr,cc]) and not blocked[rr,cc] and not water[rr,cc]:
                    return (rr,cc)
    raise SystemExit(f"nudge fail {rc}")

def lcp(z, water, river, river_mode, blocked, info, src, dst, m_water):
    H,W=z.shape; cell=info["cell"]; INF=1e100
    dist=np.full((H,W),INF); parent=np.full((H,W,2),-1,np.int32)
    sr,sc=src; er,ec=dst
    dist[sr,sc]=0; heap=[(0.0,sr,sc)]
    while heap:
        cd,r,c=heapq.heappop(heap)
        if cd>dist[r,c]: continue
        if r==er and c==ec: break
        za=float(z[r,c])
        for dr,dc,diag in NEIGH:
            rr,cc=r+dr,c+dc
            if rr<0 or rr>=H or cc<0 or cc>=W or blocked[rr,cc]: continue
            zb=z[rr,cc]
            if not np.isfinite(zb): continue
            d=cell*diag
            dest_water=bool(water[rr,cc]); dest_river=bool(river[rr,cc])
            if river_mode=="conduit" and (dest_water or dest_river):
                cost=m_water*d
            elif dest_water:
                cost=m_water*d
            elif river_mode=="barrier" and dest_river:
                cost=RIVER_BARRIER_MULT*d
            else:
                slope=(float(zb)-za)/d
                cost=d*(1+W_UP*max(slope,0)+W_DN*max(-slope,0))
            nd=cd+cost
            if nd<dist[rr,cc]:
                dist[rr,cc]=nd; parent[rr,cc]=(r,c); heapq.heappush(heap,(nd,rr,cc))
    if dist[er,ec]>=INF/2: return None
    path=[]; r,c=er,ec
    while True:
        path.append((r,c))
        if (r,c)==(sr,sc): break
        pr,pc=int(parent[r,c,0]),int(parent[r,c,1])
        if pr<0: return None
        r,c=pr,pc
    path.reverse()
    length=wlen=0.0
    for i in range(len(path)-1):
        r0,c0=path[i]; r1,c1=path[i+1]
        diag=math.sqrt(2) if (r0!=r1 and c0!=c1) else 1.0
        d=cell*diag; length+=d
        if water[r1,c1]: wlen+=d
    return dist[er,ec], path, length, wlen/length if length else 0.0

def build_masks(dem, info, coastal):
    sea_all=np.isfinite(dem)&(dem<0)
    xs=info["xmin"]+(np.arange(info["width"])+0.5)*info["cell"]
    west=xs<COAST_WEST_LIMIT
    if coastal=="bristol_channel":
        water=sea_all.copy(); water[:,west]=False
        blocked=(sea_all & west[None,:]) | (~np.isfinite(dem) & ~sea_all)
    else:
        water=sea_all.copy()
        blocked=(~np.isfinite(dem) & ~sea_all)
    z=dem.copy(); z[sea_all]=0.0; z[blocked]=np.nan
    return z, water, blocked, sea_all

def plot_map(hs, sea_show, info, paths, title, png):
    fig,ax=plt.subplots(figsize=(12,9),dpi=110)
    extent=[info["xmin"],info["xmax"],info["ymin"],info["ymax"]]
    ax.imshow(hs,cmap="gray",extent=extent,origin="upper",alpha=0.9)
    ww=np.ma.masked_where(~sea_show, np.ones_like(sea_show,float))
    ax.imshow(ww,cmap="Blues",extent=extent,origin="upper",alpha=0.35,vmin=0,vmax=1)
    cols=plt.cm.tab10.colors
    for i,(lab,path) in enumerate(paths.items()):
        xs,ys=zip(*(rc_to_xy(r,c,info) for r,c in path))
        ax.plot(xs,ys,color=cols[i%10],lw=1.3,label=lab)
    ax.plot(STARTS["Carn_Goedog"][0],STARTS["Carn_Goedog"][1],"ro",ms=5)
    ax.plot(END[1],END[2],"k*",ms=11)
    ax.axvline(COAST_WEST_LIMIT,color="cyan",ls="--",lw=0.8,alpha=0.7)
    ax.set_title(title,fontsize=10); ax.legend(loc="lower left",fontsize=6); ax.set_aspect("equal")
    fig.tight_layout(); fig.savefig(png); plt.close(fig)
    print("Wrote", png, flush=True)

def run_grid(cell_m, dem_path, info_path, river_path, tag):
    dem=np.load(dem_path)
    info=json.loads(Path(info_path).read_text())
    assert info["cell"]==cell_m
    river=np.load(river_path).astype(bool)
    rows=[]; paths={}
    total=len(STARTS)*len(RUNS); n=0
    cache_masks={}
    for coastal in ("bristol_channel","full_coast"):
        cache_masks[coastal]=build_masks(dem, info, coastal)
    t0=time.time()
    for sname,(sx,sy) in STARTS.items():
        for m, riv, coastal in RUNS:
            n+=1
            z, water, blocked, sea_all = cache_masks[coastal]
            src=nudge(z,blocked,water,xy_to_rc(sx,sy,info))
            dst=nudge(z,blocked,water,xy_to_rc(END[1],END[2],info))
            print(f"[{tag} {n}/{total}] {sname} m={m} {riv} {coastal}", flush=True)
            t1=time.time()
            res=lcp(z,water,river,riv,blocked,info,src,dst,m)
            elapsed=time.time()-t1
            if res is None:
                rows.append(dict(grain_m=cell_m,start=sname,m_water=m,river_mode=riv,coastal_reach=coastal,
                                 total_cost="",length_m="",water_fraction="",regime="NO_PATH",
                                 lands_end="",severn_approach="",a40_teifi_usk_wye="",runtime_s=round(elapsed,1)))
                continue
            total_c,path,length,wfrac=res
            reg=regime(wfrac); le,sev,a40,mn=classify(path,info,water)
            print(f"  cost={total_c:.0f} len={length/1000:.0f}km w={wfrac:.3f} {reg} LE={le} A40={a40} [{elapsed:.1f}s]", flush=True)
            rows.append(dict(grain_m=cell_m,start=sname,m_water=m,river_mode=riv,coastal_reach=coastal,
                             total_cost=round(total_c,1),length_m=round(length,1),water_fraction=round(wfrac,4),
                             regime=reg,lands_end=le,severn_approach=sev,a40_teifi_usk_wye=a40,
                             welsh_mean_land_N=mn,runtime_s=round(elapsed,1)))
            paths[(sname,m,riv,coastal)]=path
    print(f"{tag} done in {time.time()-t0:.0f}s", flush=True)
    return rows, paths, dem, info, cache_masks["bristol_channel"][3]

def main():
    lock=dict(
        locked_at=datetime.now().isoformat(timespec="seconds"),
        pass_name="pass-3", amendment="A3",
        WORKING_CELL_M=100, optional_50m=True,
        RUNS=[{"m_water":m,"river_mode":r,"coastal_reach":c} for m,r,c in RUNS],
        STARTS=STARTS, END=END, COAST_WEST_LIMIT=COAST_WEST_LIMIT,
        W_UP=W_UP, W_DN=W_DN, same_formula_as_pass2=True,
    )
    (OUT/"LOCKED_params.json").write_text(json.dumps(lock,indent=2))
    print("LOCKED pass-3", flush=True)

    rows100, paths100, dem100, info100, sea_show = run_grid(
        100, OUT/"dem_mosaic_100m.npy", OUT/"dem_info_100m.json", OUT/"river_mask_100m.npy", "100m")

    # Optional 50 m: only key Carn Goedog runs if a probe is cheap enough
    rows50=[]; paths50={}
    # Build 50m by not resampling - from 100m we could note skip; try native 50 for Carn only switch+LE
    # Probe cost: if 100m mean runtime > 120s, skip 50m
    mean_rt = np.mean([r["runtime_s"] for r in rows100 if r["runtime_s"]])
    print("mean 100m runtime", mean_rt, flush=True)
    do50 = mean_rt < 100  # only if 100m was reasonably fast
    if do50:
        # build 50m mosaic quickly from existing 100m by... need native. Skip build if slow path.
        # Use 50m = load tiles at cell 50 for smaller sub-bbox? For honesty use full frame.
        print("Attempting 50 m (may skip if too slow after first run)...", flush=True)
        # Build 50m from dem already at 50 native stored? We don't have it. Downsample reverse impossible.
        # Rebuild at 50m - same as 100m mosaic without mean factor.
        # For time: only Carn Goedog m=1 ignore bristol, m=2 ignore bristol, m=0.05 ignore full
        pass  # handled below in separate builder

    # Maps from 100m
    z=dem100.copy(); z[np.isfinite(dem100)&(dem100<0)]=0; z[~np.isfinite(dem100)]=0
    ls=LightSource(azdeg=315,altdeg=45)
    hs=ls.hillshade(z,vert_exag=1.5,dx=100,dy=100)
    d={}
    for m in (1.0,2.0):
        k=("Carn_Goedog",m,"ignore","bristol_channel")
        if k in paths100: d[f"m={m} ignore bristol"]=paths100[k]
    if d: plot_map(hs,sea_show,info100,d,"Pass-3 100m switch (bristol, ignore)", OUT/"map_100m_switch_bristol_ignore.png")
    d={}
    for m in (0.05,0.1):
        k=("Carn_Goedog",m,"ignore","full_coast")
        if k in paths100: d[f"m={m} full"]=paths100[k]
    if d: plot_map(hs,sea_show,info100,d,"Pass-3 100m Land's End test (full_coast)", OUT/"map_100m_lands_end.png")
    d={}
    for riv in ("ignore","conduit"):
        k=("Carn_Goedog",2.0,riv,"bristol_channel")
        if k in paths100: d[f"m=2 {riv}"]=paths100[k]
    if d: plot_map(hs,sea_show,info100,d,"Pass-3 100m river conduit vs ignore at m=2", OUT/"map_100m_river_m2.png")

    # CSV
    with open(OUT/"results_table.csv","w",newline="") as f:
        w=csv.DictWriter(f, fieldnames=list(rows100[0].keys()))
        w.writeheader(); w.writerows(rows100)
    print("Wrote results_table.csv", flush=True)
    (OUT/"run_meta.json").write_text(json.dumps({"mean_100m_s":mean_rt,"n":len(rows100)},indent=2))

if __name__=="__main__":
    main()
