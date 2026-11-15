# MuseFit copy of builds/_dionys/e6116ts/meas/wjump_all.py (XIVAutoFit). Changes: sys.path points at this tools/ folder; file renamed wjump.py
"""Bone-weight jump per cm along cloth edges (L1 over bones, 0..2) per body region. python3 wjump_all.py <glb>..."""
import sys
import os
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, glb_raw as g
REG = {"chest": lambda c: (np.abs(c[:,0])<0.12)&(c[:,1]>1.15)&(c[:,1]<1.36)&(c[:,2]>0),
       "armpit": lambda c: (np.abs(c[:,0])>0.08)&(np.abs(c[:,0])<0.2)&(c[:,1]>1.18)&(c[:,1]<1.35),
       "back": lambda c: (np.abs(c[:,0])<0.12)&(c[:,1]>1.1)&(c[:,1]<1.4)&(c[:,2]<0),
       "waist": lambda c: (c[:,1]>0.95)&(c[:,1]<1.12),
       "arm": lambda c: np.abs(c[:,0])>0.2}
for f in sys.argv[1:]:
    doc, blob = g.load(f); names = doc["skins"][0]["joints"]; B = len(names)
    for p in g.primitives(doc):
        if "b0001" in p["material"]: continue
        P = g.read_accessor(doc, blob, p["attributes"]["POSITION"]).astype(float)
        T = g.read_accessor(doc, blob, p["indices"]).astype(int).reshape(-1, 3)
        W = np.zeros((len(P), B))
        for s in ("0", "1"):
            if "JOINTS_" + s not in p["attributes"]: continue
            J = g.read_accessor(doc, blob, p["attributes"]["JOINTS_" + s]).astype(int); Wt = g.read_accessor(doc, blob, p["attributes"]["WEIGHTS_" + s]).astype(float)
            for k in range(J.shape[1]): np.add.at(W, (np.arange(len(P)), J[:, k]), Wt[:, k])
        W /= np.maximum(W.sum(1, keepdims=True), 1e-9)
        E = np.unique(np.sort(np.vstack([T[:, [0, 1]], T[:, [1, 2]], T[:, [2, 0]]]), 1), axis=0)
        c = (P[E[:, 0]] + P[E[:, 1]]) / 2; L = np.linalg.norm(P[E[:, 0]] - P[E[:, 1]], axis=1) * 100
        j = np.abs(W[E[:, 0]] - W[E[:, 1]]).sum(1) / np.maximum(L, 0.3)
        out = []
        for r, fn in REG.items():
            m = fn(c)
            if m.sum(): out.append(f"{r} mean {j[m].mean():.3f} p95 {np.percentile(j[m],95):.3f} >0.5/cm {(j[m]>0.5).sum()}")
        print(f"{f.split('/')[-1]:22s} {p['name']}: " + " | ".join(out))
