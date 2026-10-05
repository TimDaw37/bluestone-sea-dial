#!/usr/bin/env python3
"""Add the closed-sea overlays (A5 coast rules) to docs/data/lattice.json as 1 km run-length masks."""
import json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
from prep import surface, closed_sea

P = Path(__file__).resolve().parent.parent / "docs" / "data" / "lattice.json"
d = json.loads(P.read_text())
s = surface(200, "a4")
masks = {}
for k, rule in {"sight": "in_sight", "near": "within_2"}.items():
    cs = closed_sea(rule, s.z, s.sea, 200)
    H, W = cs.shape[0] // 5, cs.shape[1] // 5
    m = cs[:H * 5, :W * 5].reshape(H, 5, W, 5).mean(axis=(1, 3)) >= 0.5
    runs = []
    for r in range(H):
        row = m[r]; c = 0
        while c < W:
            if row[c]:
                a = c
                while c < W and row[c]:
                    c += 1
                runs += [r, a, c - a]
            else:
                c += 1
    masks[k] = dict(W=W, H=H, cell=1000, runs=runs)
d["masks"] = masks
P.write_text(json.dumps(d, separators=(",", ":")))
print({k: len(v["runs"]) // 3 for k, v in masks.items()}, P.stat().st_size)
