# MuseFit copy of builds/_dionys/e6116ts/wsmooth.py (XIVAutoFit, = e0824v2's). Changes: none
"""Smooth cloth bone weights along the cloth surface in the butt/thigh crease band, to stop the cloth tearing where the copied
skin weights jump from butt to thigh. blender -b --factory-startup --disable-autoexec -P wsmooth.py -- <in.glb> <out.glb>
Env: WSZ0/WSZ1 band height m (0.74/0.90, Blender z), WSFADE m (0.03: blend ramps in over this at the band edges),
WSBACK (Blender y > this, default -0.02 = back and sides), WSITER (8), WSBONES (4), WSEDGE mm (20: no smoothing within 5 mm of a cloth border, full from 20 mm).
Vertices at the same position (the jeans' reversed inner twin faces, UV seams) are merged so they keep identical weights."""
import os, sys, bpy
from collections import defaultdict
a = sys.argv[sys.argv.index("--") + 1:]; SRC, OUT = a
if os.path.exists(OUT): sys.exit(f"refusing to overwrite {OUT}")
E = os.environ.get
Z0 = float(E("WSZ0", 0.74)); Z1 = float(E("WSZ1", 0.90)); FADE = float(E("WSFADE", 0.03)); BACK = float(E("WSBACK", -0.02))
ITER = int(E("WSITER", 8)); EDGE = float(E("WSEDGE", 20)) / 1000; NB = int(E("WSBONES", 4))
def mat(o): return o.material_slots[0].material.name if o.material_slots and o.material_slots[0].material else ""
bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.import_scene.gltf(filepath=SRC)
cloth = [o for o in bpy.data.objects if o.type == "MESH" and o.name.startswith("mesh ") and "b0001" not in mat(o)]
for o in cloth:
    M = o.matrix_world; vs = o.data.vertices
    P = [M @ v.co for v in vs]
    key = [tuple(round(c, 5) for c in p) for p in P]
    grp = {}; rep = [grp.setdefault(k, i) for i, k in enumerate(key)]          # representative vertex per position
    adj = defaultdict(set)
    for e in o.data.edges:
        i, j = rep[e.vertices[0]], rep[e.vertices[1]]
        if i != j: adj[i].add(j); adj[j].add(i)
    # cloth borders (rips, hems): edges used by one face; smoothing fades out near them so rip edges keep their motion
    from mathutils.kdtree import KDTree
    from collections import Counter
    ec = Counter()
    for f in o.data.polygons:
        for e in f.edge_keys: ec[e] += 1
    bpts = [P[i] for e, n in ec.items() if n == 1 for i in e]
    kd = KDTree(max(len(bpts), 1))
    for k, p in enumerate(bpts): kd.insert(p, k)
    kd.balance()
    def ramp(p):
        if p.y <= BACK: return 0.0
        t = min((p.z - Z0) / FADE, (Z1 - p.z) / FADE, 1.0)
        if bpts and EDGE > 0:
            d = kd.find(p)[2]; t = min(t, (d - EDGE * 0.25) / (EDGE * 0.75))
        return max(t, 0.0)
    names = {g.index: g.name for g in o.vertex_groups}
    W = {}
    for i in set(rep):
        W[i] = {names[g.group]: g.weight for g in vs[i].groups if g.weight > 0}
    act = [i for i in W if ramp(P[i]) > 0]
    if not act: continue
    for _ in range(ITER):
        new = {}
        for i in act:
            nb = [W[j] for j in adj[i]]
            if not nb: continue
            avg = defaultdict(float)
            for w in nb:
                for b, x in w.items(): avg[b] += x / len(nb)
            s = 0.5 * ramp(P[i]); d = defaultdict(float)
            for b, x in W[i].items(): d[b] += (1 - s) * x
            for b, x in avg.items(): d[b] += s * x
            top = sorted(d.items(), key=lambda kv: -kv[1])[:NB]; tot = sum(x for _, x in top)
            new[i] = {b: x / tot for b, x in top}
        W.update(new)
    gi = {g.name: g for g in o.vertex_groups}
    for k, i in enumerate(rep):
        if ramp(P[i]) <= 0: continue
        for g in list(vs[k].groups): o.vertex_groups[g.group].remove([k])
        for b, x in W[i].items():
            if b not in gi: gi[b] = o.vertex_groups.new(name=b)
            gi[b].add([k], x, "REPLACE")
    print(f"SMOOTH {o.name}: {len(act)} positions smoothed")
bpy.ops.export_scene.gltf(filepath=OUT, export_format="GLB", export_extras=True)
