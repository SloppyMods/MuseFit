# MuseFit copy of builds/_dionys/e6116ts/meas/chest_meas.py (XIVAutoFit, ). Changes: none
"""Chest gap and front 'bumpiness' (ab/pec contour) of a top on the Dionys skin. Read only.

    blender -b --factory-startup --disable-autoexec -P chest_meas.py -- <build.glb> [skin.glb] [cloth mesh, default "mesh 1.0"]

skin: the bibo skin of the build itself, or a separate skin file (to score a creator file on the full in-game skin).

GAP: signed distance (mm) from each front cloth vertex of the largest cloth island (no drawstrings) to the skin,
per 2 cm height row, |x| < 0.10, the outer layer only (vertices whose normal faces away from the body).
BUMP: rays shot from the front onto the cloth give the visible front surface as a depth map (2 mm grid,
|x| < 0.12, height 1.08-1.34). Each point is compared with a local quadratic surface fitted to its 30 mm
neighbourhood (Gaussian, sigma 12 mm); BUMP is the RMS of that residual in mm, and p95 of |residual|.
A smooth drape (fabric over the body) scores low; cloth that copies pecs and abs scores high.
"""
import sys, os
import bpy, bmesh
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

a = sys.argv[sys.argv.index("--") + 1:]
build = a[0]; skinf = a[1] if len(a) > 1 and a[1] not in ("", "-") else None
CLOTH = a[2] if len(a) > 2 else "mesh 1.0"
SKIN_MAT = "/mt_c0201b0001_bibo.mtrl"

def mat(o):
    return o.material_slots[0].material.name if o.material_slots and o.material_slots[0].material else ""

def load(p):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=p)
    return [o for o in bpy.data.objects if o not in before]

def world_mesh(objs):
    verts, tris = [], []
    for o in objs:
        dg = bpy.context.evaluated_depsgraph_get(); oe = o.evaluated_get(dg); me = oe.to_mesh()
        base = len(verts); verts += [o.matrix_world @ v.co for v in me.vertices]
        me.calc_loop_triangles()
        tris += [tuple(base + i for i in t.vertices) for t in me.loop_triangles]
        oe.to_mesh_clear()
    return verts, tris

bpy.ops.wm.read_factory_settings(use_empty=True)
objs = load(build)
skin_objs = [o for o in (load(skinf) if skinf else objs) if o.type == "MESH" and SKIN_MAT in mat(o)]
sv, st = world_mesh(skin_objs)
stree = BVHTree.FromPolygons(sv, st)
bust = max((v for v in sv if 1.25 < v.z < 1.32 and abs(v.x) < 0.1), key=lambda v: abs(v.y))
FRONT = 1 if bust.y > 0 else -1

cloth = [o for o in objs if o.type == "MESH" and o.name == CLOTH]
o = cloth[0]
bm = bmesh.new(); bm.from_mesh(o.data); bm.verts.ensure_lookup_table()
# islands (weld coincident verts first so UV seams do not split islands)
pos = {}
parent = list(range(len(bm.verts)))
def find(i):
    while parent[i] != i:
        parent[i] = parent[parent[i]]; i = parent[i]
    return i
for v in bm.verts:
    k = tuple(round(c, 5) for c in v.co)
    if k in pos: parent[find(v.index)] = find(pos[k])
    else: pos[k] = v.index
for e in bm.edges:
    x, y = find(e.verts[0].index), find(e.verts[1].index)
    if x != y: parent[x] = y
sizes = {}
for v in bm.verts: sizes[find(v.index)] = sizes.get(find(v.index), 0) + 1
main = max(sizes, key=sizes.get)
MINISL = int(os.environ.get("CMMINISL", "0"))  # local: >0 keeps every island with at least this many verts (hood is the largest here)
keep = {v.index for v in bm.verts if (sizes[find(v.index)] >= MINISL if MINISL else find(v.index) == main)}
print("ISLANDS kept", sorted((n for n in sizes.values() if (n >= MINISL if MINISL else n == sizes[main])), reverse=True)[:8], "of", len(sizes))
mw = o.matrix_world
# GAP rows
rows = {}
for v in bm.verts:
    if v.index not in keep: continue
    co = mw @ v.co
    if abs(co.x) > 0.10 or not 1.08 <= co.z <= 1.38 or (co.y * FRONT) <= 0: continue
    loc, nrm, _, dist = stree.find_nearest(co)
    if loc is None or nrm.y * FRONT < 0.3: continue
    n = (mw.to_3x3() @ v.normal).normalized()
    if n.dot(nrm) < 0: continue  # inner face of a doubled layer
    sd = dist if (co - loc).dot(nrm) >= 0 else -dist
    rows.setdefault(round(co.z * 50) / 50, []).append(sd * 1000)
