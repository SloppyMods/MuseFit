# New file for MuseFit (Track Suit v2 fix, 2026-11-14). Posing code adapted from XIVAutoFit tools/male_score.py (git ca7988d):
# pose_matrices() and rotation() are copies; everything else is new.
"""Shared numpy geometry for the MuseFit raw-.glb tools: skin and cloth with dense weights, simulated poses, and the exact
signed distance from points to a triangle mesh. Plain numpy, no Blender, no scipy. Imported by posed_clip.py, chest_remap.py
and clip_push.py; it never writes anything.

Coordinates are the glTF ones: y is up, +z is the front of the body, +x is the character's left.
"""
import json
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np  # noqa: E402

import glb_raw as g  # noqa: E402

SKIN_TAG = "b0001"  # the Muse skin material is /mt_c0201b0001_bibo.mtrl
POSES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "poses.json")


def bone_names(doc: dict) -> list[str]:
    return [doc["nodes"][i].get("name") for i in doc["skins"][0]["joints"]]


def dense_weights(doc: dict, blob: bytes, prim: dict, n_bones: int) -> np.ndarray:
    """(vertices, bones) weights from JOINTS_0/1 and WEIGHTS_0/1, rows summing to 1."""
    count = doc["accessors"][prim["attributes"]["POSITION"]]["count"]
    W = np.zeros((count, n_bones))
    for slot in ("0", "1"):
        if "JOINTS_" + slot not in prim["attributes"]:
            continue
        J = g.read_accessor(doc, blob, prim["attributes"]["JOINTS_" + slot]).astype(int)
        acc = doc["accessors"][prim["attributes"]["WEIGHTS_" + slot]]
        Wt = g.read_accessor(doc, blob, prim["attributes"]["WEIGHTS_" + slot]).astype(float)
        if acc["componentType"] != 5126:
            Wt = Wt / g.DIVISOR[acc["componentType"]]
        for k in range(J.shape[1]):
            np.add.at(W, (np.arange(count), J[:, k]), Wt[:, k])
    return W / np.maximum(W.sum(1, keepdims=True), 1e-12)


def mesh_of(doc: dict, blob: bytes, prims: list[dict], n_bones: int) -> dict:
    """Merge primitives into one mesh: positions, triangles, dense weights, and which primitive each vertex came from."""
    P, T, W, owner, base = [], [], [], [], 0
    for k, prim in enumerate(prims):
        p = g.read_accessor(doc, blob, prim["attributes"]["POSITION"]).astype(float)
        P.append(p)
        T.append(g.read_accessor(doc, blob, prim["indices"]).astype(int).reshape(-1, 3) + base)
        W.append(dense_weights(doc, blob, prim, n_bones))
        owner.append(np.full(len(p), k))
        base += len(p)
    return dict(P=np.vstack(P), T=np.vstack(T), W=np.vstack(W), owner=np.concatenate(owner), prims=prims)


def load(path: str) -> tuple[dict, bytes, dict, dict]:
    """(doc, blob, skin mesh, cloth mesh) of a build."""
    doc, blob = g.load(path)
    n = len(bone_names(doc))
    prims = g.primitives(doc)
    skin = mesh_of(doc, blob, [p for p in prims if SKIN_TAG in p["material"]], n)
    cloth = mesh_of(doc, blob, [p for p in prims if SKIN_TAG not in p["material"]], n)
    return doc, blob, skin, cloth


# ---- simulated poses (bone turns about world axes, as XIVAutoFit's checks do) ----

def rotation(axis: str, degrees: float) -> np.ndarray:
    angle = np.radians(degrees)
    c, s = np.cos(angle), np.sin(angle)
    return {"x": np.array([[1, 0, 0], [0, c, -s], [0, s, c]]), "y": np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]]),
            "z": np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])}[axis]


