# New file for MuseFit (Track Suit v2 fix, 2026-11-14). write_weights() is adapted from XIVAutoFit
# builds/_dionys/flat6164v7/wsmooth_raw.py (same packing into JOINTS_0/1 + WEIGHTS_0/1, keeping each accessor's type).
"""Move cloth weight off bones the Muse body does not have, onto the bones the Muse skin uses at that spot. Raw .glb, no Blender.

    python3 -I -B chest_remap.py <in.glb> <out.glb> [bone,bone,...]   (default iv_c_mune_l,iv_c_mune_r)

The Muse+ (YAS) "Defined - Bare" top has no chest bones at all (docs/MUSE_BODY_STUDY.md): its chest is driven by the spine
(j_sebo_*) and collarbones (j_sako_*). For each cloth vertex with weight w on a listed bone, that weight is removed and
replaced by w times the Muse skin's own weights at the closest point of the skin (interpolated over the skin triangle, so
neighbouring vertices get smoothly varying weights). The vertex's other bones keep their weight. Coincident vertices get the
same result. Only JOINTS/WEIGHTS of changed primitives are rewritten; every other attribute stays byte-for-byte as it was
(no TANGENT is added). Writes a list of changed vertex counts and the remaining weight on the listed bones (must be 0).
"""
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np  # noqa: E402

import glb_raw as g  # noqa: E402
import muse_geom as mg  # noqa: E402

MAX_BONES = 8


def write_weights(writer: g.GlbWriter, doc: dict, prim: dict, W: np.ndarray) -> None:
    """Top 8 bones into JOINTS_0/1 + WEIGHTS_0/1, keeping each accessor's component type."""
    A = prim["attributes"]
    target = writer.doc["meshes"][prim["mesh"]]["primitives"][prim["prim"]]["attributes"]
    order = np.argsort(-W, 1)[:, :MAX_BONES]
    Wt = np.take_along_axis(W, order, 1)
    Wt = Wt / Wt.sum(1, keepdims=True)
    for slot, (jk, wk) in enumerate((("JOINTS_0", "WEIGHTS_0"), ("JOINTS_1", "WEIGHTS_1"))):
        cols = slice(slot * 4, slot * 4 + 4)
        if jk not in A:
            if Wt[:, cols].max() > 1e-6:
                sys.exit(f"{prim['name']}: needs more than 4 bones but has no {jk}")
            continue
        j = np.where(Wt[:, cols] > 0, order[:, cols], 0)
        ji, wi = doc["accessors"][A[jk]], doc["accessors"][A[wk]]
        target[jk] = writer.add_accessor(j.astype({5121: "u1", 5123: "<u2"}[ji["componentType"]]), ji["componentType"], "VEC4")
        w = Wt[:, cols]
        if wi["componentType"] != 5126:
            w = np.round(w * g.DIVISOR[wi["componentType"]])
        target[wk] = writer.add_accessor(w, wi["componentType"], "VEC4", wi.get("normalized", False))


def main(src: str, out: str, bones: list[str]) -> None:
    if os.path.exists(out):
        sys.exit(f"refusing to overwrite {out}")
    doc, blob, skin, cloth = mg.load(src)
    names = mg.bone_names(doc)
    drop = [names.index(b) for b in bones if b in names]
    if not drop:
        sys.exit(f"none of {bones} in the skeleton")
    if skin["W"][:, drop].sum() > 0:
        sys.exit("the skin itself uses a bone in the drop list: nothing to map onto")
    _, tri, bary, _ = mg.Surface(skin["P"], skin["T"]).signed(cloth["P"])
    skin_w = (skin["W"][skin["T"][tri]] * bary[..., None]).sum(1)  # skin weights at the closest skin point
    share = cloth["W"][:, drop].sum(1)
    W = cloth["W"].copy()
    W[:, drop] = 0
    W += share[:, None] * skin_w
    # coincident cloth vertices: average so they stay identical
    _, inv = np.unique(np.round(cloth["P"], 5), axis=0, return_inverse=True)
    inv = inv.ravel()
    summed = np.zeros((inv.max() + 1, W.shape[1]))
    np.add.at(summed, inv, W)
    counts = np.bincount(inv)[:, None]
    W = np.where((share > 0)[:, None] | (np.bincount(inv, share > 0)[inv] > 0)[:, None], (summed / counts)[inv], W)
    writer = g.GlbWriter(doc, blob)
    for k, prim in enumerate(cloth["prims"]):
        own = cloth["owner"] == k
        changed = own & (np.abs(W - cloth["W"]).sum(1) > 1e-6)
        if not changed.any():
            print(f"{prim['name']}: unchanged")
            continue
        write_weights(writer, doc, prim, W[own])
        moved = share[own].sum() / own.sum() * 100
        print(f"{prim['name']}: {int(changed.sum())} vertices changed; weight moved {moved:.2f}% of the mesh "
              f"(max {share[own].max():.2f} on one vertex)")
    writer.save(out)
    _, _, _, check = mg.load(out)
    left = check["W"][:, drop].sum() / len(check["W"]) * 100
    gained = check["W"].sum(0)
    top = np.argsort(-(gained - cloth["W"].sum(0)))[:5]
    print(f"left on {bones}: {left:.4f}% of the cloth weight; most gained: " +
          ", ".join(f"{names[i]} +{(gained[i] - cloth['W'][:, i].sum()) / len(check['W']) * 100:.2f}%" for i in top))
    if left > 0:
        sys.exit("weight left on a dropped bone")


if __name__ == "__main__":
    if len(sys.argv) not in (3, 4):
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2], (sys.argv[3] if len(sys.argv) == 4 else "iv_c_mune_l,iv_c_mune_r").split(","))
