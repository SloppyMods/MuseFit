# MuseFit copy of builds/_dionys/e6116ts/cup_pull.py (XIVAutoFit). Changes: none besides the file name (cup_pull.py)
"""LOCAL (e6116 v2): pull a top's chest cloth onto a groove-free envelope of the Dionys chest, removing a leftover cup.

    blender -b --factory-startup --disable-autoexec -P cup_pull.py -- <in.glb> <out.glb> [clearance_mm=4]

Why: chest_flat.py's field takes the SMALLEST pull within CFR of each spot, so one vertex already near the skin keeps a
whole cup standing off; a small CFR pulls the cup in but traces rib/ab grooves. Here the target is not the skin but its
envelope: the skin's front depth map (2.5 mm grid, ray cast from the front) closed with a disk of CUPR mm (dilate then
erode = grooves narrower than that are filled, convex shapes such as the pecs stay), lightly blurred, never below the
skin. Per grid cell the pull is the smallest (cloth depth - envelope - clearance) of the cloth vertices within CUPS mm
(the layer nearest the body), filled, blurred CUPBLUR passes and masked to the chest panel; every cloth vertex in the
front half moves straight back by the field at its (x, z), so layers, seams and trims move together. Then whole columns
are lifted until every front cloth vertex is >= clearance off the real skin (as chest_flat.py's clear passes).
Env: CUPOPEN (0; mm opening radius that removes nipples from the target), CUPSQUASH (0; 1 = depth-proportional pull, no folds), CUPSTRING (0; n = straighten pieces under n verts), CUPRELAX (0; n passes smoothing the pull along the cloth surface), CUPR (30), CUPS (6), CUPBLUR (20), CUPX "x0,x1" panel fade (0.13,0.17), CUPZ "lo0,lo1,hi0,hi1" (1.12,1.16,1.31,1.37),
CUPMESH (mesh 1.0). Prints field stats, SEAMCHECK, STRETCH. Refuses to overwrite. Shape keys get the same moves.
"""
import os
import sys

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

a = sys.argv[sys.argv.index("--") + 1:]
src, out = a[0], a[1]
CLEAR = (float(a[2]) if len(a) > 2 else 4.0) / 1000
if os.path.exists(out):
    sys.exit(f"refusing to overwrite {out}")
R = float(os.environ.get("CUPR", "30")) / 1000
RS = float(os.environ.get("CUPS", "6")) / 1000
NBLUR = int(os.environ.get("CUPBLUR", "20"))
XF = [float(v) for v in os.environ.get("CUPX", "0.13,0.17").split(",")]
ZF = [float(v) for v in os.environ.get("CUPZ", "1.12,1.16,1.31,1.37").split(",")]
CLOTH = os.environ.get("CUPMESH", "mesh 1.0").split(",")
H = 0.0025
SKIN = "/mt_c0201b0001_bibo"

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)


def mat(o):
    return o.material_slots[0].material.name if o.material_slots and o.material_slots[0].material else ""


skins = [o for o in bpy.data.objects if o.type == "MESH" and mat(o).startswith(SKIN)]
cloth = [bpy.data.objects[n] for n in CLOTH]
verts, polys = [], []
for o in skins:
    m = o.matrix_world
    base = len(verts)
    verts += [m @ v.co for v in o.data.vertices]
    polys += [[base + i for i in p.vertices] for p in o.data.polygons]
tree = BVHTree.FromPolygons(verts, polys)
for o in cloth:
    assert o.matrix_world.is_identity or True

# Blender (z up) from a y-up glb: the body faces -Y. depth = how far forward = -y.
X0, X1, Z0, Z1 = -XF[1] - 0.02, XF[1] + 0.02, ZF[0] - 0.02, ZF[3] + 0.02
NX, NZ = int(round((X1 - X0) / H)) + 1, int(round((Z1 - Z0) / H)) + 1
xs = X0 + np.arange(NX) * H
zs = Z0 + np.arange(NZ) * H
D = np.full((NX, NZ), np.nan)
MID = np.full((NX, NZ), np.nan)
for i, x in enumerate(xs):
    for k, z in enumerate(zs):
        hit = tree.ray_cast(Vector((x, -0.6, z)), Vector((0, 1, 0)))
        back = tree.ray_cast(Vector((x, 0.6, z)), Vector((0, -1, 0)))
        if hit[0] is not None:
            D[i, k] = -hit[0].y
        if hit[0] is not None and back[0] is not None:
            MID[i, k] = -(hit[0].y + back[0].y) / 2