def pose_matrices(names: list[str], parents: list[int], rest: np.ndarray, spec: list) -> np.ndarray:
    """World 4x4 per bone: each listed bone turns about its own rest position, about a world axis, and carries its children."""
    index = {n: i for i, n in enumerate(names)}
    local = np.tile(np.eye(4), (len(names), 1, 1))
    for bone, axis, degrees in spec:
        if bone not in index:
            continue
        pivot = rest[index[bone]][:3, 3]
        m = np.eye(4)
        m[:3, :3] = rotation(axis, degrees)
        m[:3, 3] = pivot - m[:3, :3] @ pivot
        local[index[bone]] = m
    out = np.zeros_like(local)
    done = [False] * len(names)

    def resolve(i: int) -> np.ndarray:
        if not done[i]:
            out[i] = local[i] if parents[i] < 0 else resolve(parents[i]) @ local[i]
            done[i] = True
        return out[i]

    for i in range(len(names)):
        resolve(i)
    return out


def poses(wanted: list[str]) -> dict[str, list]:
    table = json.load(open(POSES_FILE))
    table.setdefault("stand", [])
    return {name: table[name] for name in wanted}


def posed(P: np.ndarray, W: np.ndarray, matrices: np.ndarray) -> np.ndarray:
    """Linear blend skinning with dense weights (only the bones that carry weight are used)."""
    used = np.flatnonzero(W.sum(0) > 0)
    blended = np.einsum("vb,bij->vij", W[:, used], matrices[used])
    return (blended[:, :3, :3] @ P[..., None])[..., 0] + blended[:, :3, 3]


# ---- distances ----

def vertex_normals(P: np.ndarray, T: np.ndarray) -> np.ndarray:
    face = np.cross(P[T[:, 1]] - P[T[:, 0]], P[T[:, 2]] - P[T[:, 0]])
    N = np.zeros_like(P)
    for corner in range(3):
        np.add.at(N, T[:, corner], face)
    # coincident vertices (UV seams, submesh borders) share one normal
    _, rep, inv = np.unique(np.round(P, 5), axis=0, return_index=True, return_inverse=True)
    summed = np.zeros((len(rep), 3))
    np.add.at(summed, inv.ravel(), N)
    N = summed[inv.ravel()]
    return N / np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-12)


def knn(src: np.ndarray, dst: np.ndarray, k: int, chunk: int = 2048) -> np.ndarray:
    """Indices of the k nearest dst points for each src point (brute force in chunks)."""
    out = np.empty((len(src), k), int)
    dd = (dst ** 2).sum(1)
    for s in range(0, len(src), chunk):
        a = src[s:s + chunk]
        d = (a ** 2).sum(1)[:, None] - 2 * a @ dst.T + dd[None]
        part = np.argpartition(d, k, axis=1)[:, :k]
        order = np.take_along_axis(d, part, 1).argsort(1)
        out[s:s + chunk] = np.take_along_axis(part, order, 1)
    return out


