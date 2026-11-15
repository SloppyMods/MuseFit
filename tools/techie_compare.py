"""Numbers for docs/TECHIE_METHOD.md: what the original creator changed to move Techie (e6164) from the original body to Muse+.
New file for MuseFit. Read-only. Needs numpy only.

    python3 -I -B techie_compare.py <orig.glb> <muse.glb>        (run once for the top pair, once for the dwn pair)

Prints, for one original/remake pair of Penumbra exports:
  1. every mesh of each file: material, vertex and triangle count, node extras (atr_*), bones with weight;
  2. skin: remake skin vs original skin, nearest-vertex distance both ways (mm);
  3. cloth (material containing e6164): per mesh, vertex count change and how far the cloth moved, by height band
     (same index when the counts match, otherwise nearest remake vertex to each original vertex);
  4. cloth weights: how many vertices keep the same bone set, mean weight change, and how close each version's cloth
     weights are to the weights of the skin under it (0 = identical, 1 = no bone in common), for cloth within 12 mm of the skin;
  5. bones the cloth uses in each file that the other does not.
Heights are the glb's y axis (metres); the chest band is y 1.16-1.32. The chest in the .glb is at +z (front).
"""
import os
import sys

import numpy as np

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import glb_raw  # noqa: E402
import glb_summary as G  # noqa: E402

CLOSE = 0.012  # cloth within 12 mm of the skin counts as "close" for the weight-copy test
BANDS = [(0.0, 0.5, "legs/hips below 0.5"), (0.5, 1.0, "0.5-1.0"), (1.0, 1.16, "1.00-1.16 waist/belly"), (1.16, 1.32, "1.16-1.32 chest"), (1.32, 9.0, "above 1.32 neck/shoulder")]


def nearest(a, b, chunk=1500):
    """(distance, index into b) of the nearest point of b to every point of a."""
    dist, idx = np.empty(len(a)), np.empty(len(a), "i8")
    b2 = (b * b).sum(1)
    for i in range(0, len(a), chunk):
        c = a[i:i + chunk]
        d2 = (c * c).sum(1)[:, None] - 2 * c @ b.T + b2[None, :]
        idx[i:i + chunk] = d2.argmin(1)
        dist[i:i + chunk] = np.sqrt(np.maximum(d2.min(1), 0))
    return dist, idx


def stats(d):
    mm = np.asarray(d) * 1000
    return f"median {np.median(mm):.2f} p95 {np.percentile(mm, 95):.2f} max {mm.max():.2f} mm"


def weight_dict(prim, i):
    out = {}
    for j, w in zip(prim["joints"][i], prim["weights"][i]):
        if w > 1e-6:
            out[prim["joint_names"][j]] = out.get(prim["joint_names"][j], 0) + float(w)
    return out


def weight_gap(wa, wb):
    """0 when both vertices use the same bones in the same amounts, 1 when they share none (half the L1 distance)."""
    return 0.5 * sum(abs(wa.get(k, 0) - wb.get(k, 0)) for k in set(wa) | set(wb))


def bones_of(prims):
    used = set()
    for p in prims:
        used |= {p["joint_names"][j] for j in set(p["joints"][p["weights"] > 0].ravel().tolist())}
    return used


def concat(prims):
    return {"positions": np.concatenate([p["positions"] for p in prims]),
            "joints": np.concatenate([p["joints"] for p in prims]), "weights": np.concatenate([p["weights"] for p in prims]),
            "joint_names": prims[0]["joint_names"]}


def listing(label, prims):
    print(f"\n-- {label}")
    for p in prims:
        print(f"  {p['name']}: {p['material']}, {len(p['positions'])} vertices, {len(p['triangles'])} triangles, extras {p['extras'] or 'none'}, "
              f"{len(bones_of([p]))} bones with weight")
    print(f"  bones with weight in the whole file: {len(bones_of(prims))}")


def close_weight_gap(cloth, skin):
    """Weight gap between each close cloth vertex and its nearest skin vertex."""
    dist, idx = nearest(cloth["positions"], skin["positions"])
    keep = np.where(dist < CLOSE)[0]
    gaps = np.array([weight_gap(weight_dict(cloth, i), weight_dict(skin, idx[i])) for i in keep])
    return len(keep), gaps


def uv_and_colour(orig_path, muse_path):
    """UV0 and vertex colour of cloth meshes with the same vertex count in both files, compared by index."""
    print("\n== cloth UVs and vertex colours, same-count meshes, same index")
    docs = [glb_raw.load(orig_path), glb_raw.load(muse_path)]
    recs = [{r["name"]: r for r in glb_raw.primitives(d) if "e6164" in r["material"]} for d, _ in docs]
    for name in sorted(recs[0]):
        if name not in recs[1]:
            continue
        a, b = [glb_raw.read_accessor(d, bl, r[name]["attributes"]["TEXCOORD_0"]).astype("f8") for (d, bl), r in zip(docs, recs)]
        if len(a) != len(b):
            print(f"{name}: vertex count differs ({len(a)} vs {len(b)}), not compared")
            continue
        ca, cb = [glb_raw.read_accessor(d, bl, r[name]["attributes"]["_FFXIV_COLOR"]).astype("f8") for (d, bl), r in zip(docs, recs)]
        print(f"{name}: UV0 max diff {np.abs(a - b).max():.2e}; vertex colour differs on {int((np.abs(ca - cb).max(1) > 1e-6).sum())}/{len(a)} vertices")