# fill holes (outside the body silhouette) with the nearest row value so morphology stays defined
for k in range(NZ):
    col = D[:, k]
    ok = ~np.isnan(col)
    if ok.any():
        D[:, k] = np.interp(np.arange(NX), np.where(ok)[0], col[ok])
D = np.nan_to_num(D, nan=np.nanmin(D))
for k in range(NZ):
    col = MID[:, k]; ok = ~np.isnan(col)
    MID[:, k] = np.interp(np.arange(NX), np.where(ok)[0], col[ok]) if ok.any() else 0.0

r = int(round(R / H))
offs = [(di, dk) for di in range(-r, r + 1) for dk in range(-r, r + 1) if di * di + dk * dk <= r * r]


def morph(A, fn, fill):
    P = np.pad(A, r, constant_values=fill)
    stack = [P[r + di:r + di + NX, r + dk:r + dk + NZ] for di, dk in offs]
    return fn(np.stack(stack), axis=0)


# CUPOPEN=<mm> (added for the Track Suit): remove narrow peaks (nipples) from the skin depth map before the envelope is
# built (grey opening with that radius); the clearance pass then also ignores skin points that stick out of the opened map
# by more than 0.8 mm, so the cloth is not tented over a nipple tip.
OPENR = float(os.environ.get("CUPOPEN", "0")) / 1000
D_RAW = D.copy()
if OPENR > 0:
    ro = max(1, int(round(OPENR / H)))
    ooffs = [(di, dk) for di in range(-ro, ro + 1) for dk in range(-ro, ro + 1) if di * di + dk * dk <= ro * ro]
    def omorph(A, fn, fill):
        P = np.pad(A, ro, constant_values=fill)
        return fn(np.stack([P[ro + di:ro + di + NX, ro + dk:ro + dk + NZ] for di, dk in ooffs]), axis=0)
    D = omorph(omorph(D, np.min, 9.0), np.max, -1.0)  # erode then dilate = opening (narrow peaks removed)
    print(f"opening {OPENR * 1000:.0f} mm: peaks removed up to {(D_RAW - D).max() * 1000:.1f} mm")
MODE = os.environ.get("CUPMODE", "smooth")
SIGP = int(os.environ.get("CUPSIGP", "400"))  # blur passes for the smooth surface (400 passes ~ sigma 10 cells = 25 mm)
if MODE == "close":
    E = np.maximum(morph(morph(D, np.max, -1.0), np.min, 9.0), D)  # closing: fills grooves, keeps convex shapes
else:
    pass  # set after blur() is defined


def blur(A, n):
    for _ in range(n):
        P = np.pad(A, 1, mode="edge")
        A = 0.5 * A + 0.125 * (P[:-2, 1:-1] + P[2:, 1:-1] + P[1:-1, :-2] + P[1:-1, 2:])
    return A


