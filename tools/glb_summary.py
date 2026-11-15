# New file for MuseFit (job 009, checked and re-run in job 010).
"""Print a plain-text summary of one or more .glb files: meshes, materials, attributes (node extras), skin bones, vertex layout.

Read-only. Needs numpy (to find the bones with real weight). Run:  python3 -I glb_summary.py <file.glb> [<file.glb> ...]
Used to describe the Dionys and Doll Body 2 reference glbs next to the Muse .mdl summaries from mdl_study.py.
"""
import json
import struct
import sys

import numpy as np

sys.dont_write_bytecode = True
COUNT = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}


def load(path: str):
    """Return (gltf json, binary chunk) of a .glb."""
    data = open(path, "rb").read()
    magic, _, _ = struct.unpack_from("<4sII", data, 0)
    if magic != b"glTF":
        raise ValueError(f"{path}: not a .glb")
    length, kind = struct.unpack_from("<I4s", data, 12)
    if kind != b"JSON":
        raise ValueError(f"{path}: first chunk is not JSON")
    blen = struct.unpack_from("<I", data, 20 + length)[0]
    return json.loads(data[20:20 + length]), data[28 + length:28 + length + blen]


def read_accessor(g, blob, index):
    a = g["accessors"][index]
    view = g["bufferViews"][a["bufferView"]]
    ctype = {5121: "u1", 5123: "<u2", 5125: "<u4", 5126: "<f4"}[a["componentType"]]
    n = COUNT[a["type"]]
    stride = view.get("byteStride") or np.dtype(ctype).itemsize * n
    field = np.dtype({"names": ["v"], "formats": [(ctype, (n,))], "offsets": [0], "itemsize": stride})
    return np.frombuffer(blob, field, a["count"], view.get("byteOffset", 0) + a.get("byteOffset", 0))["v"]


def read_primitives(path: str):
    """Every mesh primitive of a .glb as a dict: name, material, extras, positions (n,3), normals (n,3), triangles (m,3), joints/weights (n,8) with
    bone names in joint_names. Joints and weights are padded to 8 slots (a second set JOINTS_1/WEIGHTS_1 is used when present)."""
    g, blob = load(path)
    nodes = g.get("nodes", [])
    joint_names = [nodes[j].get("name", "?") for j in g["skins"][0]["joints"]] if g.get("skins") else []
    out = []
    for n in nodes:
        if "mesh" not in n:
            continue
        for p in g["meshes"][n["mesh"]]["primitives"]:
            a = p["attributes"]
            joints = np.zeros((len(read_accessor(g, blob, a["POSITION"])), 8), "i8")
            weights = np.zeros(joints.shape, "f8")
            for slot, (jk, wk) in enumerate((("JOINTS_0", "WEIGHTS_0"), ("JOINTS_1", "WEIGHTS_1"))):
                if jk in a:
                    joints[:, slot * 4:slot * 4 + 4] = read_accessor(g, blob, a[jk])
                    weights[:, slot * 4:slot * 4 + 4] = read_accessor(g, blob, a[wk])
            out.append({"name": g["meshes"][n["mesh"]].get("name") or n.get("name", "?"), "material": g["materials"][p["material"]].get("name", "?") if "material" in p else "none",
                        "extras": sorted((n.get("extras") or {}).keys()), "positions": read_accessor(g, blob, a["POSITION"]).astype("f8"),
                        "normals": read_accessor(g, blob, a["NORMAL"]).astype("f8"), "triangles": read_accessor(g, blob, p["indices"]).astype("i8").reshape(-1, 3), "joints": joints, "weights": weights,
                        "joint_names": joint_names})
    return out


def summarize(path: str) -> str:
    g, blob = load(path)
    nodes, acc = g.get("nodes", []), g.get("accessors", [])
    lines = [f"file: {path}"]
    skins = g.get("skins", [])
    joint_names = [nodes[j].get("name", "?") for j in skins[0]["joints"]] if skins else []
    lines.append(f"skin: {len(joint_names)} joints in the armature")
    used_all = set()
    for n in nodes:
        if "mesh" not in n:
            continue
        mesh = g["meshes"][n["mesh"]]
        attrs = sorted(k for k, v in (n.get("extras") or {}).items() if v) or sorted(k for k in (n.get("extras") or {}))
        for p in mesh["primitives"]:
            mat = g["materials"][p["material"]].get("name", "?") if "material" in p else "none"
            verts = acc[p["attributes"]["POSITION"]]["count"]
            tris = acc[p["indices"]]["count"] // 3 if "indices" in p else 0
            layout = ", ".join(f"{k}:{acc[v]['type']}" for k, v in p["attributes"].items())
            pos = read_accessor(g, blob, p["attributes"]["POSITION"]).astype("f8")
            used = set()
            for jk, wk in (("JOINTS_0", "WEIGHTS_0"), ("JOINTS_1", "WEIGHTS_1")):
                if jk in p["attributes"]:
                    j = read_accessor(g, blob, p["attributes"][jk]).astype("i8")
                    w = read_accessor(g, blob, p["attributes"][wk]).astype("f8")
                    used |= {joint_names[i] for i in set(j[w > 0].ravel().tolist())}
            used_all |= used
            lines += [f"  {n.get('name', mesh.get('name', '?'))}: material {mat}", f"    vertices {verts}, triangles {tris}, extras {attrs or 'none'}",
                      f"    bbox min {pos.min(0).round(3).tolist()} max {pos.max(0).round(3).tolist()}",
                      f"    bones used (weight>0): {len(used)}: {', '.join(sorted(used))}", f"    vertex layout: {layout}"]
    lines.append(f"bones used in the whole file: {len(used_all)}")
    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    for p in sys.argv[1:]:
        print(summarize(p))
        print()
