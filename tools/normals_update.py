# New file for MuseFit (Track Suit v2d, 2026-11-14).
"""Turn each cloth vertex normal by how much the surface under it turned since a reference build. Raw .glb, no Blender.

    python3 -I -B normals_update.py <reference.glb> <moved.glb> <out.glb>

The raw-.glb steps (clip_push.py, peak_shave.py) move POSITION but keep NORMAL, so lighting still shows the old shape (a shaved
tip still looks like a crease). For every cloth primitive whose positions differ from the reference (same vertex count and
triangles), the geometric vertex normal (area weighted, welded across vertices at one position within the primitive) is
computed from both position sets, and the stored normal is turned by the rotation that takes the reference geometric normal
to the new one. Where nothing moved the normal is unchanged, so the creator's smoothing and hard edges stay. Where layers
fold onto one position (the welded face normals cancel: |sum| < 0.5 x sum of |face|), the direction is noise and the stored
normal is kept. Each turn is capped at atan(3 x the largest move among the vertex and its triangle neighbours / the longest
of its triangles' mean edge lengths, at least 5 mm), so tiny triangles that flip under a sub-mm move do not swing a normal. Only NORMAL of changed
primitives is rewritten; the reference must be the build whose stored normals match its positions (here v1).
"""
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np  # noqa: E402

import glb_raw as g  # noqa: E402
import muse_geom as mg  # noqa: E402


RELIABLE = 0.5  # |sum of face normals| / sum of |face normals| below this = folded layers, direction is noise
MIN_EDGE_M = 0.005  # tiny triangles flip under sub-mm moves: treat edges as at least 5 mm when limiting the turn


def geometric(P: np.ndarray, T: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Area-weighted vertex normals welded over coincident positions, and whether each one is reliable."""
    face = np.cross(P[T[:, 1]] - P[T[:, 0]], P[T[:, 2]] - P[T[:, 0]])
    area = np.linalg.norm(face, axis=1)
    _, inv = np.unique(np.round(P, 5), axis=0, return_inverse=True)
    inv = inv.ravel()
    S, A = np.zeros((inv.max() + 1, 3)), np.zeros(inv.max() + 1)
    for c in range(3):
        np.add.at(S, inv[T[:, c]], face)
        np.add.at(A, inv[T[:, c]], area)
    length = np.linalg.norm(S, axis=1)
    return (S / np.maximum(length, 1e-15)[:, None])[inv], (length > RELIABLE * A)[inv]


def rotate(N: np.ndarray, a: np.ndarray, b: np.ndarray, limit: np.ndarray) -> np.ndarray:
    """Turn each N by the rotation that takes unit vector a to unit vector b (Rodrigues), at most `limit` radians."""
    axis = np.cross(a, b)
    s = np.linalg.norm(axis, axis=1)
    angle = np.minimum(np.arctan2(s, (a * b).sum(1)), limit)
    s, c = np.sin(angle), np.cos(angle)
    k = axis / np.maximum(np.linalg.norm(axis, axis=1), 1e-15)[:, None]
    out = N * c[:, None] + np.cross(k, N) * s[:, None] + k * ((k * N).sum(1) * (1 - c))[:, None]
    out = np.where((s < 1e-9)[:, None], N, out)
    return out / np.maximum(np.linalg.norm(out, axis=1, keepdims=True), 1e-12)


def moved_near(P: np.ndarray, R: np.ndarray, T: np.ndarray) -> np.ndarray:
    """Largest move of a vertex or of any vertex sharing a triangle with it."""
    m = np.linalg.norm(P - R, axis=1)
    out = m.copy()
    for c in range(3):
        np.maximum.at(out, T[:, c], m[T].max(1))
    return out


def main(ref: str, src: str, out: str) -> None:
    if os.path.exists(out):
        sys.exit(f"refusing to overwrite {out}")
    rdoc, rblob = g.load(ref)
    doc, blob = g.load(src)
    rprims = {p["name"]: p for p in g.primitives(rdoc)}
    writer = g.GlbWriter(doc, blob)
    for prim in g.primitives(doc):
        if mg.SKIN_TAG in prim["material"]:
            continue
        rp = rprims[prim["name"]]
        P = g.read_accessor(doc, blob, prim["attributes"]["POSITION"]).astype(float)
        R = g.read_accessor(rdoc, rblob, rp["attributes"]["POSITION"]).astype(float)
        T = g.read_accessor(doc, blob, prim["indices"]).astype(int).reshape(-1, 3)
        if R.shape != P.shape or not np.array_equal(T, g.read_accessor(rdoc, rblob, rp["indices"]).astype(int).reshape(-1, 3)):
            sys.exit(f"{prim['name']}: topology differs from the reference")
        moved = np.linalg.norm(P - R, axis=1)
        if moved.max() < 1e-7:
            print(f"{prim['name']}: unchanged")
            continue
        N = g.read_accessor(doc, blob, prim["attributes"]["NORMAL"]).astype(float)
        a, a_ok = geometric(R, T)
        b, b_ok = geometric(P, T)
        near = moved_near(P, R, T)
        edge = np.zeros(len(P))
        lengths = np.linalg.norm(R[T] - R[np.roll(T, 1, axis=1)], axis=2).mean(1)
        for c in range(3):
            np.maximum.at(edge, T[:, c], lengths)
        limit = np.arctan(3 * near / np.maximum(edge, MIN_EDGE_M))  # a move d over an edge L tilts the surface ~atan(d/L)
        new = rotate(N, a, b, limit)
        keep = ~(a_ok & b_ok) | (near < 1e-5)
        new[keep] = N[keep]
        turn = np.degrees(np.arccos(np.clip((new * N).sum(1), -1, 1)))
        print(f"{prim['name']}: normals turned > 1 deg: {int((turn > 1).sum())}, > 10 deg: {int((turn > 10).sum())}, "
              f"max {turn.max():.1f} deg; left as stored (layers folded onto one position): {int((~(a_ok & b_ok)).sum())}")
        writer.doc["meshes"][prim["mesh"]]["primitives"][prim["prim"]]["attributes"]["NORMAL"] = writer.add_accessor(new.astype("<f4"), 5126, "VEC3")
    writer.save(out)


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    main(*sys.argv[1:])
