# MuseFit copy of builds/_dionys/e6116ts/fold_lift.py (XIVAutoFit). Changes: none besides the file name (fold_lift.py)
"""LOCAL (Track Suit): lift cloth that sits inside or too close to the Dionys skin in a chest box, including inward-facing
fold layers (the creator's under-bust fold) that fit_to_ref leaves alone, and spread the lift smoothly over the cloth.

    blender -b --factory-startup --disable-autoexec -P fold_lift.py -- <in.glb> <out.glb> [clearance_mm=3.5]

Each vertex of FLMESH (mesh 2.0) inside the box (|x| < 0.14, z FLZ "1.12,1.34", front half y < 0 in Blender) whose signed
distance to the skin is under the clearance gets a target move along the skin normal. The moves are spread along the
cloth surface (welded at seams) by FLSPREAD passes that keep the larger of a vertex's own move and 0.85 x the mean of
its neighbours', so the neighbourhood follows with a soft falloff instead of a spike. Repeats up to 6 rounds until no
vertex is short. Shape keys get the same moves. Prints rounds, max move and stretch. Refuses to overwrite.
"""
import os
import sys
from collections import defaultdict

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

a = sys.argv[sys.argv.index("--") + 1:]
src, out = a[0], a[1]
CLEAR = (float(a[2]) if len(a) > 2 else 3.5) / 1000
if os.path.exists(out):
    sys.exit(f"refusing to overwrite {out}")
MESH = os.environ.get("FLMESH", "mesh 2.0")
ZLO, ZHI = (float(v) for v in os.environ.get("FLZ", "1.12,1.34").split(","))
SPREAD = int(os.environ.get("FLSPREAD", "12"))
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)


def mat(o):
    return o.material_slots[0].material.name if o.material_slots and o.material_slots[0].material else ""


V, F = [], []
for o in bpy.data.objects:
    if o.type == "MESH" and mat(o).startswith("/mt_c0201b0001_bibo"):
        b = len(V)
        V += [o.matrix_world @ v.co for v in o.data.vertices]
        F += [[b + i for i in p.vertices] for p in o.data.polygons]
tree = BVHTree.FromPolygons(V, F)
o = bpy.data.objects[MESH]
mw = o.matrix_world
inv = mw.inverted().to_3x3()
vs = o.data.vertices
start = np.array([tuple(mw @ v.co) for v in vs])
keyd = {}
rep = np.array([keyd.setdefault(tuple(np.round(start[i], 5)), i) for i in range(len(vs))])
adj = defaultdict(set)
for e in o.data.edges:
    a0, a1 = rep[e.vertices[0]], rep[e.vertices[1]]
    if a0 != a1:
        adj[a0].add(a1); adj[a1].add(a0)
reps = np.unique(rep)
total = np.zeros((len(vs), 3))
for rnd in range(6):
    cur = start + total
    need = np.zeros((len(vs), 3)); short = 0
    for i in reps:
        c = Vector(tuple(cur[i]))
        if not (abs(c.x) < 0.14 and ZLO < c.z < ZHI and c.y < 0):
            continue
        loc, n, _, d = tree.find_nearest(c)
        if n is None or d > 0.03:
            continue
        sd = d if (c - loc).dot(n) >= 0 else -d
        if sd >= CLEAR - 0.0002:
            continue
        short += 1
        need[i] = np.array(tuple(n)) * (CLEAR - sd + 0.0003)
    print(f"fold lift round {rnd}: {short} vertices short of {CLEAR * 1000:.1f} mm")
    if not short:
        break
    mag = np.linalg.norm(need, axis=1)
    for _ in range(SPREAD):
        new = need.copy(); newmag = mag.copy()
        for i in reps:
            nb = list(adj[i])
            if not nb:
                continue
            m = 0.85 * need[nb].mean(axis=0)
            if np.linalg.norm(m) > mag[i]:
                new[i] = m; newmag[i] = np.linalg.norm(m)
        need, mag = new, newmag
    total += need[rep]
for v in vs:
    step = inv @ Vector(tuple(total[v.index]))
    if step.length > 1e-9:
        v.co += step
        if o.data.shape_keys:
            for kb in o.data.shape_keys.key_blocks:
                kb.data[v.index].co += step
o.data.update()
mv = np.linalg.norm(total, axis=1) * 1000
print(f"fold lift: moved {(mv > 0.05).sum()} vertices, max {mv.max():.1f} mm")
now = start + total
rat = []
for e in o.data.edges:
    i, j = e.vertices
    l0 = np.linalg.norm(start[i] - start[j])
    if l0 > 1e-6 and (mv[i] > 0.05 or mv[j] > 0.05):
        rat.append(np.linalg.norm(now[i] - now[j]) / l0)
rat = np.array(rat)
if len(rat):
    print(f"STRETCH moved edges {len(rat)} min {rat.min():.2f} max {rat.max():.2f} outside 0.5-2x: {((rat < 0.5) | (rat > 2)).sum()}")
bpy.ops.export_scene.gltf(filepath=out, export_format="GLB", export_extras=True)
