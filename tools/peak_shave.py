# New file for MuseFit (Track Suit v2d, 2026-11-14).
"""Shave sharp peaks off cloth in a box (a leftover cup or nipple tip), keeping broad shapes. Raw .glb, no Blender.

    python3 -I -B peak_shave.py <in.glb> <out.glb> [mesh name=mesh 2.0] [step_mm=1.0] [floor_mm=3.5] [passes=60]

Env SHAVEBOX="xmin,xmax,ymin,ymax,zmin" (glTF metres; |x| is used, so the box is mirrored to both sides; default
0.055,0.135,1.18,1.31,0.0 = the outer bust, front only).
Each cloth vertex in the box has a height: its signed distance to the Muse skin. Each pass lowers every vertex whose height is
more than step_mm above the mean height of its mesh neighbours down to that mean + step_mm (never raises, never below floor_mm),
over the welded mesh (vertices at one position move as one). The lowering is applied along the skin normal at the vertex's
closest skin point. A ramp over the outer 15 mm of the box fades the change to 0, so the box edge leaves no step.
Then, within SHAVESMOOTHR (25 mm) of the shaved points, SHAVESMOOTH (20) passes of two-way smoothing of the height (half way
to the neighbour mean, fading out with distance) fill the dent a cut tip leaves; never below floor_mm.
Then run normals_update.py so the lighting follows the new shape.
Only POSITION of the named mesh is rewritten.
"""
import os
import sys
from collections import defaultdict

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np  # noqa: E402

import glb_raw as g  # noqa: E402
import muse_geom as mg  # noqa: E402

FADE_M = 0.015
SMOOTH_R = float(os.environ.get("SHAVESMOOTHR", "0.025"))  # metres around shaved points that get the two-way smoothing
SMOOTH_PASSES = int(os.environ.get("SHAVESMOOTH", "20"))


def box_ramp(P: np.ndarray, box: list[float]) -> np.ndarray:
    xmin, xmax, ymin, ymax, zmin = box
    x, y, z = np.abs(P[:, 0]), P[:, 1], P[:, 2]
    inside = np.minimum.reduce([x - xmin, xmax - x, y - ymin, ymax - y])
    return np.where(z > zmin, np.clip(inside / FADE_M, 0, 1), 0)


def main(src: str, out: str, mesh: str, step_mm: float, floor_mm: float, passes: int) -> None:
    if os.path.exists(out):
        sys.exit(f"refusing to overwrite {out}")
    box = [float(v) for v in os.environ.get("SHAVEBOX", "0.055,0.135,1.18,1.31,0.0").split(",")]
    doc, blob, skin, cloth = mg.load(src)
    k = next(i for i, p in enumerate(cloth["prims"]) if p["name"] == mesh)
    own = np.flatnonzero(cloth["owner"] == k)
    P = cloth["P"][own]
    T = g.read_accessor(doc, blob, cloth["prims"][k]["indices"]).astype(int).reshape(-1, 3)
    _, rep = np.unique(np.round(P, 5), axis=0, return_inverse=True)
    rep = rep.ravel()
    adj = defaultdict(set)
    for a, b, c in rep[T]:
        for u, v in ((a, b), (b, c), (c, a)):
            if u != v:
                adj[u].add(v)
                adj[v].add(u)
    n = rep.max() + 1
    first = np.zeros(n, int)
    first[rep[::-1]] = np.arange(len(rep))[::-1]  # one vertex per welded position
    h0, _, _, normal = mg.Surface(skin["P"], skin["T"]).signed(P[first])
    ramp = box_ramp(P[first], box)
    active = [i for i in range(n) if ramp[i] > 0 and adj[i]]
    h = h0.copy()
    step, floor = step_mm / 1000, floor_mm / 1000
    for _ in range(passes):
        mean = np.array([h[list(adj[i])].mean() for i in active])
        cap = np.maximum(mean + step, floor)
        h[active] = np.minimum(h[active], np.maximum(cap, np.minimum(h[active], floor)))
    # then smooth both ways (up and down) just around what was shaved, so a cut tip leaves no dent
    shaved = np.flatnonzero(h0 - h > 0.0005)
    if len(shaved) and SMOOTH_PASSES:
        Q = P[first]
        near = np.min(np.linalg.norm(Q[:, None] - Q[shaved][None], axis=-1), axis=1)
        mix = np.clip((SMOOTH_R - near) / (SMOOTH_R / 2), 0, 1) * ramp
        zone = [i for i in active if mix[i] > 0]
        for _ in range(SMOOTH_PASSES):
            mean = np.array([h[list(adj[i])].mean() for i in zone])
            h[zone] = np.maximum((1 - 0.5 * mix[zone]) * h[zone] + 0.5 * mix[zone] * mean, np.minimum(h0[zone], floor))
        print(f"smoothed {len(zone)} positions within {SMOOTH_R * 1000:.0f} mm of the shaved ones, {SMOOTH_PASSES} passes")
    lower = (h - h0) * ramp  # mostly <= 0; the smoothing may lift a dent back a little
    move = lower[:, None] * normal
    newP = P + move[rep]
    depth = -lower * 1000
    print(f"{mesh}: {len(active)} positions in the box; lowered > 0.5 mm: {int((depth > 0.5).sum())}, > 3 mm: {int((depth > 3).sum())}, "
          f"max {depth.max():.1f} mm (from {h0[depth.argmax()] * 1000:.1f} to {(h0[depth.argmax()] + lower[depth.argmax()]) * 1000:.1f} mm off the skin) "
          f"at {np.round(P[first][depth.argmax()], 3)}")
    writer = g.GlbWriter(doc, blob)
    prim = cloth["prims"][k]
    writer.doc["meshes"][prim["mesh"]]["primitives"][prim["prim"]]["attributes"]["POSITION"] = writer.add_accessor(newP.astype("<f4"), 5126, "VEC3")
    writer.save(out)


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) < 2:
        sys.exit(__doc__)
    main(a[0], a[1], a[2] if len(a) > 2 else "mesh 2.0", float(a[3]) if len(a) > 3 else 1.0,
         float(a[4]) if len(a) > 4 else 3.5, int(a[5]) if len(a) > 5 else 60)
