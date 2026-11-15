# New file for MuseFit (job 009, checked and re-run in job 010).
"""Measure how the creator's Techie Muse remake differs from the original Techie and from the Muse body .mdl files.

Read-only. Needs numpy. Pass the paths on the command line (see docs/MUSE_BODY_STUDY.md for the exact call):
  python3 -I compare_study.py <top_orig.glb> <top_muse.glb> <miette-options-dir> <body-mdl> [<body-mdl> ...] --port <port.mdl> [<port.mdl> ...]
  python3 -I compare_study.py --cloth <orig.glb> <muse.glb>      (only the cloth part, fast)
Slow (a few minutes) in full mode: it measures every vertex against every vertex in chunks.
"""
import os
import sys

import numpy as np

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import glb_summary as G  # noqa: E402
import mdl_read as R  # noqa: E402


def nearest(a: np.ndarray, b: np.ndarray, chunk: int = 1500) -> np.ndarray:
    """Distance from every point of a to its nearest point of b (brute force, chunked; fine for 10k x 10k)."""
    out = np.empty(len(a))
    b2 = (b * b).sum(1)
    for i in range(0, len(a), chunk):
        c = a[i:i + chunk]
        d2 = (c * c).sum(1)[:, None] - 2 * c @ b.T + b2[None, :]
        out[i:i + chunk] = np.sqrt(np.maximum(d2.min(1), 0))
    return out


def stats(d: np.ndarray) -> str:
    mm = d * 1000
    return f"median {np.median(mm):.2f} mm, p95 {np.percentile(mm, 95):.2f} mm, max {mm.max():.2f} mm"


def glb_points(path: str, material_part: str, skin: bool) -> np.ndarray:
    prims = [p for p in G.read_primitives(path) if (material_part in p["material"]) == skin]
    return np.concatenate([p["positions"] for p in prims])


def mdl_points(path: str, material_part: str = "bibo") -> np.ndarray:
    m = R.read_mdl(path)
    return np.concatenate([x.positions for x in m.meshes if material_part in x.material])


def cloth_report(orig: str, muse: str) -> None:
    """Cloth meshes (the outfit's own material, e6164) of the original vs the remake, matched by mesh name."""
    print("\n== cloth: original vs remake (outfit material)")
    co = {p["name"]: p for p in G.read_primitives(orig) if "e6164" in p["material"]}
    cm = {p["name"]: p for p in G.read_primitives(muse) if "e6164" in p["material"]}
    for name in sorted(co):
        a, b = co[name], cm.get(name)
        if b is None:
            print(f"{name}: not in the remake")
            continue
        if len(a["positions"]) == len(b["positions"]):
            d = np.linalg.norm(a["positions"] - b["positions"], axis=1)
            print(f"{name}: same vertex count {len(a['positions'])}; same-index move {stats(d)}")
            dz = (b["positions"] - a["positions"])[:, 2] * 1000
            print(f"    z (front-back) change: median {np.median(dz):.2f} mm, p5 {np.percentile(dz, 5):.2f}, p95 {np.percentile(dz, 95):.2f}; "
                  f"z max {a['positions'][:, 2].max():.3f} -> {b['positions'][:, 2].max():.3f}")
        else:
            print(f"{name}: vertex count {len(a['positions'])} -> {len(b['positions'])}; nearest-point move orig->remake "
                  f"{stats(nearest(a['positions'], b['positions']))}; z max {a['positions'][:, 2].max():.3f} -> {b['positions'][:, 2].max():.3f}")


def main(argv):
    if argv[:1] == ["--cloth"] and len(argv) == 3:
        cloth_report(argv[1], argv[2])
        return
    if "--port" not in argv:
        sys.exit(__doc__)
    split = argv.index("--port")
    orig, muse, options = argv[0], argv[1], argv[2]
    bodies, ports = argv[3:split], argv[split + 1:]
    remake_skin = glb_points(muse, "b0001_bibo", True)
    print(f"remake skin (bibo-material meshes of {os.path.basename(muse)}): {len(remake_skin)} vertices")
    print("\n== remake skin vs Muse body .mdl skin (bibo material); remake->body then body->remake")
    for b in bodies:
        pts = mdl_points(b)
        print(f"{b}\n    {len(pts)} verts | remake->body {stats(nearest(remake_skin, pts))} | body->remake {stats(nearest(pts, remake_skin))}")
    print("\n== remake vs the installed port .mdl files (all vertices)")
    muse_all = np.concatenate([p["positions"] for p in G.read_primitives(muse)])
    for p in ports:
        pts = np.concatenate([x.positions for x in R.read_mdl(p).meshes])
        print(f"{p}\n    {len(pts)} verts | remake->mdl {stats(nearest(muse_all, pts))} | mdl->remake {stats(nearest(pts, muse_all))}")
    print("\n== original export vs each Miette top option .mdl (all vertices)")
    orig_all = np.concatenate([p["positions"] for p in G.read_primitives(orig)])
    for d in sorted(os.listdir(options)):
        f = os.path.join(options, d, "chara/equipment/e6164/model/c0201e6164_top.mdl")
        if os.path.exists(f):
            pts = np.concatenate([x.positions for x in R.read_mdl(f).meshes])
            print(f"{d}: {len(pts)} verts | export->mdl {stats(nearest(orig_all, pts))} | mdl->export {stats(nearest(pts, orig_all))}")
    cloth_report(orig, muse)


if __name__ == "__main__":
    main(sys.argv[1:])
