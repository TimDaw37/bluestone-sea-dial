#!/usr/bin/env python3
"""
Bluestone sea-vs-land dial — shared least-cost engine (amendment A4).

The cost rule in its default form (`transfer=0, gmax=None, nbr=8`) reproduces the
locked passes 1–3 exactly:

    land -> land   d + W_UP * rise + W_DN * fall      (rise/fall in metres)
    any  -> water  m_water * d
    water -> land  d + W_UP * rise + W_DN * fall      (from z = 0)

A4 adds, as separate dials (all off by default):
    transfer   fixed cost (metres of flat-ground equivalent) added at every
               land->water and water->land step (embark / land the stone)
    gmax       steepest overland gradient allowed (e.g. 0.15); steeper steps
               impassable
    nbr        8 or 16 neighbours (16 reduces the octilinear distance bias
               from <= 8.2 % to <= 2.7 %)

Also used to build the web model's data (see build_web_data.py). The web page
(docs/index.html) implements the same rule in JavaScript.
"""
from __future__ import annotations

import math
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra

STARTS = {
    "Carn_Goedog": (212878.0, 233160.0),
    "Craig_Rhos_y_felin": (211650.0, 236140.0),
}
END = ("Stonehenge", 412250.0, 142200.0)
W_UP, W_DN = 4.0, 2.6
SEA_FRAC_THRESH, INLAND_FRAC_THRESH = 0.25, 0.10
RIVER_BARRIER_MULT = 100.0
COAST_WEST_LIMIT = 200000

N8 = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]
N16 = N8 + [(-2, -1), (-2, 1), (2, -1), (2, 1), (-1, -2), (1, -2), (-1, 2), (1, 2)]