if MODE != "close":
    Sm = blur(D, SIGP)                     # smooth chest surface
    L = blur(morph(D - Sm, np.max, -1.0), SIGP // 4)  # lift so it stays above the skin's convex bumps (pecs, abs)
    E = Sm + L
E = np.maximum(blur(E, 4), D)
print(f"envelope mode {MODE}: above skin mm p50 {np.median(E - D) * 1000:.1f} max {(E - D).max() * 1000:.1f}")


def bil(G, x, z):
    fi = min(NX - 1.001, max(0.0, (x - X0) / H)); fk = min(NZ - 1.001, max(0.0, (z - Z0) / H))
    i, k = int(fi), int(fk); u, w = fi - i, fk - k
    return G[i, k] * (1 - u) * (1 - w) + G[i + 1, k] * u * (1 - w) + G[i, k + 1] * (1 - u) * w + G[i + 1, k + 1] * u * w


def ramp(v, lo, hi):
    return 0.0 if v <= lo else 1.0 if v >= hi else (v - lo) / (hi - lo)


def mask(co):
    return ramp(co.z, ZF[0], ZF[1]) * (1 - ramp(co.z, ZF[2], ZF[3])) * (1 - ramp(abs(co.x), XF[0], XF[1]))


def front(co):  # front half: in front of the skin's front/back mid-plane by > 1 cm, fading in over 3 cm
    return ramp(-co.y - bil(MID, co.x, co.z), 0.01, 0.04)


def facing(co):  # nearest skin faces forward (normal mostly -y), so moving along y changes the gap
    loc, nrm, _, dist = tree.find_nearest(co)
    return nrm is not None and -nrm.y > 0.6


# pull samples: cloth vertices in the panel, their distance in front of the envelope minus clearance
samp = []
for o in cloth:
    for v in o.data.vertices:
        co = o.matrix_world @ v.co
        if mask(co) <= 0 or front(co) <= 0 or not facing(co):
            continue
        samp.append((co.x, co.z, max(0.0, (-co.y) - bil(E, co.x, co.z) - CLEAR)))
kd = KDTree(len(samp))
for j, s in enumerate(samp):
    kd.insert((s[0], s[1], 0), j)
kd.balance()
G = np.full((NX, NZ), np.nan)
for i, x in enumerate(xs):
    for k, z in enumerate(zs):
        near = kd.find_range((x, z, 0), RS)
        if near:
            G[i, k] = min(samp[j][2] for _, j, _ in near)
for _ in range(400):
    miss = np.isnan(G)
    if not miss.any():
        break
    P = np.pad(G, 1, constant_values=np.nan)
    nb = np.stack([P[:-2, 1:-1], P[2:, 1:-1], P[1:-1, :-2], P[1:-1, 2:]])
    fill = np.nanmean(np.where(np.isnan(nb), np.nan, nb), axis=0)
    G = np.where(miss & ~np.isnan(fill), fill, G)
G = blur(np.nan_to_num(G), NBLUR)

start = {(o.name, v.index): Vector(o.matrix_world @ v.co) for o in cloth for v in o.data.vertices}
SQUASH = os.environ.get("CUPSQUASH", "0") == "1"
if SQUASH:
    # CUPSQUASH=1 (added for the Track Suit): weight = (depth - mid) / (T - mid), T = the cloth's front-most depth in that
    # column. The front surface takes the full pull, the mid-plane none, everything between scales linearly, so the
    # front can never pass behind a cup's side wall (the 3 cm front() ramp let it fold there).
    T = np.full((NX, NZ), np.nan)
    for o in cloth:
        for v in o.data.vertices:
            co = o.matrix_world @ v.co
            i, k = int(round((co.x - X0) / H)), int(round((co.z - Z0) / H))
            if 0 <= i < NX and 0 <= k < NZ and -co.y > bil(MID, co.x, co.z):
                T[i, k] = -co.y if np.isnan(T[i, k]) else max(T[i, k], -co.y)
    for _ in range(400):
        miss = np.isnan(T)
        if not miss.any():
            break
        P = np.pad(T, 1, constant_values=np.nan)
        nb = np.stack([P[:-2, 1:-1], P[2:, 1:-1], P[1:-1, :-2], P[1:-1, 2:]])
        with np.errstate(all="ignore"):
            fill = np.nanmax(nb, axis=0)
        T = np.where(miss & ~np.isnan(fill), fill, T)
    T = np.nan_to_num(T, nan=0.0)
    T = np.maximum(T, blur(T, 6))  # smooth but never below the real front surface


def wmove(co):
    if not SQUASH:
        return mask(co) * front(co)
    mid = bil(MID, co.x, co.z); top = bil(T, co.x, co.z)
    return mask(co) * min(1.0, max(0.0, (-co.y - mid) / max(top - mid, 0.01)))
moved, mx = 0, 0.0


def apply(field, label):
    global moved, mx
    for o in cloth:
        inv = o.matrix_world.inverted()
        keys = o.data.shape_keys
        for v in o.data.vertices:
            co = o.matrix_world @ v.co
            w = wmove(co)
            if w <= 0:
                continue
            d = bil(field, co.x, co.z) * w
            if abs(d) < 1e-7:
                continue
            step = inv.to_3x3() @ Vector((0, d, 0))  # positive d = move back (+y)
            v.co += step
            if keys:
                for kb in keys.key_blocks:
                    kb.data[v.index].co += step
            if label == "pull":
                moved += 1; mx = max(mx, abs(d))
        o.data.update()


apply(G, "pull")
print(f"cup pull: samples {len(samp)} moved {moved} max mm {mx * 1000:.1f} envelope fill mm max {(E - D).max() * 1000:.1f}")

# optional CUPSTRING=<n>: loose pieces (welded islands) with fewer than n vertices, such as drawstrings, get their pull
# replaced by a least-squares fit that is linear in height, so a straight string stays straight (added for the Track Suit).
NSTR = int(os.environ.get("CUPSTRING", "0"))
if NSTR:
    for o in cloth:
        vs = o.data.vertices
        par = list(range(len(vs)))
        def fnd(i):
            while par[i] != i:
                par[i] = par[par[i]]; i = par[i]
            return i
        seen = {}
        for v in vs:
            kk = tuple(round(c, 5) for c in start[o.name, v.index])
            if kk in seen: par[fnd(v.index)] = fnd(seen[kk])
            else: seen[kk] = v.index
        for e in o.data.edges:
            a0, a1 = fnd(e.vertices[0]), fnd(e.vertices[1])
            if a0 != a1: par[a0] = a1
        groups = {}
        for v in vs: groups.setdefault(fnd(v.index), []).append(v.index)
        inv = o.matrix_world.inverted().to_3x3(); nfix = 0
        for g in groups.values():
            if len(g) >= NSTR: continue
            st = np.array([tuple(start[o.name, i]) for i in g]); cur = np.array([tuple(o.matrix_world @ vs[i].co) for i in g])
            disp = cur - st
            if np.abs(disp).max() < 1e-6: continue
            A = np.stack([np.ones(len(g)), st[:, 2]], 1)
            coef, *_ = np.linalg.lstsq(A, disp, rcond=None)
            fit = A @ coef
            for j, i in enumerate(g):
                step = inv @ Vector(tuple(fit[j] - disp[j]))
                vs[i].co += step
                if o.data.shape_keys:
                    for kb in o.data.shape_keys.key_blocks: kb.data[i].co += step
            nfix += 1
        o.data.update()
        print(f"strings: {nfix} small pieces (< {NSTR} verts) moved by a linear-in-height fit")

# optional (CUPRELAX=n, added for the Track Suit): smooth the pull displacement along the cloth surface n times, so a cup's
# side wall moves with its front instead of the front folding behind it. Coincident vertices are welded so seams stay shut;
# cloth borders keep their displacement fixed only if CUPRELAXPIN=1 (default 0).
RELAX = int(os.environ.get("CUPRELAX", "0"))
if RELAX:
    from collections import defaultdict
    for o in cloth:
        vs = o.data.vertices
        cur = np.array([tuple(o.matrix_world @ v.co) for v in vs])
        st = np.array([tuple(start[o.name, v.index]) for v in vs])
        disp = cur - st
        keyd = {}
        rep = np.array([keyd.setdefault(tuple(np.round(st[i], 5)), i) for i in range(len(vs))])
        adj = defaultdict(set)
        for e in o.data.edges:
            a0, a1 = rep[e.vertices[0]], rep[e.vertices[1]]
            if a0 != a1:
                adj[a0].add(a1); adj[a1].add(a0)
        reps = np.unique(rep)
        moving = np.zeros(len(vs), bool)
        moving[reps] = np.linalg.norm(disp[reps], axis=1) > 1e-6
        # relax over the moved region plus a 1-ring margin so the edge of the pulled area blends out
        region = set(np.where(moving)[0])
        for i in list(region):
            region |= adj[i]
        region = np.array(sorted(region))
        D = disp.copy()
        for _ in range(RELAX):
            N = D.copy()
            for i in region:
                nb = list(adj[i])
                if nb:
                    N[i] = 0.5 * D[i] + 0.5 * D[nb].mean(axis=0)
            D = N
        D = D[rep]  # every vertex takes its representative's displacement (seams stay closed)
        inv = o.matrix_world.inverted().to_3x3()
        keys = o.data.shape_keys
        for v in vs:
            step = inv @ Vector(tuple(D[v.index] - disp[v.index]))
            if step.length > 1e-9:
                v.co += step
                if keys:
                    for kb in keys.key_blocks:
                        kb.data[v.index].co += step
        o.data.update()
    print(f"relax: {RELAX} passes on the pull displacement")

# clearance: lift columns until front cloth vertices are CLEAR off the real skin
for it in range(10):
    S = np.zeros((NX, NZ)); short = 0
    for o in cloth:
        for v in o.data.vertices:
            co = o.matrix_world @ v.co
            w = mask(co) * front(co)
            if w < 0.05:
                continue
            loc, nrm, _, dist = tree.find_nearest(co)
            if nrm is None or dist > 0.03 or -nrm.y < 0.6:
                continue
            sd = dist if (co - loc).dot(nrm) >= 0 else -dist
            if sd >= CLEAR - 0.0001:
                continue
            if OPENR > 0 and bil(D_RAW, loc.x, loc.z) - bil(D, loc.x, loc.z) > 0.0008:
                continue  # nipple tip: removed from the target on purpose
            short += 1
            need = min(0.012, (CLEAR - sd + 0.0003) / max(w, 0.3))
            i, k = int((co.x - X0) / H), int((co.z - Z0) / H)
            S[max(0, i - 1):i + 3, max(0, k - 1):k + 3] = np.maximum(S[max(0, i - 1):i + 3, max(0, k - 1):k + 3], need)
    print("clear pass", it, "short", short)
    if not short:
        break
    apply(-np.minimum(blur(S, 2) * 1.4, 0.004), "clear")  # at most 4 mm per pass

# checks: coincident pairs and edge stretch
pts = [(o.name, v.index, start[o.name, v.index]) for o in cloth for v in o.data.vertices]
kda = KDTree(len(pts))
for j, p in enumerate(pts):
    kda.insert(p[2], j)
kda.balance()
now = {(o.name, v.index): o.matrix_world @ v.co for o in cloth for v in o.data.vertices}
sep = 0.0; npair = 0
for j, (nm, vi, c) in enumerate(pts):
    for _, j2, _ in kda.find_range(c, 0.00005):
        if j2 > j:
            npair += 1; sep = max(sep, (now[nm, vi] - now[pts[j2][0], pts[j2][1]]).length)
print(f"SEAMCHECK coincident pairs {npair} max separation mm {sep * 1000:.3f}")
rat = []
for o in cloth:
    for e in o.data.edges:
        a0, a1 = e.vertices
        l0 = (start[o.name, a0] - start[o.name, a1]).length
        if l0 > 1e-6 and ((now[o.name, a0] - start[o.name, a0]).length > 1e-5 or (now[o.name, a1] - start[o.name, a1]).length > 1e-5):
            rat.append((now[o.name, a0] - now[o.name, a1]).length / l0)
rat = np.array(rat)
if len(rat):
    print(f"STRETCH moved edges {len(rat)} p1={np.percentile(rat, 1):.2f} p99={np.percentile(rat, 99):.2f} "
          f"min={rat.min():.2f} max={rat.max():.2f} outside 0.5-2x: {((rat < 0.5) | (rat > 2)).sum()}")
bpy.ops.export_scene.gltf(filepath=out, export_format="GLB", export_extras=True)