def closest_on_triangles(p: np.ndarray, a: np.ndarray, b: np.ndarray, c: np.ndarray) -> np.ndarray:
    """Barycentric weights of the closest point on each triangle (a, b, c) to p (Ericson's method, vectorised)."""
    ab, ac, ap = b - a, c - a, p - a
    d1, d2 = (ab * ap).sum(-1), (ac * ap).sum(-1)
    bp = p - b
    d3, d4 = (ab * bp).sum(-1), (ac * bp).sum(-1)
    cp = p - c
    d5, d6 = (ab * cp).sum(-1), (ac * cp).sum(-1)
    va, vb, vc = d3 * d6 - d5 * d4, d5 * d2 - d1 * d6, d1 * d4 - d3 * d2
    denom = np.where(np.abs(va + vb + vc) > 1e-30, va + vb + vc, 1e-30)
    v, w = vb / denom, vc / denom
    bary = np.stack([1 - v - w, v, w], -1)
    tests = [  # (condition, barycentric) applied last-to-first so the region tests win as in the scalar version
        ((d1 <= 0) & (d2 <= 0), lambda: np.stack([np.ones_like(d1), 0 * d1, 0 * d1], -1)),
        ((d3 >= 0) & (d4 <= d3), lambda: np.stack([0 * d1, np.ones_like(d1), 0 * d1], -1)),
        ((d6 >= 0) & (d5 <= d6), lambda: np.stack([0 * d1, 0 * d1, np.ones_like(d1)], -1)),
        ((vc <= 0) & (d1 >= 0) & (d3 <= 0), lambda: (lambda t: np.stack([1 - t, t, 0 * t], -1))(d1 / np.where(d1 - d3 != 0, d1 - d3, 1e-30))),
        ((vb <= 0) & (d2 >= 0) & (d6 <= 0), lambda: (lambda t: np.stack([1 - t, 0 * t, t], -1))(d2 / np.where(d2 - d6 != 0, d2 - d6, 1e-30))),
        ((va <= 0) & ((d4 - d3) >= 0) & ((d5 - d6) >= 0),
         lambda: (lambda t: np.stack([0 * t, 1 - t, t], -1))((d4 - d3) / np.where((d4 - d3) + (d5 - d6) != 0, (d4 - d3) + (d5 - d6), 1e-30))),
    ]
    done = np.zeros(d1.shape, bool)
    for cond, value in tests:
        use = cond & ~done
        if use.any():
            bary = np.where(use[..., None], value(), bary)
        done |= cond
    return bary


def vertex_triangles(T: np.ndarray, n: int, cap: int = 12) -> np.ndarray:
    """For each vertex, up to `cap` triangle indices that use it (-1 padded)."""
    out = np.full((n, cap), -1, int)
    fill = np.zeros(n, int)
    for t, tri in enumerate(T):
        for v in tri:
            if fill[v] < cap:
                out[v, fill[v]] = t
                fill[v] += 1
    return out


class Surface:
    """A triangle mesh to measure against. signed() gives the signed distance (positive = outside, along the surface normal),
    the closest triangle and its barycentric weights for each query point."""

    def __init__(self, P: np.ndarray, T: np.ndarray, k: int = 8):
        self.P, self.T, self.k = P, T, k
        self.N = vertex_normals(P, T)
        self.vt = vertex_triangles(T, len(P))

    def signed(self, Q: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        near = knn(Q, self.P, self.k)
        cand = self.vt[near].reshape(len(Q), -1)  # candidate triangles: those touching the k nearest vertices
        valid = cand >= 0
        cand = np.where(valid, cand, self.vt[near[:, 0], 0][:, None])
        tri = self.T[cand]
        a, b, c = self.P[tri[..., 0]], self.P[tri[..., 1]], self.P[tri[..., 2]]
        bary = closest_on_triangles(Q[:, None], a, b, c)
        hit = bary[..., 0:1] * a + bary[..., 1:2] * b + bary[..., 2:3] * c
        dist = np.linalg.norm(Q[:, None] - hit, axis=-1)
        best = dist.argmin(1)
        r = np.arange(len(Q))
        tri_best, bary_best, hit_best = cand[r, best], bary[r, best], hit[r, best]
        n = (self.N[self.T[tri_best]] * bary_best[..., None]).sum(1)
        n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
        sign = np.where(((Q - hit_best) * n).sum(1) < 0, -1.0, 1.0)
        return sign * dist[r, best], tri_best, bary_best, n


def region(P: np.ndarray) -> np.ndarray:
    """Coarse body region per point (rest pose), for 'where' reports."""
    x, y, z = np.abs(P[:, 0]), P[:, 1], P[:, 2]
    out = np.where(x > 0.2, "sleeve", np.where((x > 0.08) & (y > 1.18) & (y < 1.35), "armpit", np.where(z < 0, "back", "front")))
    return np.where((x > 0.2) & (y > 1.18) & (x < 0.26), "sleeve-armpit", out)