def xy_to_rc(x, y, info):
    return int((info["ymax"] - y) // info["cell"]), int((x - info["xmin"]) // info["cell"])


def rc_to_xy(r, c, info):
    return info["xmin"] + (c + 0.5) * info["cell"], info["ymax"] - (r + 0.5) * info["cell"]


def regime_label(wf):
    if wf >= SEA_FRAC_THRESH:
        return "sea-preferring"
    if wf <= INLAND_FRAC_THRESH:
        return "inland-preferring"
    return "mixed/unresolved"


class Surface:
    """Static grid: elevation, sea, river, west-sea, impassable."""

    def __init__(self, z, sea, river, info, west_sea=None):
        self.z = z.astype(np.float64)          # NaN = impassable land gap
        self.sea = sea.astype(bool)
        self.river = river.astype(bool)
        self.info = info
        self.H, self.W = z.shape
        if west_sea is None:
            xs = info["xmin"] + (np.arange(self.W) + 0.5) * info["cell"]
            west_sea = self.sea & (xs < COAST_WEST_LIMIT)[None, :]
        self.west_sea = west_sea
        self._edges = {}

    def _edge_arrays(self, nbr):
        """Precompute (src, dst, d, dz, flags) for all valid neighbour pairs."""
        if nbr in self._edges:
            return self._edges[nbr]
        H, W, cell = self.H, self.W, self.info["cell"]
        idx = np.arange(H * W).reshape(H, W)
        z = np.where(self.sea, 0.0, self.z)
        ok = np.isfinite(z)
        out = []
        for dr, dc in (N8 if nbr == 8 else N16):
            r0, r1 = max(0, -dr), H - max(0, dr)
            c0, c1 = max(0, -dc), W - max(0, dc)
            a = (slice(r0, r1), slice(c0, c1))
            b = (slice(r0 + dr, r1 + dr), slice(c0 + dc, c1 + dc))
            valid = ok[a] & ok[b]
            if abs(dr) + abs(dc) == 3:  # knight move: both straddled cells passable
                sr, sc = (dr // 2, 0) if abs(dr) == 2 else (0, dc // 2)
                m1 = (slice(r0 + sr, r1 + sr), slice(c0 + sc, c1 + sc))
                m2 = (slice(r0 + dr - sr, r1 + dr - sr), slice(c0 + dc - sc, c1 + dc - sc))
                valid &= ok[m1] & ok[m2]
            d = cell * math.hypot(dr, dc)
            out.append((idx[a][valid].astype(np.int32), idx[b][valid].astype(np.int32),
                        np.full(valid.sum(), d, dtype=np.float32),
                        (z[b] - z[a])[valid].astype(np.float32)))
        src = np.concatenate([o[0] for o in out])
        dst = np.concatenate([o[1] for o in out])
        d = np.concatenate([o[2] for o in out])
        dz = np.concatenate([o[3] for o in out])
        self._edges[nbr] = (src, dst, d, dz)
        return self._edges[nbr]

    def weights(self, m_water, river_mode="ignore", coastal="bristol_channel",
                transfer=0.0, gmax=None, nbr=8, w_up=W_UP, w_dn=W_DN, closed_sea=None):
        src, dst, d, dz = self._edge_arrays(nbr)
        sea = self.sea.ravel()
        if coastal == "bristol_channel":
            sea = sea & ~self.west_sea.ravel()
            dead = self.west_sea.ravel()
        else:
            dead = np.zeros_like(sea)
        if closed_sea is not None:  # A5: sea cells shut by the coast rule
            cs = closed_sea.ravel() & self.sea.ravel()
            sea = sea & ~cs
            dead = dead | cs
        riv = self.river.ravel() & ~self.sea.ravel()
        water = sea | riv if river_mode == "conduit" else sea
        wa, wb = water[src], water[dst]
        land_cost = d + w_up * np.maximum(dz, 0) + w_dn * np.maximum(-dz, 0)
        cost = np.where(wb, m_water * d, land_cost)
        if river_mode == "barrier":
            cost = np.where(riv[dst], RIVER_BARRIER_MULT * d, cost)
        if transfer:
            cost = cost + transfer * (wa != wb)
        keep = ~(dead[src] | dead[dst])
        if gmax is not None:
            steep = (~wa & ~wb) & (np.abs(dz) / d > gmax)
            keep &= ~steep
        return src[keep], dst[keep], cost[keep], water

    def run(self, start_xy, m_water, **kw):
        H, W = self.H, self.W
        src, dst, cost, water = self.weights(m_water, **kw)
        g = csr_matrix((cost, (src, dst)), shape=(H * W, H * W))
        s = self._land_cell(*xy_to_rc(*start_xy, self.info))
        e = self._land_cell(*xy_to_rc(END[1], END[2], self.info))
        dist, pred = dijkstra(g, directed=True, indices=s, return_predecessors=True)
        if not np.isfinite(dist[e]):
            return None
        path = [e]
        while path[-1] != s:
            path.append(pred[path[-1]])
        path = path[::-1]
        rc = np.array(np.unravel_index(path, (H, W))).T
        cell = self.info["cell"]
        steps = np.hypot(np.diff(rc[:, 0]), np.diff(rc[:, 1])) * cell
        wsteps = water[np.array(path[1:])]
        length = steps.sum()
        wf = steps[wsteps].sum() / length
        transfers = int(np.sum(water[np.array(path[1:])] != water[np.array(path[:-1])]))
        zz = np.where(self.sea, 0.0, self.z).ravel()[np.array(path)]
        dzs = np.diff(zz)
        landstep = ~wsteps
        climb = float(np.maximum(dzs, 0)[landstep].sum())
        fall = float(np.maximum(-dzs, 0)[landstep].sum())
        tr_idx = np.nonzero(water[np.array(path[1:])] != water[np.array(path[:-1])])[0]
        tr_xy = [rc_to_xy(*rc[i + 1], self.info) for i in tr_idx]
        return dict(cost=float(dist[e]), length_m=float(length), water_fraction=float(wf),
                    regime=regime_label(wf), transfers=transfers, path_rc=rc,
                    climb_m=climb, descent_m=fall, transfer_xy=tr_xy,
                    land_m=float(steps[~wsteps].sum()), water_m=float(steps[wsteps].sum()))

    def _land_cell(self, r, c):
        z = self.z
        if np.isfinite(z[r, c]) and not self.sea[r, c]:
            return r * self.W + c
        for rad in range(1, 30):
            for dr in range(-rad, rad + 1):
                for dc in range(-rad, rad + 1):
                    rr, cc = r + dr, c + dc
                    if 0 <= rr < self.H and 0 <= cc < self.W and np.isfinite(z[rr, cc]) and not self.sea[rr, cc]:
                        return rr * self.W + cc
        raise ValueError("no land near endpoint")
