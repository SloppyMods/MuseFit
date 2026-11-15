"""Check mdl_to_glb.py against a real Penumbra export of the same .mdl. New file for MuseFit. Read-only.

    python3 -B compare_export.py <converted.glb> <penumbra_export.glb>

For every mesh name found in both files it compares, vertex by vertex (same order): POSITION, NORMAL, TEXCOORD_0/1/2,
_FFXIV_COLOR, the bone names and weights (all 8 influences), the triangles and the atr_* tags. Prints the largest difference
per field. Needs numpy only.
"""
import os
import sys

import numpy as np

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import glb_raw  # noqa: E402


def prim_data(doc, blob, rec):
    a = rec["attributes"]
    get = lambda k: glb_raw.read_accessor(doc, blob, a[k]).astype("f8")
    joints = np.concatenate([glb_raw.read_accessor(doc, blob, a[k]) for k in ("JOINTS_0", "JOINTS_1")], 1).astype(int)
    weights = np.concatenate([get("WEIGHTS_0"), get("WEIGHTS_1")], 1)
    names, _ = glb_raw.joint_matrices(doc, blob, rec["skin"] or 0)
    col = glb_raw.read_accessor(doc, blob, a["_FFXIV_COLOR"]).astype("f8") / 65535.0
    out = {k: get(k) for k in ("POSITION", "NORMAL", "TEXCOORD_0", "TEXCOORD_1", "TEXCOORD_2")}
    out["COLOR"] = col
    out["TRIS"] = glb_raw.read_accessor(doc, blob, rec["indices"]).reshape(-1, 3).astype(int)
    out["WEIGHTS"] = weights
    out["BONES"] = np.array([[names[j] if w > 1e-6 else "-" for j, w in zip(jr, wr)] for jr, wr in zip(joints, weights)])
    out["ATR"] = sorted(k for k, v in (rec["extras"] or {}).items() if v is True)
    return out


def main(mine_path, real_path):
    md, mb = glb_raw.load(mine_path)
    rd, rb = glb_raw.load(real_path)
    real = {r["name"]: r for r in glb_raw.primitives(rd)}
    bad = 0
    compared = 0
    for rec in glb_raw.primitives(md):
        name = rec["name"]
        if name not in real:
            print(f"{name}: not in the export")
            bad += 1  # every converted mesh must have a counterpart
            continue
        compared += 1
        a, b = prim_data(md, mb, rec), prim_data(rd, rb, real[name])
        if len(a["POSITION"]) != len(b["POSITION"]):
            print(f"{name}: vertex count {len(a['POSITION'])} vs export {len(b['POSITION'])}")
            bad += 1
            continue
        line = [f"{name}: {len(a['POSITION'])} vertices"]
        for k in ("POSITION", "NORMAL", "TEXCOORD_0", "TEXCOORD_1", "TEXCOORD_2", "COLOR"):
            d = np.abs(a[k] - b[k]).max()
            line.append(f"{k} max diff {d:.2e}")
            bad += d > 1e-4
        # compare bone names weighted: same set of (bone, weight) per vertex, order free
        mism = 0
        for ba, wa, bb, wb in zip(a["BONES"], a["WEIGHTS"], b["BONES"], b["WEIGHTS"]):
            da, db = {}, {}
            for n, w in zip(ba, wa):
                if n != "-": da[n] = da.get(n, 0) + w
            for n, w in zip(bb, wb):
                if n != "-": db[n] = db.get(n, 0) + w
            if set(da) != set(db) or any(abs(da[n] - db[n]) > 1e-4 for n in da):
                mism += 1
        line.append(f"bone/weight sets differing {mism}")
        bad += mism > 0
        same_tris = a["TRIS"].shape == b["TRIS"].shape and bool((a["TRIS"] == b["TRIS"]).all())
        line.append(f"triangles identical {same_tris}")
        line.append(f"atr {a['ATR']} vs {b['ATR']}")
        bad += (not same_tris) or a["ATR"] != b["ATR"]
        print("; ".join(line))
    if compared == 0:
        print("no mesh of the converted file was found in the export: nothing compared")
        bad += 1
    print("RESULT", "MATCH" if not bad else f"{int(bad)} difference(s)")
    return int(bad)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    sys.exit(1 if main(*sys.argv[1:]) else 0)
