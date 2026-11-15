# New file for MuseFit (Track Suit v2 fix, 2026-11-14).
"""Push cloth that sits inside (or too close to) the Muse skin out to a clearance, with a smooth falloff. Raw .glb, no Blender.

    python3 -I -B clip_push.py <in.glb> <out.glb> [clearance_mm=3] [falloff_sigma_mm=8] [poses=stand,arms_up]

For every cloth vertex within 5 cm of the skin, the signed distance to the skin is measured at rest and in the listed simulated
poses (tools/poses.json). A vertex's deficit is clearance minus its lowest distance, counted only where the skin it is measured
against carries the same bones as the cloth vertex (weight difference under 0.15). Where the hit skin has other bones (an arm
sleeve closing onto the chest in a pose) the vertex is left alone: a push at rest along the arm would move it toward the chest.
Each deficit (capped at 12 mm) is spread over all cloth meshes by a Gaussian (cut off at 3 sigma) of the distance between
the vertices' closest skin points ("foot points"), the largest contribution wins, and every vertex moves along the skin
normal at its foot point. So inner and outer cloth layers over one skin spot get the same lift and keep their order, and
vertices at the same position move identically. Cloth more than 15 mm from the skin gets less, none from 30 mm (far cloth such
as a hood has foot points that jump between neighbours, which would make steps). Up to 3 passes, re-measuring each time.
Env CLIP_SKELETONS=<a.sklb,b.sklb>: the deficits are also measured with the mesh carried onto each listed skeleton's rest
pose (as posed_clip.py --skeleton does), e.g. the c0801 skeleton a Miqo'te wearing c0201 gear uses; the lift is still applied
in the .glb's own rest pose. Only POSITION of changed cloth primitives is rewritten (new accessor with fresh min/max); NORMAL and everything else stay.
"""
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np  # noqa: E402

import glb_raw as g  # noqa: E402
import muse_geom as mg  # noqa: E402

NEAR_M, SAME_BONES, CAP_M, PASSES = 0.05, 0.15, 0.012, 3
NEAR_FULL_M, FAR_M = 0.015, 0.030  # full lift for cloth up to 15 mm from the skin, none from 30 mm


def deficits(P: np.ndarray, cloth: dict, skin: dict, mats: list[np.ndarray], clear: float) -> tuple[np.ndarray, int]:
    """Per cloth vertex: metres it must move out (0 if fine), and how many different-bone contacts were skipped."""
    need = np.zeros(len(P))
    skipped = np.zeros(len(P), bool)
    for M in mats:
        sp, cp = mg.posed(skin["P"], skin["W"], M), mg.posed(P, cloth["W"], M)
        s, tri, bary, _ = mg.Surface(sp, skin["T"]).signed(cp)
        near = np.linalg.norm(cp - sp[mg.knn(cp, sp, 1)[:, 0]], axis=1) < NEAR_M
        hit_w = (skin["W"][skin["T"][tri]] * bary[..., None]).sum(1)
        same = np.abs(hit_w - cloth["W"]).sum(1) / 2 < SAME_BONES
        low = near & (s < clear)
        need = np.where(low & same, np.maximum(need, clear - s), need)
        skipped |= low & ~same & (s < 0)
    return np.minimum(need, CAP_M), int((skipped & (need == 0)).sum())


def spread(P: np.ndarray, need: np.ndarray, sigma: float) -> np.ndarray:
    seeds = np.flatnonzero(need > 0)
    lift = np.zeros(len(P))
    for j in seeds:
        d2 = ((P - P[j]) ** 2).sum(1)
        lift = np.maximum(lift, np.where(d2 < (3 * sigma) ** 2, need[j] * np.exp(-d2 / (2 * sigma ** 2)), 0))
    return lift


def main(src: str, out: str, clear_mm: float, sigma_mm: float, pose_names: list[str]) -> None:
    if os.path.exists(out):
        sys.exit(f"refusing to overwrite {out}")
    doc, blob, skin, cloth = mg.load(src)
    names, rest = g.joint_matrices(doc, blob)
    parents = g.joint_parents(doc)
    specs = list(mg.poses(pose_names).values())
    if "stand" not in pose_names:
        specs.insert(0, [])
    mats = [mg.pose_matrices(names, parents, rest, spec) for spec in specs]
    # CLIP_SKELETONS=a.sklb,b.sklb: also measure on those skeletons' rest poses (mesh carried there bone by bone first)
    for sklb in filter(None, os.environ.get("CLIP_SKELETONS", "").split(",")):
        import posed_clip
        target = posed_clip.skeleton_rest(sklb, names, rest)
        base = target @ np.linalg.inv(rest)
        mats += [mg.pose_matrices(names, parents, target, spec) @ base for spec in specs]
        print(f"also measured on the rest pose of {os.path.basename(sklb)}")
    clear, sigma = clear_mm / 1000, sigma_mm / 1000
    surface = mg.Surface(skin["P"], skin["T"])
    P = cloth["P"].copy()
    _, inv = np.unique(np.round(cloth["P"], 5), axis=0, return_inverse=True)
    inv = inv.ravel()
    for n in range(PASSES):
        need, skipped = deficits(P, cloth, skin, mats, clear)
        if not need.any():
            print(f"pass {n + 1}: nothing under {clear_mm} mm (skipped different-bone contacts: {skipped})")
            break
        dist, tri, bary, normal = surface.signed(P)
        foot = (skin["P"][skin["T"][tri]] * bary[..., None]).sum(1)
        lift = spread(foot, need, sigma)  # measured between skin foot points: stacked layers over one spot get one lift
        # only cloth near the skin moves: far cloth (the hood, 6 cm out) has jumpy foot points and never needs a lift
        lift *= np.clip((FAR_M - np.abs(dist)) / (FAR_M - NEAR_FULL_M), 0, 1)
        group = np.zeros(inv.max() + 1)
        np.maximum.at(group, inv, lift)
        lift = group[inv]  # same position, same lift
        P = P + lift[:, None] * normal
        print(f"pass {n + 1}: {int((need > 0).sum())} vertices under {clear_mm} mm (deepest {(clear - need.max()) * 1000:.1f} mm); "
              f"{int((lift > 1e-5).sum())} moved, max {lift.max() * 1000:.1f} mm; skipped different-bone contacts: {skipped}")
    moved = np.linalg.norm(P - cloth["P"], axis=1)
    writer = g.GlbWriter(doc, blob)
    for k, prim in enumerate(cloth["prims"]):
        own = cloth["owner"] == k
        if moved[own].max() < 1e-7:
            continue
        target = writer.doc["meshes"][prim["mesh"]]["primitives"][prim["prim"]]["attributes"]
        target["POSITION"] = writer.add_accessor(P[own].astype("<f4"), 5126, "VEC3")
        print(f"{prim['name']}: {int((moved[own] > 1e-5).sum())} vertices moved, max {moved[own].max() * 1000:.1f} mm")
    writer.save(out)


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) < 2:
        sys.exit(__doc__)
    main(a[0], a[1], float(a[2]) if len(a) > 2 else 3.0, float(a[3]) if len(a) > 3 else 8.0,
         (a[4] if len(a) > 4 else "stand,arms_up").split(","))
