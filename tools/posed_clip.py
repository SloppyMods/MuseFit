# New file for MuseFit (Track Suit v2 fix, 2026-11-14).
"""Count cloth vertices inside the Muse skin, at rest and in simulated poses. Read-only. Plain numpy, no Blender.

    python3 -I -B posed_clip.py <build.glb> [--poses stand,arms_up,...] [--save <out.npz>] [--skeleton <file.sklb>]

Both skin and cloth are posed with their own weights (linear blend skinning, the pose table tools/poses.json, the same bone
turns render_poses.py uses). For every cloth vertex within 5 cm of the skin it measures the exact signed distance to the
posed skin surface (negative = inside). Per pose it prints, per cloth mesh, the vertices more than 1 mm inside, the deepest,
and where they sit (region at rest). --save writes, per cloth vertex (merged cloth order), the lowest signed distance over
all poses and the pose it happened in, for clip_push.py. Poses are bone turns, not game animation.
--skeleton (default: the c0801 Miqo'te NFLB+YAS skeleton, the primary check; 'none' = the .glb's c0201 rest): first move skin and cloth from the .glb's rest pose onto the .sklb's rest pose (each vertex by its own bones,
which is how the game fits c0201 gear to another race's skeleton, approximately), then pose about the new bone positions.
"""
import argparse
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np  # noqa: E402

import glb_raw as g  # noqa: E402
import muse_geom as mg  # noqa: E402

DEFAULT_POSES = "stand,arms_up,arms_forward,bend,twist,walk"
# SloppyMods's character is always a Miqo'te female: the c0801 skeleton's rest pose is the primary check (2026-11-14)
DEFAULT_SKELETON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "builds", "skeleton", "nofflebones_yas.sklb")
NEAR_M, INSIDE_MM = 0.05, -1.0


def skeleton_rest(sklb: str, names: list[str], rest: np.ndarray) -> np.ndarray:
    """World rest matrices of the .glb's bones taken from an .sklb (the skeleton whose bone count matches)."""
    import sklb_study as ss
    found = ss.skeletons(sklb)
    skel = next((s for s in found if len(s["bones"]) == len(names)), None)
    if skel is None:
        sys.exit(f"no skeleton with {len(names)} bones in {sklb}")
    W = ss.world(skel)
    index = {b["name"]: i for i, b in enumerate(skel["bones"])}
    return np.stack([W[index[n]] if n in index else rest[i] for i, n in enumerate(names)])


def measure(path: str, wanted: list[str], sklb: str | None = None) -> tuple[dict, np.ndarray, dict]:
    doc, blob, skin, cloth = mg.load(path)
    names, rest = g.joint_matrices(doc, blob)
    parents = g.joint_parents(doc)
    where = mg.region(cloth["P"])
    # with --skeleton: carry the mesh from the .glb rest pose onto that skeleton's rest pose first (per bone, as skinning does)
    target = skeleton_rest(sklb, names, rest) if sklb else rest
    base = target @ np.linalg.inv(rest)
    signed = {}
    for pose, spec in mg.poses(wanted).items():
        M = mg.pose_matrices(names, parents, target, spec) @ base
        sp, cp = mg.posed(skin["P"], skin["W"], M), mg.posed(cloth["P"], cloth["W"], M)
        s, _, _, _ = mg.Surface(sp, skin["T"]).signed(cp)
        dist = np.linalg.norm(cp - sp[mg.knn(cp, sp, 1)[:, 0]], axis=1)
        signed[pose] = np.where(dist < NEAR_M, s * 1000, np.inf)  # mm; far cloth (hood, loose parts) is not measured
    return signed, where, cloth


def report(path: str, signed: dict, where: np.ndarray, cloth: dict) -> None:
    print(f"{os.path.basename(path)}: cloth vertices more than 1 mm inside the skin (deepest mm) [where at rest]")
    for pose, s in signed.items():
        parts = []
        for k, prim in enumerate(cloth["prims"]):
            own = cloth["owner"] == k
            bad = own & (s < INSIDE_MM)
            spots = ", ".join(f"{r} {int((where[bad] == r).sum())}" for r in np.unique(where[bad]))
            deepest = s[own].min() if np.isfinite(s[own]).any() else float("nan")
            parts.append(f"{prim['name']} {int(bad.sum())} ({deepest:.1f}) [{spots}]")
        total = int((s < INSIDE_MM).sum())
        print(f"  {pose:13s} total {total:4d} | " + " | ".join(parts))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("build")
    ap.add_argument("--poses", default=DEFAULT_POSES)
    ap.add_argument("--save")
    ap.add_argument("--skeleton", default=DEFAULT_SKELETON,
                    help=".sklb whose rest pose replaces the .glb's; default the Miqo'te c0801 NFLB+YAS skeleton "
                         "(builds/skeleton/nofflebones_yas.sklb); 'none' = the .glb's own c0201 rest pose")
    a = ap.parse_args()
    if a.save and os.path.exists(a.save):
        sys.exit(f"refusing to overwrite {a.save}")
    wanted = a.poses.split(",")
    sklb = None if a.skeleton == "none" else a.skeleton
    if sklb and not os.path.exists(sklb):
        sys.exit(f"skeleton not found: {sklb} (pass --skeleton none for the .glb rest pose)")
    print(f"rest pose: {sklb or 'the .glb (c0201)'}")
    signed, where, cloth = measure(a.build, wanted, sklb)
    report(a.build, signed, where, cloth)
    if a.save:
        stack = np.stack([signed[p] for p in wanted])
        with open(a.save, "xb") as handle:
            np.savez(handle, low=stack.min(0), pose=np.array(wanted)[stack.argmin(0)], rest=signed[wanted[0]], P=cloth["P"])


if __name__ == "__main__":
    main()
