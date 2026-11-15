# MuseFit copy of builds/_dionys/e6116ts/string_wavg.py (XIVAutoFit). Changes: none besides the file name (string_wavg.py)
"""LOCAL (Track Suit): even out bone weights across thin loose pieces (drawstrings) so each slice of a string moves as one.

    blender -b --factory-startup --disable-autoexec -P string_wavg.py -- <in.glb> <out.glb>

Pieces of SWMESH (mesh 2.0) with fewer than SWMAX (500) welded vertices: every vertex takes the mean weights of the piece's
vertices within SWBAND mm (6) of its height, top SWBONES (4) bones, normalised. The copy from the skin had given the front
and back of a 5 mm string tube different chest-physics shares (weight jumps of 0.5-0.75 per cm across the tube).
Refuses to overwrite. Prints pieces and vertices changed.
"""
import os
import sys

import bpy
import numpy as np

a = sys.argv[sys.argv.index("--") + 1:]
src, out = a
if os.path.exists(out):
    sys.exit(f"refusing to overwrite {out}")
MESH = os.environ.get("SWMESH", "mesh 2.0")
NMAX = int(os.environ.get("SWMAX", "500"))
BAND = float(os.environ.get("SWBAND", "6")) / 1000
NB = int(os.environ.get("SWBONES", "4"))
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
o = bpy.data.objects[MESH]
vs = o.data.vertices
P = np.array([tuple(o.matrix_world @ v.co) for v in vs])
par = list(range(len(vs)))


def fnd(i):
    while par[i] != i:
        par[i] = par[par[i]]; i = par[i]
    return i


seen = {}
for i in range(len(vs)):
    k = tuple(np.round(P[i], 5))
    if k in seen:
        par[fnd(i)] = fnd(seen[k])
    else:
        seen[k] = i
for e in o.data.edges:
    x, y = fnd(e.vertices[0]), fnd(e.vertices[1])
    if x != y:
        par[x] = y
groups = {}
for i in range(len(vs)):
    groups.setdefault(fnd(i), []).append(i)
vg = o.vertex_groups
ng = len(vg)
W = np.zeros((len(vs), ng))
for v in vs:
    for g in v.groups:
        W[v.index, g.group] = g.weight
npieces = nchanged = 0
for g in groups.values():
    if len(g) >= NMAX:
        continue
    npieces += 1
    g = np.array(g)
    z = P[g, 2]
    for i in g:
        sel = g[np.abs(z - P[i, 2]) <= BAND]
        m = W[sel].mean(axis=0)
        keep = np.argsort(-m)[:NB]
        new = np.zeros(ng)
        new[keep] = m[keep]
        new /= max(new.sum(), 1e-9)
        for k in range(ng):
            if W[i, k] > 0 and new[k] == 0:
                vg[k].remove([int(i)])
            elif new[k] > 0:
                vg[k].add([int(i)], float(new[k]), "REPLACE")
        nchanged += 1
print(f"string weights: {npieces} pieces, {nchanged} vertices averaged over +-{BAND * 1000:.0f} mm height slices")
bpy.ops.export_scene.gltf(filepath=out, export_format="GLB", export_extras=True)