def main(orig_path, muse_path):
    orig, muse = G.read_primitives(orig_path), G.read_primitives(muse_path)
    listing(f"original: {os.path.basename(orig_path)}", orig)
    listing(f"Muse remake: {os.path.basename(muse_path)}", muse)
    skin = lambda ps: [p for p in ps if "b0001_bibo" in p["material"]]
    cloth = lambda ps: [p for p in ps if "e6164" in p["material"]]
    so, sm = concat(skin(orig)), concat(skin(muse))
    print("\n== skin: original skin vs remake skin (bibo meshes)")
    print(f"  vertices {len(so['positions'])} -> {len(sm['positions'])}")
    print(f"  original->remake {stats(nearest(so['positions'], sm['positions'])[0])}")
    print(f"  remake->original {stats(nearest(sm['positions'], so['positions'])[0])}")
    print(f"  bones with weight: original {len(bones_of(skin(orig)))}, remake {len(bones_of(skin(muse)))}")
    print(f"  skin bones only in the original: {sorted(bones_of(skin(orig)) - bones_of(skin(muse)))}")
    print(f"  skin bones only in the remake: {sorted(bones_of(skin(muse)) - bones_of(skin(orig)))}")
    print("\n== cloth movement, original -> remake (positions in metres, heights are y)")
    co, cm = {p["name"]: p for p in cloth(orig)}, {p["name"]: p for p in cloth(muse)}
    for name in sorted(co):
        a, b = co[name], cm.get(name)
        if b is None:
            print(f"{name}: not in the remake")
            continue
        pa, pb = a["positions"], b["positions"]
        if len(pa) == len(pb):
            move = pb - pa
            how = "same index"
        else:
            dist, idx = nearest(pa, pb)
            move = pb[idx] - pa
            how = "nearest remake vertex"
        d = np.linalg.norm(move, axis=1)
        print(f"{name} ({how}): {len(pa)} -> {len(pb)} vertices; moved {stats(d)}; front/back (z) median {np.median(move[:, 2]) * 1000:.2f} mm, "
              f"p5 {np.percentile(move[:, 2], 5) * 1000:.2f}, p95 {np.percentile(move[:, 2], 95) * 1000:.2f}; z max {pa[:, 2].max():.3f} -> {pb[:, 2].max():.3f}")
        for lo, hi, label in BANDS:
            m = (pa[:, 1] >= lo) & (pa[:, 1] < hi)
            if m.sum() > 20:
                print(f"    band {label}: {int(m.sum())} vertices, moved median {np.median(d[m]) * 1000:.2f} p95 {np.percentile(d[m], 95) * 1000:.2f} mm, z median {np.median(move[m][:, 2]) * 1000:.2f} mm")
        if len(pa) == len(pb):
            same = diff = 0
            gaps = []
            for i in range(len(pa)):
                wa, wb = weight_dict(a, i), weight_dict(b, i)
                same += set(wa) == set(wb)
                gaps.append(weight_gap(wa, wb))
            print(f"    weights, same index: same bone set on {same}/{len(pa)} vertices; weight gap mean {np.mean(gaps):.4f}, p95 {np.percentile(gaps, 95):.4f}, max {np.max(gaps):.4f}")
        else:
            gaps = np.array([weight_gap(weight_dict(a, i), weight_dict(b, j)) for i, j in enumerate(idx)])
            print(f"    weights, nearest remake vertex: weight gap mean {gaps.mean():.4f}, p95 {np.percentile(gaps, 95):.4f}, max {gaps.max():.4f}")
    print("\n== cloth weights against the skin under the cloth (cloth within 12 mm of its own file's skin)")
    for label, prims, sk in (("original", cloth(orig), so), ("remake", cloth(muse), sm)):
        n, gaps = close_weight_gap(concat(prims), sk)
        print(f"  {label}: {n} close cloth vertices; weight gap to the skin mean {gaps.mean():.4f}, p95 {np.percentile(gaps, 95):.4f}, "
              f"identical (<0.01) on {int((gaps < 0.01).sum())}")
    uv_and_colour(orig_path, muse_path)
    bo, bm = bones_of(cloth(orig)), bones_of(cloth(muse))
    print("\n== bones used by the cloth")
    print(f"  original {len(bo)}, remake {len(bm)}; only in the original: {sorted(bo - bm)}; only in the remake: {sorted(bm - bo)}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(*sys.argv[1:])