print("GAP", os.path.basename(build), "(mm, outer layer, |x|<0.10; row: n p5 median p95 min)")
allg = []
for z in sorted(rows):
    g = np.array(rows[z]); allg += list(g)
    print(f"GAPROW z{z:.2f} n{len(g):4d} p5 {np.percentile(g,5):5.1f} med {np.median(g):5.1f} p95 {np.percentile(g,95):5.1f} min {g.min():5.1f}")
allg = np.array(allg)
sel = np.array([r for z in rows if 1.16 <= z <= 1.32 for r in rows[z]])
print(f"GAPSUM chest z1.16-1.32 median {np.median(sel):.1f} p5 {np.percentile(sel,5):.1f} p95 {np.percentile(sel,95):.1f} min {sel.min():.1f} under3mm {(sel<3).sum()}")

# BUMP: visible front surface depth map
cv, ct = [], []
faces = [f for f in bm.faces if all(v.index in keep for v in f.verts)]
idx = {}
for f in faces:
    for v in f.verts:
        if v.index not in idx: idx[v.index] = len(cv); cv.append(mw @ v.co)
    vs = [idx[v.index] for v in f.verts]
    for i in range(1, len(vs) - 1): ct.append((vs[0], vs[i], vs[i + 1]))
ctree = BVHTree.FromPolygons(cv, ct)
H = 0.002
SIG = float(os.environ.get("BUMPSIG", "20")); R = 2.2 * SIG
xs = np.arange(-0.12, 0.12 + 1e-9, H); zs = np.arange(1.10, 1.34 + 1e-9, H)
def depth(tree):
    D = np.full((len(xs), len(zs)), np.nan)
    for i, x in enumerate(xs):
        for k, z in enumerate(zs):
            hit = tree.ray_cast(Vector((x, FRONT * 0.5, z)), Vector((0, -FRONT, 0)))
            if hit[0] is not None and hit[1].y * FRONT > 0.2: D[i, k] = hit[0].y * FRONT * 1000
    return D
X, Z = np.meshgrid(xs * 1000, zs * 1000, indexing="ij")
def bandpass(D):
    """residual of each cell against a local quadratic fitted with a Gaussian window (sigma SIG mm)"""
    ok = ~np.isnan(D); px, pz, pd = X[ok], Z[ok], D[ok]
    res = np.full(D.shape, np.nan); full = np.pi * R * R / (H * 1000) ** 2
    for (i, k) in zip(*np.where(ok)):
        dx, dz = px - X[i, k], pz - Z[i, k]
        m = (dx * dx + dz * dz) < R * R
        if m.sum() < 0.8 * full: continue  # hem, neck opening or hole: one-sided window
        w = np.sqrt(np.exp(-(dx[m] ** 2 + dz[m] ** 2) / (2 * SIG * SIG)))
        A = np.stack([np.ones(m.sum()), dx[m], dz[m], dx[m] ** 2, dx[m] * dz[m], dz[m] ** 2], 1)
        coef, *_ = np.linalg.lstsq(A * w[:, None], pd[m] * w, rcond=None)
        res[i, k] = D[i, k] - coef[0]
    return res
rc = bandpass(depth(ctree)); rs = bandpass(depth(stree))
both = ~np.isnan(rc) & ~np.isnan(rs)
def stats(m, nm):
    c, s_ = rc[m], rs[m]
    slope = (c * s_).sum() / max((s_ * s_).sum(), 1e-9); corr = np.corrcoef(c, s_)[0, 1]
    print(f"BUMP{nm} sigma{SIG:.0f} n {m.sum():5d} cloth rms {np.sqrt((c**2).mean()):.2f} skin rms {np.sqrt((s_**2).mean()):.2f} "
          f"copy-slope {slope:.2f} corr {corr:.2f}")
stats(both, "")
for zlo, zhi, nm in ((1.10, 1.20, "ROW belly"), (1.20, 1.27, "ROW underbust"), (1.27, 1.34, "ROW bust")):
    stats(both & (Z >= zlo * 1000) & (Z < zhi * 1000), nm)
